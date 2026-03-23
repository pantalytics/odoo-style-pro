{
    "name": "Pantalytics Style Pro",
    "version": "19.0.1.0.0",
    "summary": "Modern Pantalytics brand theme for Odoo backend",
    "description": """
        Gives Odoo a modern, consumer-grade look and feel using the Pantalytics brand.
        Inspired by Linear/Vercel design language.
    """,
    "author": "Pantalytics",
    "website": "https://pantalytics.com",
    "category": "Themes/Backend",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_frontend": [
            "pan_style_pro/static/src/scss/_login.scss",
        ],
        "web.assets_backend": [
            "pan_style_pro/static/src/scss/_tokens.scss",
            "pan_style_pro/static/src/scss/_typography.scss",
            "pan_style_pro/static/src/scss/_components.scss",
            "pan_style_pro/static/src/scss/_tags.scss",
            "pan_style_pro/static/src/scss/_layout.scss",
            "pan_style_pro/static/src/scss/_statusbar.scss",
            "pan_style_pro/static/src/scss/_dropdowns.scss",
            "pan_style_pro/static/src/scss/_control_panel.scss",
            "pan_style_pro/static/src/scss/_pager.scss",
            "pan_style_pro/static/src/scss/_kanban.scss",
            "pan_style_pro/static/src/scss/_notifications.scss",
            "pan_style_pro/static/src/scss/_modals.scss",
            "pan_style_pro/static/src/scss/_chatter.scss",
            "pan_style_pro/static/src/scss/_settings.scss",
            "pan_style_pro/static/src/scss/_stat_buttons.scss",
            "pan_style_pro/static/src/scss/_navbar_search.scss",
            "pan_style_pro/static/src/js/patches/navbar_search_patch.js",
            "pan_style_pro/static/src/xml/navbar_search.xml",
            "pan_style_pro/static/src/xml/apps_menu.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
