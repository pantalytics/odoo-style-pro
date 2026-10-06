{
    "name": "Pantalytics Style Pro Search",
    "version": "19.0.1.1.0",
    "summary": "Google-style product search: words in any order, typos, best match first",
    "description": """
        Adds a "Smart search" field to the product search bar and to product
        dropdowns. Every word must match somewhere in the name, internal
        reference or barcode, in any order. Words of four letters or more also
        match with typos (PostgreSQL pg_trgm word similarity). Results are
        ranked best match first unless the user sorts on a column.

        The standard search fields, filters, group-bys and custom filters are
        untouched: smart search is one extra field next to them.

        Installs automatically with Style Pro when Products is present, and is
        off until switched on in Settings > Style Pro > Smart product search.
    """,
    "author": "Pantalytics",
    "website": "https://pantalytics.com",
    "category": "Productivity",
    "license": "LGPL-3",
    "depends": ["pan_style_pro", "product"],
    "data": [
        "security/pan_style_pro_search_groups.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
