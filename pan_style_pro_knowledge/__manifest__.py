{
    "name": "Style Pro — Knowledge",
    "version": "19.0.1.0.0",
    "summary": "Style Pro for the public Knowledge sidebar: a caret only where pages sit underneath",
    "description": """
        The public Knowledge sidebar draws the same caret on every row and only
        on hover. This marks the rows that have children, so the caret shows
        there and nowhere else. Auto-installs with Style Pro and website_knowledge.
    """,
    "author": "Pantalytics",
    "website": "https://pantalytics.com",
    "category": "Themes/Backend",
    "license": "LGPL-3",
    "depends": ["pan_style_pro_enterprise", "website_knowledge"],
    "data": [],
    "assets": {
        "web.assets_frontend": [
            "pan_style_pro_knowledge/static/src/js/public_sidebar_patch.js",
            "pan_style_pro_knowledge/static/src/xml/public_sidebar.xml",
        ],
        "website_knowledge.assets_public_knowledge": [
            "pan_style_pro_knowledge/static/src/scss/_public_sidebar.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": True,
}
