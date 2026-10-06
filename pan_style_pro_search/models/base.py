"""Smart search for every model: words in any order, typos, best match first.

Nothing is configured per model. Each model tells us itself what is
searchable:

- search bar: the fields of its search view, including the field paths in
  their filter_domain (so linked fields such as partner_id or
  product_variant_ids.default_code come along). A field a customer adds to
  the search view, via Studio or custom code, is searched automatically.
- dropdowns: the fields Odoo itself uses there (_rec_names_search, else
  _rec_name), which keeps them fast.
- typos and ranking: the name field (complete_name if the model has one,
  else _rec_name) and a reference field (default_code, ref, code, barcode).

See docs/SMART_SEARCH.md.
"""

import logging
import unicodedata

from lxml import etree

from odoo import api, fields, models, tools
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.tools.safe_eval import safe_eval
from odoo.tools.sql import escape_psql

_logger = logging.getLogger(__name__)

GROUP = "pan_style_pro_search.group_smart_search"
THRESHOLD_PARAM = "pan_style_pro_search.word_similarity_threshold"
DEFAULT_THRESHOLD = 0.5
# Only words of letters this long get typo tolerance. A typo-tolerant "M8" or
# "3" matches half the catalogue, and pg_trgm splits "hp-rvs" into "hp" and
# "rvs", so codes and sizes ("3mm", "M8x20") match literally.
FUZZY_MIN_LENGTH = 4
# Shorter words only match the name: "62" inside a reference like R0000062,
# or inside an email address, matches nearly at random.
SHORT_WORD_LENGTH = 4
# Words this long that occur nowhere as typed also try every variant with two
# neighbouring letters swapped ("pijpbuegel" -> "pijpbeugel"), which trigram
# similarity misses at a threshold that does not add noise.
SWAP_MIN_LENGTH = 5
# A trigram index only serves LIKE patterns of 3+ characters; shorter words
# match the name literally, without accent folding (a seq scan otherwise).
FOLD_MIN_LENGTH = 3
# An exact reference beats any similarity score.
EXACT_CODE_BONUS = 10
# Upper bound on searched field paths per model: every word is OR-ed over all
# of them, so this caps the cost on models with very wide search views.
MAX_PATHS = 15
NAME_FIELDS = ("complete_name",)
CODE_FIELDS = ("default_code", "ref", "code", "barcode")
# Field types a word can be matched against with ilike. Text and html are left
# out on purpose: long descriptions and mail bodies are noise and slow.
MATCH_TYPES = ("char", "many2one", "many2many", "one2many")
_MARK = "__pan_smart_search__"


def _fold_table():
    """Accented Latin letters (both cases) -> plain lower-case letters, for
    PostgreSQL translate(). Both cases, because lower() only lowercases ASCII
    in a database with LC_CTYPE C."""
    extra = {"ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ø": "o", "Ø": "o", "ß": "s", "æ": "a", "Æ": "a",
             "œ": "o", "Œ": "o", "ı": "i", "ħ": "h", "Ħ": "h", "þ": "t", "Þ": "t", "ð": "d", "Ð": "d"}
    pairs = dict(extra)
    for code in range(0xC0, 0x250):
        char = chr(code)
        base = unicodedata.normalize("NFKD", char)[0].lower()
        if char not in pairs and base != char.lower() and base.isascii() and base.isalpha():
            pairs[char] = base
    return "".join(pairs), "".join(pairs.values())


FOLD_FROM, FOLD_TO = _fold_table()


_FOLD_PY = str.maketrans(FOLD_FROM, FOLD_TO)


def fold(text):
    """Lower case without accents: "SPÓŁKA" -> "spolka"."""
    return (text or "").lower().translate(_FOLD_PY)


def fold_sql(expression):
    """SQL counterpart of fold(); the trigram index cron uses the same expression."""
    return SQL("translate(lower(%s), %s, %s)", expression, FOLD_FROM, FOLD_TO)


