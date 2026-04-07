{
    "name": "Pantalytics Style Pro — Enterprise",
    "version": "19.0.1.1.0",
    "summary": "Enterprise extensions for Pantalytics Style Pro (home menu, dark mode)",
    "description": """
        Adds Enterprise-specific styling: home menu search bar, dark mode tokens.
        Auto-installs when both pan_style_pro and web_enterprise are present.
    """,
    "author": "Pantalytics",
    "website": "https://pantalytics.com",
    "category": "Themes/Backend",
    "license": "LGPL-3",
    "depends": ["pan_style_pro", "web_enterprise"],
    "data": [],
    "assets": {
        "web.assets_web_dark": [
            "pan_style_pro_enterprise/static/src/scss/_tokens.dark.scss",
            "pan_style_pro_enterprise/static/src/scss/_tags.dark.scss",
            "pan_style_pro_enterprise/static/src/scss/_components.dark.scss",
        ],
        "web.assets_backend": [
            ("remove", "pan_style_pro/static/src/js/home_menu_service.js"),
            ("remove", "pan_style_pro/static/src/js/home_menu_community.js"),
            ("remove", "pan_style_pro/static/src/xml/home_menu_community.xml"),
            ("remove", "pan_style_pro/static/src/js/patches/home_menu_community_patch.js"),
            ("remove", "pan_style_pro/static/src/scss/_home_menu_community.scss"),
            "pan_style_pro_enterprise/static/src/scss/_home_menu.scss",
            "pan_style_pro_enterprise/static/src/js/patches/home_menu_patch.js",
            "pan_style_pro_enterprise/static/src/xml/home_menu.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": True,
}
