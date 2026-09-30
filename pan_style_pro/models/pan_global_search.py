import re

from odoo import api, models
from odoo.fields import Domain
from odoo.tools import html2plaintext

# Models the home screen search looks in, in display order. Only the ones that
# are installed and readable by the current user are searched.
SEARCH_MODELS = [
    "res.partner",
    "product.template",
    "sale.order",
    "purchase.order",
    "account.move",
    "crm.lead",
    "project.project",
    "project.task",
    "helpdesk.ticket",
    "stock.picking",
    "mrp.production",
    "hr.employee",
]
# Where a model's own search fields miss what people type, e.g. product codes.
SEARCH_FIELDS = {
    "product.template": ["name", "default_code", "barcode"],
}
RECORDS_PER_MODEL = 5
MESSAGE_LIMIT = 5
MIN_LENGTH = 2


class PanGlobalSearch(models.AbstractModel):
    _name = "pan.global.search"
    _description = "Home screen search over records and messages"

    @api.model
    def _pan_words(self, query):
        return [w for w in re.split(r"\s+", query or "") if w]

    @api.model
    def _pan_words_domain(self, words, fields):
        """Every word must match, in any order, in at least one of the fields.

        "rvs plaat 3mm" finds "Plaat 3mm RVS 304". This is the one place to make
        smarter (typos, ranking) and every caller gets it.
        """
        return Domain.AND(
            Domain.OR(Domain(field, "ilike", word) for field in fields)
            for word in words
        )

    @api.model
    def search_all(self, query):
        words = self._pan_words(query)
        if len("".join(words)) < MIN_LENGTH:
            return {"records": [], "messages": []}
        return {
            "records": self._pan_search_records(words),
            "messages": self._pan_search_messages(words),
        }

    @api.model
    def _pan_search_records(self, words):
        groups = []
        for model_name in SEARCH_MODELS:
            if model_name not in self.env:
                continue
            Model = self.env[model_name]
            if not Model.has_access("read"):
                continue
            fields = (
                SEARCH_FIELDS.get(model_name)
                or Model._rec_names_search
                or [Model._rec_name or "display_name"]
            )
            records = Model.search(
                self._pan_words_domain(words, fields), limit=RECORDS_PER_MODEL
            )
            if records:
                groups.append({
                    "model": model_name,
                    "label": self.env["ir.model"]._get(model_name).name,
                    "records": [{"id": r.id, "name": r.display_name} for r in records],
                })
        return groups

    @api.model
    def _pan_search_messages(self, words):
        if "mail.message" not in self.env:
            return []
        # mail.message filters on access to the linked document by itself.
        domain = Domain.AND([
            self._pan_words_domain(words, ["body", "subject"]),
            Domain("message_type", "in", ["comment", "email"]),
            Domain("model", "!=", False),
            Domain("res_id", "!=", False),
        ])
        messages = self.env["mail.message"].search(domain, limit=MESSAGE_LIMIT)
        return [{
            "id": m.id,
            "model": m.model,
            "res_id": m.res_id,
            "record_name": m.record_name or "",
            "author": m.author_id.display_name or m.email_from or "",
            "snippet": " ".join(html2plaintext(m.body or m.subject or "").split())[:120],
        } for m in messages]
