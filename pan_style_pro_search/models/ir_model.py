import logging

from odoo import api, models
from odoo.tools import SQL

from .base import GROUP

_logger = logging.getLogger(__name__)

# Below this many rows a typo search without index takes milliseconds; above
# it a trigram index on the name field keeps it fast (measured: 500k contacts,
# 563 ms without index, 7 ms with).
INDEX_MIN_ROWS = 50_000


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
        """Trigram index on the name field smart search fuzzy-matches, if this
        table has at least `min_rows` rows and no such index yet."""
        if not self._auto or not self._pan_smart_search_eligible():
            return False
        fname = self._pan_smart_search_name_field()
        field = self._fields[fname]
        if field.inherited or field.translate or field.company_dependent:
            # Lives on another table, or is stored as jsonb; Odoo indexes
            # translated names itself where it matters (index='trigram'),
            # e.g. the product name.
            return False
        cr = self.env.cr
        cr.execute("SELECT reltuples FROM pg_class WHERE relname = %s AND relkind = 'r'", [self._table])
        row = cr.fetchone()
        if not row or row[0] < min_rows:
            return False
        cr.execute(
            "SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexdef ILIKE %s",
            [self._table, f"%({fname} gin_trgm_ops)%"],
        )
        if cr.fetchone():
            return False
        index = f"{self._table}__{fname}_pan_trgm"[:63]
        _logger.info("Smart search: creating trigram index %s (%d rows)", index, row[0])
        cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s USING gin (%s gin_trgm_ops)",
            SQL.identifier(index), SQL.identifier(self._table), SQL.identifier(fname),
        ))
        return True
