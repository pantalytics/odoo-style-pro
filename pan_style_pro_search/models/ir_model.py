import logging

from odoo import api, models
from odoo.tools import SQL

from .base import GROUP

_logger = logging.getLogger(__name__)

# Smart search matches names on an accent-folded expression, which Odoo's own
# indexes do not cover. Folding every row costs ~70 ms per 1,000 rows (10,810
# products: 700-950 ms per search without index, 64-87 ms with), so tables of
# this size and up get a trigram index on that exact expression.
INDEX_MIN_ROWS = 1_000


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def _pan_smart_search_ensure_indexes(self):
        """Daily cron, and right after the setting is switched on."""
        group = self.env.ref(GROUP, raise_if_not_found=False)
        if not self.env.registry.has_trigram or group not in self.env.ref("base.group_user").all_implied_ids:
            return
        for model_name in list(self.env.registry):
            self.env[model_name]._pan_smart_search_ensure_index(INDEX_MIN_ROWS)


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _pan_smart_search_ensure_index(self, min_rows):
        """Trigram index on the expression smart search matches the name on,
        if this table has at least `min_rows` rows and no such index yet."""
        if not self._auto or not self._pan_smart_search_eligible():
            return False
        fname = self._pan_smart_search_name_field()
        field = self._fields[fname]
        if field.inherited or field.company_dependent:
            # Lives on another table, which gets its own index.
            return False
        cr = self.env.cr
        cr.execute("SELECT reltuples FROM pg_class WHERE relname = %s AND relkind = 'r'", [self._table])
        row = cr.fetchone()
        if row and row[0] < 0:
            # Never analyzed yet (fresh table): PostgreSQL reports -1. Count.
            cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(self._table)))
            row = cr.fetchone()
        if not row or row[0] < min_rows:
            return False
        index = f"{self._table}__{fname}_pan_fold_trgm"[:63]
        cr.execute("SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s", [self._table, index])
        if cr.fetchone():
            return False
        expression = self._pan_smart_search_name_expression(SQL.identifier(fname), fname)
        _logger.info("Smart search: creating trigram index %s (%d rows)", index, row[0])
        cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s USING gin ((%s) gin_trgm_ops)",
            SQL.identifier(index), SQL.identifier(self._table), expression,
        ))
        return True
