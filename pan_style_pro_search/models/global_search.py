import logging

from odoo import api, models, tools
from odoo.fields import Domain
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

MIN_TERM_LENGTH = 3
# Per keystroke (after the palette's debounce) every model costs a search, so
# only the main models, a few hits each, the best overall.
MAX_MODELS = 8
PER_MODEL = 4
MAX_RESULTS = 12


class PanSmartSearchGlobal(models.AbstractModel):
    """Search everything at once, for the command palette (Style Pro's navbar
    search). Which models: those behind the menus this user can see, most-used
    first. Nothing is configured."""

    _name = "pan.smart.search.global"
    _description = "Smart search: everything at once"

    @api.model
    def search_everywhere(self, term):
        term = (term or "").strip()
        if len(term) < MIN_TERM_LENGTH or not self.env["base"]._pan_smart_search_enabled():
            return []
        selects = []
        for model_name in self._pan_smart_search_models():
            # Typos only in each record's own name, and without the "does this
            # word occur literally?" probe: each would cost a round trip per
            # model, and the list is about the records themselves.
            model = self.env[model_name].with_context(
                pan_smart_search_own_name_only=True,
                pan_smart_search_always_fuzzy=True,
                pan_smart_search_dropdown_paths=True,
            )
            try:
                select = model._pan_smart_search_scored_sql(Domain("x_smart_search", "ilike", term), term, PER_MODEL)
            except Exception:  # noqa: BLE001 - one model must not break the palette
                _logger.debug("Smart search everywhere: skipping %s", model_name, exc_info=True)
                continue
            if select is not None:
                selects.append(SQL("(%s)", select))
        if not selects:
            return []
        # One query for all models, one relevance scale: the office chairs
        # before an employee whose job title happens to contain "office".
        self.env.cr.execute(SQL(
            "SELECT * FROM (%s) AS hits ORDER BY 3 DESC LIMIT %s",
            SQL(" UNION ALL ").join(selects), MAX_RESULTS,
        ))
        hits = self.env.cr.fetchall()
        names = {}
        for model_name in {model_name for model_name, _id, _score in hits}:
            ids = [res_id for name, res_id, _score in hits if name == model_name]
            names.update({(model_name, r.id): r.display_name for r in self.env[model_name].browse(ids)})
        return [
            {
                "model": model_name,
                "model_label": self.env["ir.model"]._get(model_name).name,
                "id": res_id,
                "display_name": names[(model_name, res_id)],
            }
            for model_name, res_id, _score in hits
        ]

    @api.model
    @tools.ormcache("self.env.uid")
    def _pan_smart_search_models(self):
        """Business-document models behind the menus this user can see,
        largest first. "Business document" = has a chatter (message_ids):
        contacts, products, orders, invoices, tasks. Not countries or units of
        measure, which are referenced everywhere but nobody looks up here."""
        menus = self.env["ir.ui.menu"].browse(self.env["ir.ui.menu"]._visible_menu_ids())
        names = []
        for menu in menus:
            action = menu.action
            if action and action._name == "ir.actions.act_window" and action.res_model not in names:
                names.append(action.res_model)
        names = [
            name for name in names
            if name in self.env and self.env[name]._pan_smart_search_eligible() and self.env[name].has_access("read")
        ]
        documents = [name for name in names if "message_ids" in self.env[name]._fields]
        names = documents or names
        # A child of an _inherits parent in the list shows the same records
        # twice (product.product next to product.template): keep the parent.
        names = [name for name in names if not set(self.env[name]._inherits) & set(names)]
        self.env.cr.execute(
            "SELECT relname, reltuples FROM pg_class WHERE relname = ANY(%s) AND relkind = 'r'",
            [[self.env[name]._table for name in names]],
        )
        size = dict(self.env.cr.fetchall())
        names.sort(key=lambda name: -size.get(self.env[name]._table, 0))
        return tuple(names[:MAX_MODELS])
