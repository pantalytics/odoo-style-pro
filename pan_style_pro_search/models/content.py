"""Smart search in what was written on a record: its description and its
chatter (emails and notes), like searching a mail inbox.

The index holds everything; access is checked at search time, never at index
time. Only the search method reads it, with SQL, and it only returns record
ids into the normal _search, so record rules and ACLs apply as for any field.
Nobody can read the index through the ORM or RPC: no group has any right on it.

See docs/SMART_SEARCH.md, "Descriptions and chatter".
"""

import logging
import re

from lxml import etree, html

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

from .base import GROUP, fold

_logger = logging.getLogger(__name__)

# The one field smart search reads besides the chatter. Odoo's own convention
# for what was written on a card (tasks, leads, tickets, products, events).
# Other text fields (terms and conditions, website descriptions) are mostly
# boilerplate repeated on every record, so they are left out.
CONTENT_FIELD = "description"
CONTENT_FIELD_TYPES = ("html", "text")
# Written by a person, a colleague or a customer: no tracking, no system
# notifications ("Stage changed"), no automated or mass mailings.
MESSAGE_TYPES = ("email", "comment")
MESSAGE_SOURCE = "message"
# Newsletters and pasted logs add noise, not signal.
MAX_CHARS = 10_000
# Like ilike on the other fields: shorter words match the name only.
MIN_WORD_LENGTH = 4
BATCH = 500
SNIPPET_CHARS = 120
# Quoted history and signatures, as Odoo marks them when it receives a mail
# (tools.mail.tag_quote), plus anything that is not text. Otherwise our own
# signature's "Amsterdam" matches every record we ever mailed from.
_DROP = "//*[@data-o-mail-quote] | //blockquote | //style | //script | //head | //title"
_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "hr", "table", "ul", "ol"}


def content_text(value, is_html):
    """The words a person wrote in `value`, as one line of plain text."""
    if not value:
        return ""
    if is_html:
        try:
            root = html.fragment_fromstring(value, create_parent="div")
        except (etree.LxmlError, ValueError):
            return ""
        for node in root.xpath(_DROP):
            node.drop_tree()
        for node in root.iter():
            # <p>pomp</p><p>lekt</p> is two words, not "pomplekt".
            if isinstance(node.tag, str) and node.tag in _BLOCK_TAGS:
                node.tail = " " + (node.tail or "")
        value = root.text_content()
    return " ".join(value.split())[:MAX_CHARS]


def content_word(word):
    """`word` as a full-text prefix query, or None if it does not search content."""
    folded = fold(word)
    if len(folded) < MIN_WORD_LENGTH or not folded.isalnum():
        # Codes and sizes with punctuation ("hp-rvs", "3,5") match literally on
        # the other fields; the text parser would split them into noise.
        return None
    return f"{folded}:*"


