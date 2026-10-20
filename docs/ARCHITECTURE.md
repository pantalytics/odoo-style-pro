# Architecture

## Overview

`odoo-style-pro` consists of four Odoo modules that override Odoo's default UI without modifying core files:

- **`pan_style_pro`** — Community-compatible base (depends only on `web`)
- **`pan_style_pro_enterprise`** — Enterprise bridge (auto-installs when `web_enterprise` is present)
- **`pan_style_pro_knowledge`** — Public Knowledge sidebar bridge (auto-installs with `website_knowledge`). Odoo draws the same hover caret on every row and its sidebar data carries no "has children", so `/pan_style_pro/knowledge/parents` answers it for the rows on screen, a patch on `KnowledgePublicSidebar` marks each row `pan-has-children` or `pan-leaf`, and the caret shows only on the first. Not installable in CI (Enterprise); checked against odoo.pantalytics.com with the bundle swapped in
- **`pan_style_pro_search`** — Smart search in every search bar and dropdown, off by default (auto-installs with `pan_style_pro`). Works differently from the theme modules (Python on `base`, no styling); see [SMART_SEARCH.md](SMART_SEARCH.md)

Three mechanisms are used:

1. **CSS design tokens** — CSS custom properties (`--pan-*`) that replace Odoo's hardcoded colors, fonts, and spacing
2. **SCSS overrides** — targeted overrides of Odoo component styles via partials
3. **OWL component patches** — JavaScript patches that extend specific OWL components

---

## Module Structure

Assets are registered per bundle in each `__manifest__.py`; that list is the source for load order. `pan_style_pro_search` is described in [SMART_SEARCH.md](SMART_SEARCH.md).

```
pan_style_pro/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── ir_http.py
│   ├── pan_view.py
│   ├── res_config_settings.py
│   └── res_users_settings.py
├── security/
│   ├── ir.model.access.csv
│   └── pan_view_rules.xml
├── static/
│   ├── description/
│   │   ├── banner.png
│   │   └── icon.png
│   └── src/
│       ├── fonts/
│       │   ├── OFL-Murecho.txt
│       │   └── murecho-latin.woff2
│       ├── js/
│       │   ├── chatter_resizer.js
│       │   ├── home_menu_community.js
│       │   ├── home_menu_service.js
│       │   ├── pan_field_list.js
│       │   ├── pan_style_service.js
│       │   ├── pan_view_store.js
│       │   └── patches/
│       │       ├── home_menu_community_patch.js
│       │       ├── kanban_mobile_sortable_patch.js
│       │       ├── list_columns_patch.js
│       │       └── search_view_patch.js
│       ├── scss/
│       │   ├── _chatter.scss
│       │   ├── _components.scss
│       │   ├── _control_panel.scss
│       │   ├── _dropdowns.scss
│       │   ├── _fonts.scss
│       │   ├── _hidden_apps.scss
│       │   ├── _home_menu_community.scss
│       │   ├── _kanban.scss
│       │   ├── _layout.scss
│       │   ├── _list_columns.scss
│       │   ├── _login.scss
│       │   ├── _modals.scss
│       │   ├── _notifications.scss
│       │   ├── _pager.scss
│       │   ├── _settings.scss
│       │   ├── _stat_buttons.scss
│       │   ├── _statusbar.scss
│       │   ├── _tags.scss
│       │   ├── _tokens.scss
│       │   └── _typography.scss
│       └── xml/
│           ├── home_menu_community.xml
│           └── list_columns.xml
├── tests/
│   ├── __init__.py
│   └── test_pan_view.py
└── views/
    └── res_config_settings_views.xml

pan_style_pro_enterprise/
├── __init__.py
├── __manifest__.py
└── static/
    ├── description/
    │   └── icon.png
    └── src/
        ├── js/
        │   └── patches/
        │       └── home_menu_patch.js
        ├── scss/
        │   ├── _components.dark.scss
        │   ├── _home_menu.scss
        │   ├── _knowledge.scss
        │   ├── _studio.scss
        │   ├── _tags.dark.scss
        │   └── _tokens.dark.scss
        └── xml/
            └── home_menu.xml
```

---

## Design Token System

All visual values are CSS custom properties on `:root`. Dark mode overrides are in `_tokens.dark.scss` (loaded via `web.assets_web_dark`, Enterprise only).

```scss
:root {
  --pan-accent:            #5b58d8;   // dark: #9b99ff
  --pan-accent-hover:      #4a47c4;   // dark: #7370ff
  --pan-accent-foreground: #ffffff;   // dark: #001d21
  --pan-bg:                #ffffff;   // dark: #001d21
  --pan-bg-secondary:      #f4f5f7;   // dark: #002328
  --pan-text:              #001d21;   // dark: #ffffff
  --pan-text-secondary:    rgba(0, 29, 33, 0.6);
  --pan-border:            rgba(0, 0, 0, 0.08);
  --pan-font-heading:      "Murecho", sans-serif;
  --pan-font-body:         "Murecho", sans-serif;
  --pan-shadow-*:          none;      // brand: elevation is a 1px border
}
```

---

## Asset Injection

Assets are registered in `__manifest__.py` using the `assets` dict — no separate `assets.xml` file.

```python
"assets": {
    "web.assets_frontend": [
        "pan_style_pro/static/src/scss/_fonts.scss",
        "pan_style_pro/static/src/scss/_login.scss",
    ],
    "web.assets_backend": [
        "pan_style_pro/static/src/scss/_tokens.scss",
        "pan_style_pro/static/src/scss/_fonts.scss",
        "pan_style_pro/static/src/scss/_typography.scss",
        # ... all other partials, JS patches, and XML templates
    ],
},
```

