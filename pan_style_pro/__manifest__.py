{
    "name": "Style Pro",
    "version": "19.0.1.6.0",
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
    "data": [
        "security/ir.model.access.csv",
        "security/pan_view_rules.xml",
        "views/res_config_settings_views.xml",
    ],
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
            "pan_style_pro/static/src/scss/_home_menu_community.scss",
            "pan_style_pro/static/src/scss/_hidden_apps.scss",
            "pan_style_pro/static/src/scss/_list_columns.scss",
            "pan_style_pro/static/src/js/pan_style_service.js",
            "pan_style_pro/static/src/js/chatter_resizer.js",
            "pan_style_pro/static/src/js/patches/home_menu_community_patch.js",
            "pan_style_pro/static/src/js/patches/kanban_mobile_sortable_patch.js",
            "pan_style_pro/static/src/js/pan_view_store.js",
            "pan_style_pro/static/src/js/pan_field_list.js",
            "pan_style_pro/static/src/js/patches/list_columns_patch.js",
            "pan_style_pro/static/src/js/patches/search_view_patch.js",
            "pan_style_pro/static/src/js/home_menu_community.js",
            "pan_style_pro/static/src/js/home_menu_service.js",
            "pan_style_pro/static/src/xml/home_menu_community.xml",
            # Right after Odoo's own list template, not at the end of the
            # bundle: modules that copy web.ListRenderer (account's file-upload
            # list for sales orders and invoices, ...) only take the extensions
            # loaded before their copy.
            ("after", "web/static/src/views/list/list_renderer.xml", "pan_style_pro/static/src/xml/list_columns.xml"),
        ],
    },
    "post_init_hook": "_cleanup_stale_fields",
    "installable": True,
    "application": False,
    "auto_install": False,
}
