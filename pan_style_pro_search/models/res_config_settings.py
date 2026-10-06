from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Odoo only treats a setting as a group toggle when its name starts with
    # group_, so this one cannot carry the x_ prefix.
    group_pan_smart_search = fields.Boolean(
        # Not "Smart search": every model, this one included, has a field
        # x_smart_search with that label, and Odoo warns on duplicate labels.
        string="Use smart search",
        implied_group="pan_style_pro_search.group_smart_search",
        help="Search with separate words in any order, tolerant of typos, best match "
        "first. Applies to every search bar, search dialog and dropdown.",
    )

    def set_values(self):
        super().set_values()
        if self.group_pan_smart_search:
            self.env.ref("pan_style_pro_search.ir_cron_smart_search_indexes")._trigger()
            self.env.ref("pan_style_pro_search.ir_cron_smart_search_usage")._trigger()