Each SCSS partial is registered individually (no `main.scss` entry point).

---

## Community vs Enterprise

The module split uses Odoo's standard bridge module pattern:

| Module | `depends` | `auto_install` | What it provides |
|---|---|---|---|
| `pan_style_pro` | `["web"]` | `False` | All base styling, navbar search bar, app icons in dropdown |
| `pan_style_pro_enterprise` | `["pan_style_pro", "web_enterprise"]` | `True` | Home menu search bar, dark mode tokens |

Users install only `pan_style_pro`. On Enterprise, `pan_style_pro_enterprise` installs automatically.

**Why two modules?** Enterprise-specific code (`@web_enterprise` JS imports, `web_enterprise.HomeMenu` XML inheritance, `web.assets_web_dark` bundle) crashes on Community where those don't exist.

---

## OWL Component Patches

Patches extend existing components using `patch()` from `@web/core/utils/patch`:

```js
import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.commandService = useService("command");
    },
    onSearchBarClick() {
        this.commandService.openMainPalette({ searchValue: "" });
    },
});
```

---

## Icon Font Compatibility

Odoo uses two icon fonts: `odoo_ui_icons` (`.oi` class) and FontAwesome (`.fa` class). Our global `font-family` override on `body` breaks these unless explicitly preserved:

```scss
.oi { font-family: 'odoo_ui_icons' !important; }
.fa { font-family: 'FontAwesome' !important; }
```

This is defined in `_typography.scss`.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| CSS custom properties over SCSS variables | Runtime theme switching without recompilation |
| OWL patches over full component replacement | Upgradability — smaller diff against Odoo core |
| Self-hosted fonts | No Google CDN dependency |
| Bridge module over conditional loading | JS `import` and XML `t-inherit` can't be made conditional |
| No `main.scss` entry point | Odoo's asset pipeline handles ordering; individual registration is more explicit |
| No shadows, a 1px border | Brand rule (brand.pantalytics.com/en/product-ui) |

## Personal views (`pan.view`)

One Postgres table, `pan_view`: one row per user, model and view type (unique), plus at most one shared row per model and type (`user_id` empty, written by administrators, read by everyone). A row is a view on a model in the Airtable sense: `columns` (ordered `{name, visible, width}`), `sort`, `filter` (the search bar as facets: a predefined filter by XML name, a typed value for a search field, or a custom domain) and `group_by` as JSON. Record rules keep users on their own rows and let them read the shared ones; administrators manage all. The web client gets the user's own and the shared rows once at login (`session_info.pan_views`, `{model: {type: {mine, shared}}}`), shows mine when present, else shared, and calls `pan.view.save(res_model, values, view_type, shared)` on each change, `pan.view.reset` to drop one. Keyed on the model, not on an `ir.ui.view`, so a view follows the user into every list of that model. Only `list` is wired in the web client today; the table is ready for a name, several views per model and shared views.

Web client (`js/pan_view_store.js` holds the session copy and writes through):
- `list_columns_patch.js` on `ListRenderer`: order by dragging a column (in the table or in the column list), visible via the column list, width via the resize handle. Saved as one `columns` list; "Reset my view" in the dropdown clears it. x2many lists in forms are left alone.

### Moving columns: interaction design

Two places, one result: the table and the column list stay in sync.

**In the table**
- Hover a header: a grip (⋮⋮) shows on the left and the label moves aside for it. The grip is the sign that the column moves.
- Press the header (or the grip) and move more than 4 px: that is a drag. A press without moving stays a click and sorts, as in Odoo; the right edge still resizes.
- While dragging: the column (header and every cell) fades to 35 %, a label with its name follows the pointer, and a 2 px accent line over the table's full height marks where it lands. No line when the spot equals where it already is. The list scrolls along near its left and right edge.
- Release drops it and saves; Esc cancels and leaves no trace. The drop's click does not sort.

**In the column list** (the ⚙ at the end of the header row, after Airtable's "Hide fields")
- Every column in table order: a grip, the name, and a switch to show or hide it. Columns the view always shows carry a lock ("This list always shows this column"); hidden ones are greyed.
- Drag a row by its grip: an accent-outlined slot shows where it goes; the table follows on release, the list stays open.
- From 12 columns a search field filters the list; dragging is off while it filters (an order among a few visible rows says nothing about the hidden ones) and the list says so.
- Above the columns: whose view you edit (mine, or everyone's for administrators) and a reset.
- Property columns keep Odoo's own grouped list below.

**Implementation notes**
- The table drag is our own pointer handling, not Odoo's `useSortable`: that moves only the `<th>`, so the cells did not follow and the target was unclear.
- `list_columns.xml` is inserted right after `web/static/src/views/list/list_renderer.xml` in the bundle (`("after", ...)` in the manifest). Modules that copy `web.ListRenderer` as a primary template (account's file-upload list: sales orders, invoices) only take the extensions loaded before their copy; at the end of the bundle the columns feature was missing from those lists.
- The column list is reached through a prototype getter (`t-component="panFieldList"`), not `ListRenderer.components`: subclasses copy those at load time.
- An open dropdown is not re-rendered with fresh data when the list behind it is, so the column list applies a move or a switch from its own state and drops that state when new props differ.
- `search_view_patch.js` on `SearchModel` and `DynamicList`: when an action opens, the stored `filter` facets and `group_by` are *added* to the action's own defaults (never replacing them, so two actions on one model keep their meaning); every search bar change is saved back. A column-header sort is saved as `sort` and applies below a favorite's order, above the action's default. Dialog lists are left alone.
