from odoo import models

_TOKEN_KEYS = [
    "accent_color",
    "accent_hover_color",
    "bg_color",
    "bg_secondary_color",
    "text_color",
    "text_secondary_color",
    "border_color",
    "border_strong_color",
    "navbar_bg_color",
    "navbar_border_color",
]

PAN_STYLE_PARAMS = {k: f"pan_style_pro.{k}" for k in _TOKEN_KEYS}
PAN_STYLE_DARK_PARAMS = {k: f"pan_style_pro.dark_{k}" for k in _TOKEN_KEYS}


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        get_param = self.env["ir.config_parameter"].sudo().get_param
        result["pan_style"] = {
            key: get_param(param, "")
            for key, param in PAN_STYLE_PARAMS.items()
        }
        result["pan_style_dark"] = {
            key: get_param(param, "")
            for key, param in PAN_STYLE_DARK_PARAMS.items()
        }
        return result
