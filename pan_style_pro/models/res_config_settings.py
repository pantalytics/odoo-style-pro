from odoo import fields, models

PAN_DEFAULTS = {
    # Light mode — brand guide: pantalytics-brand/src/pages/kleuren.astro
    "pan_style_pro.accent_color": "#5b58d8",
    "pan_style_pro.accent_hover_color": "#4a47c4",
    "pan_style_pro.bg_color": "#ffffff",
    "pan_style_pro.bg_secondary_color": "#f4f5f7",
    "pan_style_pro.text_color": "#001d21",
    "pan_style_pro.text_secondary_color": "rgba(0, 29, 33, 0.6)",
    "pan_style_pro.border_color": "rgba(0, 0, 0, 0.08)",
    "pan_style_pro.border_strong_color": "rgba(0, 0, 0, 0.15)",
    "pan_style_pro.navbar_bg_color": "#ffffff",
    "pan_style_pro.navbar_border_color": "rgba(0, 0, 0, 0.08)",
    # Dark mode — brand guide: pantalytics-brand/src/pages/kleuren.astro
    "pan_style_pro.dark_accent_color": "#9b99ff",
    "pan_style_pro.dark_accent_hover_color": "#7370ff",
    "pan_style_pro.dark_bg_color": "#001d21",
    "pan_style_pro.dark_bg_secondary_color": "#002328",
    "pan_style_pro.dark_text_color": "#ffffff",
    "pan_style_pro.dark_text_secondary_color": "rgba(255, 255, 255, 0.6)",
    "pan_style_pro.dark_border_color": "rgba(255, 255, 255, 0.1)",
    "pan_style_pro.dark_border_strong_color": "rgba(255, 255, 255, 0.2)",
    "pan_style_pro.dark_navbar_bg_color": "#001d21",
    "pan_style_pro.dark_navbar_border_color": "rgba(255, 255, 255, 0.1)",
}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_pan_reset_colors(self):
        set_param = self.env["ir.config_parameter"].sudo().set_param
        for key, default in PAN_DEFAULTS.items():
            set_param(key, default)
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.config.settings",
            "view_mode": "form",
            "target": "inline",
            "context": {"module": "pan_style_pro"},
        }

    # ── Light mode ──────────────────────────────────────────────────────────

    x_pan_accent_color = fields.Char(
        string="Accent Color",
        config_parameter="pan_style_pro.accent_color",
        default="#5b58d8",
    )
    x_pan_accent_hover_color = fields.Char(
        string="Accent Hover Color",
        config_parameter="pan_style_pro.accent_hover_color",
        default="#4a47c4",
    )
    x_pan_bg_color = fields.Char(
        string="Background Color",
        config_parameter="pan_style_pro.bg_color",
        default="#ffffff",
    )
    x_pan_bg_secondary_color = fields.Char(
        string="Secondary Background",
        config_parameter="pan_style_pro.bg_secondary_color",
        default="#f4f5f7",
    )
    x_pan_text_color = fields.Char(
        string="Text Color",
        config_parameter="pan_style_pro.text_color",
        default="#001d21",
    )
    x_pan_text_secondary_color = fields.Char(
        string="Secondary Text Color",
        config_parameter="pan_style_pro.text_secondary_color",
        default="rgba(0, 29, 33, 0.6)",
    )
    x_pan_border_color = fields.Char(
        string="Border Color",
        config_parameter="pan_style_pro.border_color",
        default="rgba(0, 0, 0, 0.08)",
    )
    x_pan_border_strong_color = fields.Char(
        string="Strong Border Color",
        config_parameter="pan_style_pro.border_strong_color",
        default="rgba(0, 0, 0, 0.15)",
    )
    x_pan_navbar_bg_color = fields.Char(
        string="Navbar Background",
        config_parameter="pan_style_pro.navbar_bg_color",
        default="#ffffff",
    )
    x_pan_navbar_border_color = fields.Char(
        string="Navbar Border",
        config_parameter="pan_style_pro.navbar_border_color",
        default="rgba(0, 0, 0, 0.08)",
    )

    # ── Dark mode ───────────────────────────────────────────────────────────

    x_pan_dark_accent_color = fields.Char(
        string="Dark Accent Color",
        config_parameter="pan_style_pro.dark_accent_color",
        default="#9b99ff",
    )
    x_pan_dark_accent_hover_color = fields.Char(
        string="Dark Accent Hover Color",
        config_parameter="pan_style_pro.dark_accent_hover_color",
        default="#7370ff",
    )
    x_pan_dark_bg_color = fields.Char(
        string="Dark Background Color",
        config_parameter="pan_style_pro.dark_bg_color",
        default="#001d21",
    )
    x_pan_dark_bg_secondary_color = fields.Char(
        string="Dark Secondary Background",
        config_parameter="pan_style_pro.dark_bg_secondary_color",
        default="#002328",
    )
    x_pan_dark_text_color = fields.Char(
        string="Dark Text Color",
        config_parameter="pan_style_pro.dark_text_color",
        default="#ffffff",
    )
    x_pan_dark_text_secondary_color = fields.Char(
        string="Dark Secondary Text Color",
        config_parameter="pan_style_pro.dark_text_secondary_color",
        default="rgba(255, 255, 255, 0.6)",
    )
    x_pan_dark_border_color = fields.Char(
        string="Dark Border Color",
        config_parameter="pan_style_pro.dark_border_color",
        default="rgba(255, 255, 255, 0.1)",
    )
    x_pan_dark_border_strong_color = fields.Char(
        string="Dark Strong Border Color",
        config_parameter="pan_style_pro.dark_border_strong_color",
        default="rgba(255, 255, 255, 0.2)",
    )
    x_pan_dark_navbar_bg_color = fields.Char(
        string="Dark Navbar Background",
        config_parameter="pan_style_pro.dark_navbar_bg_color",
        default="#001d21",
    )
    x_pan_dark_navbar_border_color = fields.Char(
        string="Dark Navbar Border",
        config_parameter="pan_style_pro.dark_navbar_border_color",
        default="rgba(255, 255, 255, 0.1)",
    )
