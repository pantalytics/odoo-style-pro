from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    hidden_apps = fields.Json(string="Hidden Apps", readonly=True)
    homemenu_config = fields.Json(string="Home Menu Config", readonly=True)
