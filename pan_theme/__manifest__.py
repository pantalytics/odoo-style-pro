{
    "name": "Pantalytics Theme",
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
            "pan_theme/static/src/scss/_login.scss",
        ],
        "web.assets_web_dark": [
            "pan_theme/static/src/scss/_tokens.dark.scss",
        ],
        "web.assets_backend": [
            "pan_theme/static/src/scss/_tokens.scss",
            "pan_theme/static/src/scss/_typography.scss",
            "pan_theme/static/src/scss/_components.scss",
            "pan_theme/static/src/scss/_tags.scss",
            "pan_theme/static/src/scss/_layout.scss",
            "pan_theme/static/src/scss/_statusbar.scss",
            "pan_theme/static/src/scss/_dropdowns.scss",
            "pan_theme/static/src/scss/_control_panel.scss",
            "pan_theme/static/src/scss/_pager.scss",
            "pan_theme/static/src/scss/_kanban.scss",
            "pan_theme/static/src/scss/_notifications.scss",
            "pan_theme/static/src/scss/_modals.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
