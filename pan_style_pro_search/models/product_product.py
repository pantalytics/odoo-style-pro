from odoo import api, models


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "pan.smart.search.mixin"]

    _pan_smart_search_match_fields = ("name", "default_code", "barcode")

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