class Base(models.AbstractModel):
    _inherit = "base"

    x_smart_search = fields.Char(
        string="Smart search",
        compute="_compute_x_smart_search",
        search="_search_x_smart_search",
        exportable=False,
        help="Search with separate words in any order, tolerant of typos. "
        "Results are ranked best match first.",
    )

    def _compute_x_smart_search(self):
        for record in self:
            record.x_smart_search = False

    def _search_x_smart_search(self, operator, value):
        if operator != "ilike" or not isinstance(value, str):
            return NotImplemented
        return self._pan_smart_search_domain(value, self._pan_smart_search_view_paths())

    # ------------------------------------------------------------------
    # Which models, which fields
    # ------------------------------------------------------------------

    @api.model
    def _pan_smart_search_enabled(self):
        """The Style Pro setting: smart search on, for every internal user."""
        return self.env.user.has_group(GROUP)

    @api.model
    def _pan_smart_search_sql_char(self, name):
        """A char field SQL can read here: stored, or inherited from a parent
        table (product.product's name lives on product.template)."""
        field = self._fields.get(name)
        if not field or field.type != "char":
            return False
        return bool(field.store or (field.inherited and field.inherited_field.store))

    @api.model
    def _pan_smart_search_name_field(self):
        """Char field holding the record's name, or None."""
        return next((name for name in (*NAME_FIELDS, self._rec_name) if self._pan_smart_search_sql_char(name)), None)

    @api.model
    def _pan_smart_search_code_field(self):
        return next((name for name in CODE_FIELDS if self._pan_smart_search_sql_char(name)), None)

    @api.model
    def _pan_smart_search_eligible(self):
        # Technical models (ir.*) are left out: Settings > Technical, large
        # tables such as ir.model.data, and nobody searches them for work.
        return (
            not self._abstract
            and not self._transient
            and not self._name.startswith("ir.")
            and bool(self._pan_smart_search_name_field())
        )

    @api.model
    def _pan_smart_search_valid_path(self, path):
        """True if this user can match `path` with ilike. Every word is OR-ed
        over all paths, so one path the user cannot search would break the
        whole search, not just that field."""
        model = self
        names = path.split(".")
        for position, name in enumerate(names):
            field = model._fields.get(name)
            # Odoo's own rule (fields_get "searchable"): stored, or a search
            # method; related and inherited fields only get one when their
            # target is searchable.
            if field is None or not field._description_searchable:
                return False
            if not model._has_field_access(field, "read"):
                return False
            if field.relational and not self.env[field.comodel_name].has_access("read"):
                return False
            if not self._pan_smart_search_chain_readable(model, field):
                return False
            if position < len(names) - 1:
                if not field.relational:
                    return False
                model = self.env[field.comodel_name]
            elif field.type not in MATCH_TYPES:
                return False
        return True

    @api.model
    def _pan_smart_search_chain_readable(self, model, field):
        """A related or inherited field reads other models behind the scenes
        (website.menu.url is page_id.url); the user needs read access on each."""
        if field.inherited and not self.env[field.inherited_field.model_name].has_access("read"):
            return False
        if field.related:
            current = model
            for name in field.related.split(".")[:-1]:
                link = current._fields.get(name)
                if link is None or not link.relational or not self.env[link.comodel_name].has_access("read"):
                    return False
                current = self.env[link.comodel_name]
        return True

    @api.model
    @tools.ormcache(cache="templates")
    def _pan_smart_search_view_candidates(self):
        """Field paths of the default search view, in view order (cached until
        a view changes)."""
        arch, _view = self.sudo()._get_view(view_type="search")
        paths = []
        for node in arch.iter("field"):
            name = node.get("name")
            if name == "x_smart_search" or any(parent.tag == "searchpanel" for parent in node.iterancestors()):
                continue
            found = self._pan_smart_search_filter_domain_paths(node.get("filter_domain"))
            for path in found or [name]:
                if path and path not in paths:
                    paths.append(path)
        return tuple(paths)

    @api.model
    def _pan_smart_search_filter_domain_paths(self, filter_domain):
        """Field paths a search view field's filter_domain matches the typed value on."""
        if not filter_domain:
            return []
        try:
            domain = safe_eval(
                filter_domain,
                {"self": _MARK, "raw_value": _MARK, "context": {}, "uid": self.env.uid},
            )
        except Exception:  # noqa: BLE001 - any domain we cannot evaluate falls back to the field name
            return []
        return [
            leaf[0]
            for leaf in domain
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and isinstance(leaf[0], str) and leaf[2] == _MARK
        ]

    @api.model
    def _pan_smart_search_rec_name_paths(self):
        names = self._rec_names_search or ([self._rec_name] if self._rec_name else [])
        return tuple(names)

    @api.model
    def _pan_smart_search_view_paths(self):
        return self._pan_smart_search_usable(self._pan_smart_search_view_candidates())

    @api.model
    def _pan_smart_search_dropdown_paths(self):
        return self._pan_smart_search_usable(self._pan_smart_search_rec_name_paths())

    @api.model
    def _pan_smart_search_usable(self, candidates):
        """Name field first, then the candidates this user can search, capped."""
        return list(self._pan_smart_search_usable_cached(tuple(candidates)))

    @api.model
    @tools.ormcache("self.env.uid", "candidates")
    def _pan_smart_search_usable_cached(self, candidates):
        name = self._pan_smart_search_name_field()
        paths = [name] if name else []
        # The link to an _inherits parent (product.product.product_tmpl_id)
        # repeats fields this model already has, at the cost of a second search.
        parent_links = set(self._inherits.values())
        for path in candidates:
            if (
                path not in paths
                and path.split(".")[0] not in parent_links
                and self._pan_smart_search_valid_path(path)
                and self._pan_smart_search_path_works(path)
            ):
                paths.append(path)
        return tuple(paths[:MAX_PATHS])

    @api.model
    def _pan_smart_search_path_works(self, path):
        """Build (not run) an ilike search on `path` as this user. Catches what
        the field definition does not show: website.menu.url has a search
        method that reads website.page, which a normal user may not."""
        try:
            self._search([(path, "ilike", "x")])
        except Exception:  # noqa: BLE001 - any failure means: not for this user
            _logger.debug("Smart search: skipping %s.%s for user %s", self._name, path, self.env.uid)
            return False
        return True

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    @api.model
    def _pan_smart_search_words(self, term):
        words, seen = [], set()
        for word in (term or "").split():
            if word.lower() not in seen:
                seen.add(word.lower())
                words.append(word)
        return words

    @api.model
    def _pan_smart_search_threshold(self):
        params = self.env["ir.config_parameter"].sudo()
        if hasattr(params, "get_float"):  # Odoo 20 replaced get_param with typed getters
            return params.get_float(THRESHOLD_PARAM, DEFAULT_THRESHOLD)
        value = params.get_param(THRESHOLD_PARAM)
        try:
            return float(value) if value else DEFAULT_THRESHOLD
        except ValueError:
            return DEFAULT_THRESHOLD

    @api.model
    def _pan_smart_search_fuzzy(self, word):
        return self.env.registry.has_trigram and word.isalpha() and len(word) >= FUZZY_MIN_LENGTH

    @api.model
    def _pan_smart_search_field_sql(self, query, field):
        # Odoo 19: query.table is the alias string. Odoo 20: a TableSQL that
        # resolves fields itself.
        if isinstance(query.table, str):
            return self._field_to_sql(query.table, field, query)
        return query.table[field]

    @api.model
    def _pan_smart_search_domain(self, term, paths):
        """Every word must match one of `paths` (ilike), or the name with typos."""
        words = self._pan_smart_search_words(term)
        if not words:
            return Domain.TRUE
        name = self._pan_smart_search_name_field()
        if any(self._pan_smart_search_fuzzy(word) for word in words):
            # <% uses a trigram index when there is one; the threshold is per
            # transaction, like Odoo's own website search does it.
            self.env.cr.execute(
                SQL("SELECT set_config('pg_trgm.word_similarity_threshold', %s, true)", str(self._pan_smart_search_threshold()))
            )
        word_domains = []
        for word in words:
            searched = paths if len(word) >= SHORT_WORD_LENGTH or not name else [name]
            options = [Domain(path, "ilike", word) for path in searched]
            if name and len(fold(word)) >= FOLD_MIN_LENGTH:
                # The name, accent-insensitive ("muller" finds "Müller"), with
                # typos for longer words.
                options.append(Domain("id", "in", self._pan_smart_search_name_query(word)))
            if name and self._pan_smart_search_fuzzy(word):
                # Also in the name of directly linked records: "gemini
                # furnitre" finds the orders of Gemini Furniture.
                for path in searched:
                    field = self._fields.get(path)
                    if field and field.type == "many2one":
                        comodel = self.env[field.comodel_name]
                        # Only models that take part themselves: technical
                        # comodels (ir.model.fields, ...) are large and unindexed.
                        if comodel._pan_smart_search_eligible():
                            linked = Domain("id", "in", comodel._pan_smart_search_name_query(word))
                            options.append(Domain(path, "any", linked))
            word_domains.append(Domain.OR(options))
        return Domain.AND(word_domains)

    @api.model
    def _pan_smart_search_name_expression(self, column, fname):
        """The accent-folded text smart search matches a name on. `column` is
        the column as SQL (with or without table alias); the trigram index
        cron builds its index on this same expression. For translated fields
        it is the expression Odoo indexes: all languages at once."""
        if self._fields[fname].translate:
            column = SQL("jsonb_path_query_array(%s, '$.*')::text", column)
        return fold_sql(column)

    @api.model
    def _pan_smart_search_name_text_sql(self, query, fname):
        alias = query.table if isinstance(query.table, str) else query.table._alias
        return self._pan_smart_search_name_expression(SQL.identifier(alias, fname), fname)

    @api.model
    def _pan_smart_search_name_query(self, word, fname=None):
        """Records whose `fname` (default: the name field) contains `word`,
        accent-insensitive, typos allowed for longer letter words. Written so
        it can use the trigram index the cron builds on the same expression."""
        fname = fname or self._pan_smart_search_name_field()
        field = self._fields[fname]
        if field.inherited:
            # product.product's name lives on product.template: search that
            # exact field there (with its index) and follow the _inherits link.
            # Not the parent's own name field: res.users.role inherits `name`
            # from res.groups, whose _rec_name is not stored.
            parent = self.env[field.inherited_field.model_name]
            link = self._inherits[parent._name]
            own = self.with_context(active_test=False)
            # Only the parent records of this model: website.page inherits its
            # name from ir.ui.view, and folding every view's name is slow.
            parent_query = parent._pan_smart_search_name_query(word, field.inherited_field.name)
            parent_query.add_where(SQL("%s IN (%s)", parent._pan_smart_search_field_sql(parent_query, "id"), own._search([]).subselect(link)))
            return own._search([(link, "any", Domain("id", "in", parent_query))])
        folded = fold(word)
        query = self.with_context(active_test=False)._search([])
        text = self._pan_smart_search_name_text_sql(query, fname)
        literal = SQL("%s LIKE %s", text, f"%{escape_psql(folded)}%")
        if self._pan_smart_search_fuzzy(word) and not self._pan_smart_search_name_exists(fname, literal):
            # Typos only for a word that occurs nowhere as typed, like Google's
            # "did you mean": "lasbogt" gets typo matching, "staal" does not
            # (that only added near-misses: 1,165 hits instead of 1,070, and
            # three times the time).
            options = [literal, SQL("%s <%% %s", folded, text)]
            if len(folded) >= SWAP_MIN_LENGTH:
                # One regular expression, not one LIKE per variant: separate
                # ORs made PostgreSQL drop the index and fold every row a dozen
                # times (3.4 s). Letters only (fuzzy words), so no escaping.
                options.append(SQL("%s ~ %s", text, "|".join(self._pan_smart_search_swaps(folded))))
            query.add_where(SQL("(%s)", SQL(" OR ").join(options)))
        else:
            query.add_where(literal)
        return query

    @api.model
    def _pan_smart_search_swaps(self, word):
        """`word` with each pair of neighbouring letters swapped."""
        variants = {word[:i] + word[i + 1] + word[i] + word[i + 2:] for i in range(len(word) - 1)}
        variants.discard(word)
        return sorted(variants)

    @api.model
    def _pan_smart_search_name_exists(self, fname, literal):
        """Does any record this user can see match `literal`? One indexed row."""
        probe = self._search([])
        probe.add_where(literal)
        probe.limit = 1
        self.env.cr.execute(probe.select())
        return bool(self.env.cr.fetchone())

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    @api.model
    def _pan_smart_search_term(self, domain):
        """The smart search term in a client domain, or "" if there is none."""
        if not isinstance(domain, (list, tuple)):
            return ""
        values = [
            leaf[2]
            for leaf in domain
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == "x_smart_search" and isinstance(leaf[2], str)
        ]
        return " ".join(values).strip()

    @api.model
    def _pan_smart_search_order_sql(self, query, term):
        # Plain lower(), not fold_sql(): folding every matched row for every
        # score term cost ~145 ms on a 1,070-hit word; ranking does not need it.
        name = SQL("lower(COALESCE(%s, ''))", self._pan_smart_search_field_sql(query, self._pan_smart_search_name_field()))
        code_field = self._pan_smart_search_code_field()
        code = SQL("COALESCE(%s, '')", self._pan_smart_search_field_sql(query, code_field)) if code_field else SQL("''")
        scores = [SQL("CASE WHEN %s ILIKE %s THEN %s ELSE 0 END", code, escape_psql(term), EXACT_CODE_BONUS)]
        if self.env.registry.has_trigram:
            haystack = SQL("(%s || ' ' || lower(%s))", name, code)
            scores += [SQL("word_similarity(%s, %s)", fold(word), haystack) for word in self._pan_smart_search_words(term)]
            # Tie-breaker: the name closest to the whole term, so "Plaat 3mm"
            # comes before "Plaat 3mm RVS 304 1000x2000 geslepen".
            scores.append(SQL("similarity(%s, %s)", fold(term), name))
        return SQL("%s DESC, %s", SQL(" + ").join(scores), self._pan_smart_search_field_sql(query, "id"))

    @api.model
    def _pan_smart_search_ranked(self, domain, term, offset=0, limit=None, field_names=None):
        query = self._search(domain, offset=offset, limit=limit)
        if query.is_empty():
            return self.browse()
        query.order = self._pan_smart_search_order_sql(query, term)
        return self._fetch_query(query, self._determine_fields_to_fetch(field_names))

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        """Put "Smart search" first in every eligible search view. The view is
        cached for all groups; the groups attribute hides it per user."""
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "search" and arch.tag == "search" and self._pan_smart_search_eligible():
            node = etree.Element("field", name="x_smart_search", string=self.env._("Smart search"), groups=GROUP)
            arch.insert(0, node)
        return arch, view

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        term = self._pan_smart_search_term(domain)
        if not term or order or not self._pan_smart_search_eligible():
            return super().web_search_read(domain, specification, offset, limit, order, count_limit)
        records = self._pan_smart_search_ranked(domain, term, offset, limit, specification.keys())
        values = records.web_read(specification)
        return self._format_web_search_read_results(domain, values, offset, limit, count_limit)

    @api.model
    def web_name_search(self, name, specification, domain=None, operator="ilike", limit=100):
        """Dropdowns. Hooked here rather than in name_search: some models
        (product.product) return from name_search without calling super(), and
        programmatic name_search calls (imports, API) keep Odoo's behaviour."""
        if not self._pan_smart_search_applies(name, operator):
            return super().web_name_search(name, specification, domain, operator, limit)
        pairs = self.name_search(name, domain, operator, limit)
        pairs = self._pan_smart_search_name_search(pairs, name, domain, limit)
        records = self.browse([record_id for record_id, _name in pairs])
        # Same output as Odoo's web_name_search. Like Odoo 19, skip web_read
        # when only the name is asked: some models' web_read has side effects
        # (iap.account writes, which a normal user may not).
        if len(specification) == 1 and "display_name" in specification:
            return [
                {
                    "id": record.id,
                    "display_name": record.display_name,
                    "__formatted_display_name": record.with_context(formatted_display_name=True).display_name,
                }
                for record in records
            ]
        values = records.web_read(specification)
        if "display_name" in specification:
            for value, record in zip(values, records):
                value["__formatted_display_name"] = record.with_context(formatted_display_name=True).display_name
        return values

    @api.model
    def _pan_smart_search_applies(self, name, operator):
        return (
            operator == "ilike"
            and bool(self._pan_smart_search_words(name))
            and self._pan_smart_search_eligible()
            and self._pan_smart_search_enabled()
        )

    @api.model
    def _pan_smart_search_name_search(self, result, name, domain, limit):
        """Ranked smart-search hits first, then the standard hits not among them."""
        smart = self._pan_smart_search_domain(name, self._pan_smart_search_dropdown_paths())
        ranked = self._pan_smart_search_ranked(Domain(domain or Domain.TRUE) & smart, name, limit=limit, field_names=["display_name"])
        seen = set(ranked.ids)
        merged = [(record.id, record.display_name) for record in ranked.sudo()]
        merged += [row for row in result if row[0] not in seen]
        return merged[:limit] if limit else merged
