# Architecture

## Overview

`odoo-style-pro` consists of two Odoo modules that override Odoo's default UI without modifying core files:

- **`pan_style_pro`** — Community-compatible base (depends only on `web`)
- **`pan_style_pro_enterprise`** — Enterprise bridge (auto-installs when `web_enterprise` is present)

Three mechanisms are used:

1. **CSS design tokens** — CSS custom properties (`--pan-*`) that replace Odoo's hardcoded colors, fonts, and spacing
2. **SCSS overrides** — targeted overrides of Odoo component styles via partials
3. **OWL component patches** — JavaScript patches that extend specific OWL components

---

## Module Structure

```
pan_style_pro/                          # Community + Enterprise base
├── __init__.py
├── __manifest__.py                     # Assets registered here (no assets.xml)
├── static/
│   ├── description/
│   │   └── icon.png
│   └── src/
│       ├── fonts/
│       │   ├── instrument-sans-400-latin.woff2
│       │   ├── instrument-sans-700-latin.woff2
│       │   └── lexend-500-latin.woff2
│       ├── scss/
│       │   ├── _tokens.scss            # Design tokens (:root)
│       │   ├── _typography.scss        # Font faces, body/heading rules, icon font fixes
│       │   ├── _layout.scss            # Navbar, list/form views
│       │   ├── _components.scss        # Buttons, inputs, cards
│       │   ├── _control_panel.scss     # Search bar, filter pills, view switcher
│       │   ├── _dropdowns.scss         # Dropdown panels and items
│       │   ├── _kanban.scss            # Kanban columns and cards
│       │   ├── _tags.scss              # Tags and badges
│       │   ├── _modals.scss            # Modal dialogs
│       │   ├── _notifications.scss     # Toast notifications
│       │   ├── _statusbar.scss         # Status bar stages
│       │   ├── _pager.scss             # Pager controls
│       │   ├── _chatter.scss           # Mail chatter
│       │   ├── _settings.scss          # Settings page
│       │   ├── _stat_buttons.scss      # Stat buttons on forms
│       │   ├── _navbar_search.scss     # Command palette search bar
│       │   └── _login.scss             # Login page (assets_frontend)
│       ├── js/
│       │   └── patches/
│       │       └── navbar_search_patch.js  # Patches NavBar to add search
│       └── xml/
│           ├── navbar_search.xml       # Search bar template (extends web.NavBar)
│           └── apps_menu.xml           # App icons in dropdown (extends web.NavBar.AppsMenu)

pan_style_pro_enterprise/               # Enterprise-only features
├── __init__.py
├── __manifest__.py                     # auto_install: True
└── static/
    └── src/
        ├── scss/
        │   ├── _home_menu.scss         # Home menu styling
        │   └── _tokens.dark.scss       # Dark mode token overrides
        ├── js/
        │   └── patches/
        │       └── home_menu_patch.js  # Patches HomeMenu with search bar
        └── xml/
            └── home_menu.xml           # Home menu search template
```

---

## Design Token System

All visual values are CSS custom properties on `:root`. Dark mode overrides are in `_tokens.dark.scss` (loaded via `web.assets_web_dark`, Enterprise only).

```scss
:root {
  --pan-accent:        #9b99ff;
  --pan-accent-hover:  #7370ff;
  --pan-bg:            #ffffff;
  --pan-bg-secondary:  #fafafa;
  --pan-text:          #001d21;
  --pan-text-secondary: rgba(0, 29, 33, 0.55);
  --pan-border:        rgba(0, 0, 0, 0.08);
  --pan-font-heading:  "Lexend", sans-serif;
  --pan-font-body:     "Instrument Sans", sans-serif;
  --pan-navbar-bg:     #ffffff;
}
```

---

## Asset Injection

Assets are registered in `__manifest__.py` using the `assets` dict — no separate `assets.xml` file.

```python
"assets": {
    "web.assets_frontend": ["pan_style_pro/static/src/scss/_login.scss"],
    "web.assets_backend": [
        "pan_style_pro/static/src/scss/_tokens.scss",
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
| Navbar search bar opens command palette | Vercel/Linear pattern — makes ⌘K discoverable |
