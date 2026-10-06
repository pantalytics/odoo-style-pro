import logging
import math

from odoo import api, fields, models
from odoo.tools import SQL

from .base import GROUP

_logger = logging.getLogger(__name__)

# Usage = how often other records referred to this one, over this period.
USAGE_DAYS = 365
# Source tables that say nothing about what people work with: technical,
# messaging and logging tables.
SKIP_SOURCE_PREFIXES = ("ir.", "mail.", "bus.", "base.", "res.users.log", "auth_", "iap.", "pan.smart.search.")
# Fields every record has; counting them ranks users by activity and companies
# by size, not by how often people pick them.
SKIP_FIELDS = {"create_uid", "write_uid", "company_id", "currency_id"}


class PanSmartSearchUsage(models.Model):
    """How often each record was used, rebuilt nightly. Read by the ranking
    with plain SQL; nobody reads it through the ORM."""

    _name = "pan.smart.search.usage"
    _description = "Smart search: usage per record"
    _log_access = False

    model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    uses = fields.Integer(required=True)
    # ln(1 + uses) / ln(1 + most uses in this model): 0..1 per model.
    score = fields.Float(required=True)

    _model_res_id_unique = models.UniqueIndex("(model, res_id)")

    @api.model
    def _pan_smart_search_rebuild(self):
        """Count, per record of every eligible model, the references to it from
        every stored many2one in the database, created in the last year.

        Generic on purpose: a product counts the sale and purchase lines that
        use it, a contact its orders, invoices and tasks, and custom models
        count as well. Child models (_inherits) add up to their parent:
        product.product usage counts for product.template too."""
        group = self.env.ref(GROUP, raise_if_not_found=False)
        if group not in self.env.ref("base.group_user").all_implied_ids:
            return
        cr = self.env.cr
        registry = self.env.registry
        targets = {name for name in registry if self.env[name]._pan_smart_search_eligible()}
        counts = {}  # (model, res_id) -> uses
        for source_name in registry:
            source = self.env[source_name]
            if (
                source._abstract
                or source._transient
                or not source._auto
                or source_name.startswith(SKIP_SOURCE_PREFIXES)
                or "create_date" not in source._fields
                or not source._fields["create_date"].store
            ):
                continue
            for field in source._fields.values():
                if (
                    field.type != "many2one"
                    or not field.store
                    or field.inherited
                    or field.company_dependent  # jsonb per company, not a column of ids
                    or field.name in SKIP_FIELDS
                    or field.comodel_name not in targets
                    or field.name in source._inherits.values()
                ):
                    continue
                cr.execute(SQL(
                    "SELECT %s, count(*) FROM %s WHERE %s IS NOT NULL AND create_date >= now() - %s * interval '1 day' GROUP BY %s",
                    SQL.identifier(field.name), SQL.identifier(source._table), SQL.identifier(field.name),
                    USAGE_DAYS, SQL.identifier(field.name),
                ))
                for res_id, uses in cr.fetchall():
                    key = (field.comodel_name, res_id)
                    counts[key] = counts.get(key, 0) + uses
        # Children add up to their _inherits parent.
        for child_name in targets:
            child = self.env[child_name]
            for parent_name, link in child._inherits.items():
                if parent_name not in targets or not child._fields[link].store:
                    # hr.employee's _inherits link to hr.version is computed.
                    continue
                child_counts = {res_id: uses for (model, res_id), uses in counts.items() if model == child_name}
                if not child_counts:
                    continue
                cr.execute(SQL(
                    "SELECT id, %s FROM %s WHERE id = ANY(%s)",
                    SQL.identifier(link), SQL.identifier(child._table), list(child_counts),
                ))
                for child_id, parent_id in cr.fetchall():
                    key = (parent_name, parent_id)
                    counts[key] = counts.get(key, 0) + child_counts[child_id]
        top = {}
        for (model, _res_id), uses in counts.items():
            top[model] = max(top.get(model, 0), uses)
        rows = [
            (model, res_id, uses, math.log1p(uses) / math.log1p(top[model]))
            for (model, res_id), uses in counts.items()
        ]
        cr.execute(SQL("DELETE FROM %s", SQL.identifier(self._table)))
        for start in range(0, len(rows), 1000):
            chunk = rows[start:start + 1000]
            cr.execute(SQL(
                "INSERT INTO %s (model, res_id, uses, score) VALUES %s",
                SQL.identifier(self._table),
                SQL(", ").join(SQL("(%s, %s, %s, %s)", *row) for row in chunk),
            ))
        _logger.info("Smart search: usage of %d records in %d models", len(rows), len(top))