class PanSmartSearchContent(models.Model):
    """One row per description and per message: a tsvector of the cleaned,
    accent-folded text, nothing readable. Kept fresh by the create/write hooks
    below; the daily cron fills the gaps (first build, edits through SQL)."""

    _name = "pan.smart.search.content"
    _description = "Smart search: descriptions and chatter"
    _log_access = False

    model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    # The field name, or "message".
    source = fields.Char(required=True)
    # 0 for a field.
    message_id = fields.Integer(required=True, default=0)
    indexed_at = fields.Datetime(required=True)

    _source_unique = models.UniqueIndex("(model, res_id, source, message_id)")
    _message_id_index = models.Index("(message_id) WHERE message_id <> 0")

    def init(self):
        # No ORM field type for tsvector; the ORM leaves an unknown column alone.
        cr = self.env.cr
        cr.execute(SQL("ALTER TABLE %s ADD COLUMN IF NOT EXISTS tsv tsvector", SQL.identifier(self._table)))
        cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s USING gin (tsv)",
            SQL.identifier(f"{self._table}__tsv_index"), SQL.identifier(self._table),
        ))

    @api.model
    def _pan_smart_search_active(self):
        group = self.env.ref(GROUP, raise_if_not_found=False)
        return bool(group) and group in self.env.ref("base.group_user").all_implied_ids

    @api.model
    def _pan_smart_search_models(self):
        return [name for name in self.env.registry if self.env[name]._pan_smart_search_content_fields() is not None]

    @api.model
    def _pan_smart_search_store(self, rows):
        """Upsert [(model, res_id, source, message_id, text)]."""
        for start in range(0, len(rows), BATCH):
            chunk = rows[start:start + BATCH]
            self.env.cr.execute(SQL(
                """INSERT INTO %s (model, res_id, source, message_id, tsv, indexed_at) VALUES %s
                   ON CONFLICT (model, res_id, source, message_id)
                   DO UPDATE SET tsv = EXCLUDED.tsv, indexed_at = EXCLUDED.indexed_at""",
                SQL.identifier(self._table),
                SQL(", ").join(
                    SQL("(%s, %s, %s, %s, to_tsvector('simple', %s), now() AT TIME ZONE 'UTC')", model, res_id, source, message_id, fold(text))
                    for model, res_id, source, message_id, text in chunk
                ),
            ))

    @api.model
    def _pan_smart_search_index_records(self, model_name, ids):
        """(Re)index the content fields of these records, every language at once."""
        Model = self.env[model_name]
        rows = []
        for fname in Model._pan_smart_search_content_fields() or ():
            field = Model._fields[fname]
            Model.flush_model([fname])
            self.env.cr.execute(SQL(
                "SELECT id, %s FROM %s WHERE id = ANY(%s)",
                SQL.identifier(fname), SQL.identifier(Model._table), list(ids),
            ))
            for res_id, value in self.env.cr.fetchall():
                if isinstance(value, dict):  # translated: {"en_US": ..., "nl_NL": ...}
                    value = " ".join(dict.fromkeys(v for v in value.values() if v))
                rows.append((model_name, res_id, fname, 0, content_text(value, field.type == "html")))
        self._pan_smart_search_store(rows)
        return len(ids)

    @api.model
    def _pan_smart_search_index_messages(self, messages):
        """(Re)index these mail.message records, or drop them if they no longer
        count (a model without content search, a system notification)."""
        rows, drop = [], []
        content_models = {}
        for message in messages.sudo():
            if message.model not in content_models:
                content_models[message.model] = (
                    message.model in self.env and self.env[message.model]._pan_smart_search_content_fields() is not None
                )
            if content_models[message.model] and message.res_id and message.message_type in MESSAGE_TYPES:
                rows.append((message.model, message.res_id, MESSAGE_SOURCE, message.id, content_text(message.body, True)))
            else:
                drop.append(message.id)
        self._pan_smart_search_unindex_messages(drop)
        self._pan_smart_search_store(rows)

    @api.model
    def _pan_smart_search_unindex_messages(self, message_ids):
        if message_ids:
            self.env.cr.execute(SQL(
                "DELETE FROM %s WHERE message_id = ANY(%s)", SQL.identifier(self._table), list(message_ids),
            ))

    @api.model
    def _pan_smart_search_build(self):
        """Daily cron, and right after the setting is switched on: index what
        the hooks did not (the first build, records changed while the setting
        was off), drop what is gone. Newest first, in batches; the cron loops
        until nothing is left."""
        if not self._pan_smart_search_active():
            return
        cr = self.env.cr
        table = SQL.identifier(self._table)
        content_models = self._pan_smart_search_models()
        cr.execute(SQL(
            "DELETE FROM %s c WHERE c.message_id <> 0 AND NOT EXISTS (SELECT 1 FROM mail_message m WHERE m.id = c.message_id)",
            table,
        ))
        cr.execute(SQL("DELETE FROM %s WHERE model <> ALL(%s)", table, content_models))
        todo = []
        for model_name in content_models:
            Model = self.env[model_name]
            cr.execute(SQL(
                "DELETE FROM %s c WHERE c.model = %s AND c.message_id = 0 AND NOT EXISTS (SELECT 1 FROM %s r WHERE r.id = c.res_id)",
                table, model_name, SQL.identifier(Model._table),
            ))
            for fname in Model._pan_smart_search_content_fields():
                Model.flush_model([fname, "write_date"])
                cr.execute(SQL(
                    """SELECT r.id FROM %s r
                       LEFT JOIN %s c ON c.model = %s AND c.res_id = r.id AND c.source = %s AND c.message_id = 0
                       WHERE r.%s IS NOT NULL AND (c.id IS NULL OR c.indexed_at < r.write_date)
                       ORDER BY r.id DESC""",
                    SQL.identifier(Model._table), table, model_name, fname, SQL.identifier(fname),
                ))
                todo += [(model_name, [row[0] for row in cr.fetchall()])]
        self.env["mail.message"].flush_model(["model", "res_id", "message_type"])
        cr.execute(SQL(
            """SELECT m.id FROM mail_message m
               WHERE m.model = ANY(%s) AND m.res_id IS NOT NULL AND m.message_type = ANY(%s)
                 AND NOT EXISTS (SELECT 1 FROM %s c WHERE c.message_id = m.id)
               ORDER BY m.id DESC""",
            content_models, list(MESSAGE_TYPES), table,
        ))
        message_ids = [row[0] for row in cr.fetchall()]
        remaining = sum(len(ids) for _model, ids in todo) + len(message_ids)
        _logger.info("Smart search: %d descriptions and messages to index", remaining)
        for model_name, ids in todo:
            for start in range(0, len(ids), BATCH):
                done = self._pan_smart_search_index_records(model_name, ids[start:start + BATCH])
                remaining -= done
                if not self._pan_smart_search_progress(done, remaining):
                    return
        Message = self.env["mail.message"].sudo()
        for start in range(0, len(message_ids), BATCH):
            batch = Message.browse(message_ids[start:start + BATCH])
            self._pan_smart_search_index_messages(batch)
            batch.invalidate_recordset()
            remaining -= len(batch)
            if not self._pan_smart_search_progress(len(batch), remaining):
                return

    @api.model
    def _pan_smart_search_progress(self, done, remaining):
        """Commit a batch when running as the cron; False once its time is up
        (it then runs again for the rest). Called directly (tests, a shell),
        it does everything in the caller's transaction."""
        if not self.env.context.get("cron_id"):
            return True
        return bool(self.env["ir.cron"]._commit_progress(done, remaining=remaining))


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _pan_smart_search_content_fields(self):
        """The content fields smart search indexes on this model ((), or a tuple
        with "description"), or None if it does not search content at all.
        Only models with a chatter: business documents, not countries."""
        if (
            "message_ids" not in self._fields
            or not self._auto
            or self._abstract
            or not self._pan_smart_search_eligible()
        ):
            return None
        field = self._fields.get(CONTENT_FIELD)
        if (
            field is not None
            and field.type in CONTENT_FIELD_TYPES
            and field.store
            and not field.related
            and not field.inherited
            and not field.company_dependent
        ):
            return (CONTENT_FIELD,)
        return ()

    @api.model
    def _pan_smart_search_content_sources(self):
        """What this user may match content on: the content fields they may
        read, and the chatter for internal users. Portal users never match the
        chatter: they may not read internal notes, and smart search is for
        employees."""
        fnames = self._pan_smart_search_content_fields()
        if fnames is None or not self.env["pan.smart.search.content"]._pan_smart_search_active():
            return ()
        sources = [fname for fname in fnames if self._has_field_access(self._fields[fname], "read")]
        if self.env.user._is_internal():
            sources.append(MESSAGE_SOURCE)
        return tuple(sources)

    @api.model
    def _pan_smart_search_content_domain(self, word, sources):
        """Records of this model with `word` in one of `sources`, or None. A
        subquery on the index; the caller's _search applies the access rules."""
        query = content_word(word)
        if not query or not sources:
            return None
        table = SQL.identifier(self.env["pan.smart.search.content"]._table)
        subquery = SQL(
            "SELECT res_id FROM %s WHERE model = %s AND source = ANY(%s) AND tsv @@ to_tsquery('simple', %s)",
            table, self._name, list(sources), query,
        )
        return Domain.custom(to_sql=lambda model, alias, _query: SQL("%s IN (%s)", SQL.identifier(alias, "id"), subquery))

    @api.model
    def pan_smart_search_snippets(self, ids, term):
        """{id: one line of text} showing where `term` matched, for records
        whose name does not explain the match. Read as the user, through the
        ORM: only records they can read, only text they can read."""
        sources = self._pan_smart_search_content_sources()
        words = [fold(word) for word in self._pan_smart_search_words(term) if content_word(word)]
        if not sources or not words or not ids:
            return {}
        records = self.with_context(active_test=False).search([("id", "in", [int(i) for i in ids])])
        texts = {record.id: [] for record in records}
        for fname in sources:
            if fname == MESSAGE_SOURCE:
                continue
            is_html = self._fields[fname].type == "html"
            for record in records:
                texts[record.id].append(content_text(record[fname], is_html))
        if MESSAGE_SOURCE in sources and records:
            # Only the messages the index says match, then read as the user:
            # mail.message's own rules decide what they may see.
            self.env.cr.execute(SQL(
                """SELECT message_id FROM %s WHERE model = %s AND res_id = ANY(%s) AND source = %s
                   AND tsv @@ to_tsquery('simple', %s)""",
                SQL.identifier(self.env["pan.smart.search.content"]._table), self._name, records.ids,
                MESSAGE_SOURCE, " | ".join(content_word(word) for word in words),
            ))
            matched = [row[0] for row in self.env.cr.fetchall()]
            messages = self.env["mail.message"].search(
                [("id", "in", matched), ("model", "=", self._name), ("res_id", "in", records.ids)], order="id desc",
            )
            for message in messages:
                texts[message.res_id].append(content_text(message.body, True))
        result = {}
        for record in records:
            name = fold(record.display_name)
            missing = [word for word in words if word not in name]
            if not missing:
                continue
            for text in texts[record.id]:
                snippet = self._pan_smart_search_snippet(text, missing)
                if snippet:
                    result[record.id] = snippet
                    break
        return result

    @api.model
    def _pan_smart_search_snippet(self, text, words):
        """About SNIPPET_CHARS of `text` around the first of `words` it contains
        at the start of a word, or ""."""
        folded = fold(text)
        if len(folded) != len(text):
            # lower() changed the length (a rare ligature): positions would
            # drift, so match on the text itself.
            folded = text.lower()
        starts = [m.start() for word in words if (m := re.search(r"\b" + re.escape(word), folded))]
        if not starts:
            return ""
        position = min(starts)
        begin = max(0, position - SNIPPET_CHARS // 3)
        end = min(len(text), begin + SNIPPET_CHARS)
        snippet = text[begin:end]
        if begin:
            snippet = "…" + snippet.split(" ", 1)[-1]
        if end < len(text):
            snippet = snippet.rsplit(" ", 1)[0] + "…"
        return snippet


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(vals.get(CONTENT_FIELD) for vals in vals_list):
            records._pan_smart_search_reindex()
        return records

    def write(self, vals):
        result = super().write(vals)
        if CONTENT_FIELD in vals:
            self._pan_smart_search_reindex()
        return result

    def _pan_smart_search_reindex(self):
        Content = self.env["pan.smart.search.content"]
        if self and self._pan_smart_search_content_fields() and Content._pan_smart_search_active():
            Content._pan_smart_search_index_records(self._name, self.ids)


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        Content = self.env["pan.smart.search.content"]
        if Content._pan_smart_search_active():
            # So this morning's email is found now, not after tonight's cron.
            Content._pan_smart_search_index_messages(messages)
        return messages

    def write(self, vals):
        result = super().write(vals)
        Content = self.env["pan.smart.search.content"]
        if {"body", "model", "res_id", "message_type"} & set(vals) and Content._pan_smart_search_active():
            Content._pan_smart_search_index_messages(self)
        return result

    def unlink(self):
        ids = self.ids
        result = super().unlink()
        self.env["pan.smart.search.content"]._pan_smart_search_unindex_messages(ids)
        return result
