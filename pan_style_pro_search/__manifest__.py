{
    "name": "Pantalytics Style Pro Search",
    "version": "19.0.2.1.0",
    "summary": "Google-style search in every Odoo model: words in any order, typos, best match first",
    "description": """
        Adds "Smart search" as the first option of every search bar, search
        dialog and dropdown. Every word must match, in any order; words of four
        letters or more also match with typos (PostgreSQL pg_trgm); results are
        ranked best match first unless the user sorts on a column.

        Nothing is configured per model: the searched fields come from each
        model's own search view, so custom fields added there are searched too.
        Standard search fields, filters, group-bys and custom filters are
        untouched.

        Installs automatically with Style Pro and is off until switched on in
        Settings > Style Pro > Search. See docs/SMART_SEARCH.md.
    """,
    "author": "Pantalytics",
    "website": "https://pantalytics.com",
    "category": "Productivity",
    "license": "LGPL-3",
    "depends": ["pan_style_pro"],
    "data": [
        "security/pan_style_pro_search_groups.xml",
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
