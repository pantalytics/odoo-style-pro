from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Odoo only treats a setting as a group toggle when its name starts with
    # group_, so this one cannot carry the x_ prefix.
    group_pan_smart_search = fields.Boolean(
        string="Smart product search",
        implied_group="pan_style_pro_search.group_smart_search",
        help="Search products with separate words in any order, tolerant of typos, "
        "best match first. Applies to the product search bar and product dropdowns.",
    )
