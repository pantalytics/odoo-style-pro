from odoo import api, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "pan.smart.search.mixin"]

    # Same fields Odoo searches for a contact (_rec_names_search); complete_name
    # holds "Company, Person", so a company name finds its people.
    _pan_smart_search_match_fields = ("complete_name", "email", "ref", "vat", "company_registry")
    _pan_smart_search_code_field = "ref"

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        term = self._pan_smart_search_term(domain)
        if not term or order:
            return super().web_search_read(domain, specification, offset, limit, order, count_limit)
        return self._pan_smart_search_web_search_read(domain, specification, offset, limit, count_limit, term)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        result = super().name_search(name, domain, operator, limit)
        return self._pan_smart_search_name_search(result, name, domain, operator, limit)
