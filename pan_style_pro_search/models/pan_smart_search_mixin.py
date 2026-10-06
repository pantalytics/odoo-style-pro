from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.tools.sql import escape_psql

# Only words of letters this long get typo tolerance. A typo-tolerant "M8" or
# "3" matches half the catalogue, and pg_trgm splits "hp-rvs" into "hp" and
# "rvs", so codes and sizes ("3mm", "M8x20") match literally.
FUZZY_MIN_LENGTH = 4
CODE_MIN_LENGTH = 4
THRESHOLD_PARAM = "pan_style_pro_search.word_similarity_threshold"
DEFAULT_THRESHOLD = 0.5
GROUP = "pan_style_pro_search.group_smart_search"
# An exact internal reference beats any similarity score.
EXACT_CODE_BONUS = 10


class PanSmartSearchMixin(models.AbstractModel):
    """Google-style search: words in any order, typos, best match first.

    Every word of the search term must match, in any order: literally (ilike)
    in one of ``_pan_smart_search_match_fields`` (the first one, the name,
    only for short words), or, for words of
    FUZZY_MIN_LENGTH letters or more, with typos via pg_trgm word_similarity
    on the name. Without pg_trgm it degrades to literal matching only.

    A model opts in by inheriting this mixin, setting the two attributes
    below, overriding web_search_read and name_search like product.product
    does, and adding x_smart_search to its search view.
    """

    _name = "pan.smart.search.mixin"
    _description = "Smart search: words in any order, typos, best match first"

    # Stored text fields searched literally; the first is the name, which
    # also gets typo tolerance and ranks the results.
    _pan_smart_search_match_fields = ("name", "default_code")
    # Reference field: an exact match on it ranks first.
    _pan_smart_search_code_field = "default_code"

    x_smart_search = fields.Char(
        string="Smart search",
        compute="_compute_x_smart_search",
        search="_search_x_smart_search",
        help="Search with separate words in any order, tolerant of typos. "
        "Results are ranked best match first.",
    )

    def _compute_x_smart_search(self):
        self.x_smart_search = False

    def _search_x_smart_search(self, operator, value):
        if operator != "ilike" or not isinstance(value, str):
            return NotImplemented
        words = self._pan_smart_search_words(value)
        if not words:
            return Domain.TRUE
        return [("id", "in", self._pan_smart_search_ids_sql(words))]

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    @api.model
    def _pan_smart_search_enabled(self):
        """The Style Pro setting: smart search on, for every internal user."""
        return self.env.user.has_group(GROUP)

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
    def _pan_smart_search_ids_sql(self, words):
        """Query selecting the ids of the records matching every word."""
        query = self.with_context(active_test=False)._search([])
        # Skip fields this database does not have (company_registry left base in Odoo 20).
        fields_ = [field for field in self._pan_smart_search_match_fields if field in self._fields]
        texts = [self._pan_smart_search_field_sql(query, field) for field in fields_]
        threshold = self._pan_smart_search_threshold()
        for word in words:
            like = f"%{escape_psql(word)}%"
            # A short word ("62", "M8") only matches the name: inside internal
            # references like R0000062 it matches nearly at random.
            searched = texts if len(word) >= CODE_MIN_LENGTH else texts[:1]
            conditions = [SQL("%s ILIKE %s", text, like) for text in searched]
            if self._pan_smart_search_fuzzy(word):
                conditions.append(
                    SQL("word_similarity(%s, %s) >= %s", word, texts[0], threshold)
                )
            query.add_where(SQL("(%s)", SQL(" OR ").join(conditions)))
        return query

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    @api.model
    def _pan_smart_search_term(self, domain):
        """The smart search term in a client domain, or "" if there is none."""
        values = [
            leaf[2]
            for leaf in domain or []
            if isinstance(leaf, (list, tuple))
            and len(leaf) == 3
            and leaf[0] == "x_smart_search"
            and isinstance(leaf[2], str)
        ]
        return " ".join(values).strip()

    @api.model
    def _pan_smart_search_order_sql(self, query, term):
        name = self._pan_smart_search_field_sql(query, self._pan_smart_search_match_fields[0])
        code = SQL("COALESCE(%s, '')", self._pan_smart_search_field_sql(query, self._pan_smart_search_code_field))
        scores = [
            SQL("CASE WHEN %s ILIKE %s THEN %s ELSE 0 END", code, escape_psql(term), EXACT_CODE_BONUS)
        ]
        if self.env.registry.has_trigram:
            haystack = SQL("(%s || ' ' || %s)", name, code)
            scores += [
                SQL("word_similarity(%s, %s)", word, haystack)
                for word in self._pan_smart_search_words(term)
            ]
            # Tie-breaker: the name closest to the whole term, so "Plaat 3mm"
            # comes before "Plaat 3mm RVS 304 1000x2000 geslepen".
            scores.append(SQL("similarity(%s, %s)", term, name))
        return SQL("%s DESC, %s", SQL(" + ").join(scores), self._pan_smart_search_field_sql(query, "id"))

    @api.model
    def _pan_smart_search_ranked(self, domain, term, offset=0, limit=None, field_names=None):
        query = self._search(domain, offset=offset, limit=limit)
        if query.is_empty():
            return self.browse()
        query.order = self._pan_smart_search_order_sql(query, term)
        return self._fetch_query(query, self._determine_fields_to_fetch(field_names))

    # ------------------------------------------------------------------
    # Entry points, called from the concrete models' overrides (a mixin
    # method would sit behind the model's own name_search in the MRO)
    # ------------------------------------------------------------------

    @api.model
    def _pan_smart_search_web_search_read(self, domain, specification, offset, limit, count_limit, term):
        records = self._pan_smart_search_ranked(domain, term, offset, limit, specification.keys())
        values = records.web_read(specification)
        return self._format_web_search_read_results(domain, values, offset, limit, count_limit)

    @api.model
    def _pan_smart_search_name_search(self, result, name, domain, operator, limit):
        """Ranked smart-search hits first, then the standard hits not among them."""
        if operator != "ilike" or not self._pan_smart_search_words(name) or not self._pan_smart_search_enabled():
            return result
        smart_domain = Domain(domain or Domain.TRUE) & Domain("x_smart_search", "ilike", name)
        ranked = self._pan_smart_search_ranked(smart_domain, name, limit=limit, field_names=["display_name"])
        seen = set(ranked.ids)
        merged = [(record.id, record.display_name) for record in ranked.sudo()]
        merged += [row for row in result if row[0] not in seen]
        return merged[:limit] if limit else merged
