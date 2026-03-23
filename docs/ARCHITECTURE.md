# Architecture

## Overview

`odoo-style` is a single Odoo module (`pan_theme`) that overrides Odoo's default UI without modifying core files. It uses three mechanisms:

1. **CSS design tokens** — CSS custom properties that replace Odoo's hardcoded colors, fonts, and spacing
2. **SCSS overrides** — targeted overrides of Odoo's SCSS variables and component styles
3. **OWL component patches** — JavaScript patches that extend or replace specific OWL components (e.g. navbar, buttons, form views)

---

## Design Token System

All visual values are defined as CSS custom properties on `:root` and `[data-theme="dark"]`. This is the single source of truth for both themes.

```scss
:root {
  // Light theme (default)
  --pan-accent:        #9b99ff;
  --pan-accent-hover:  #7370ff;
  --pan-bg:            #ffffff;
  --pan-bg-secondary:  #f5f5f5;
  --pan-text:          #001d21;
  --pan-text-secondary: rgba(0, 29, 33, 0.6);
  --pan-border:        rgba(0, 29, 33, 0.1);

  --pan-font-heading:  "Lexend", sans-serif;
  --pan-font-body:     "Instrument Sans", sans-serif;

  --pan-radius-sm:     0.25rem;
  --pan-radius-md:     0.5rem;
  --pan-radius-lg:     0.75rem;
}

[data-theme="dark"] {
  --pan-bg:            #001d21;
  --pan-bg-secondary:  #002328;
  --pan-text:          #ffffff;
  --pan-text-secondary: rgba(255, 255, 255, 0.6);
  --pan-border:        rgba(255, 255, 255, 0.1);
}
```

The `data-theme` attribute is toggled on `<html>` by an OWL service that respects:
1. User preference stored in `localStorage`
2. System preference via `prefers-color-scheme`

---

## Module Structure

```
pan_theme/
├── __init__.py
├── __manifest__.py
├── static/
│   └── src/
│       ├── fonts/
│       │   ├── lexend-500-latin.woff2
│       │   ├── lexend-500-latin-ext.woff2
│       │   ├── instrument-sans-latin.woff2
│       │   └── instrument-sans-latin-ext.woff2
│       ├── scss/
│       │   ├── _tokens.scss        # CSS custom property definitions
│       │   ├── _reset.scss         # Normalize on top of Odoo's reset
│       │   ├── _typography.scss    # Font faces + heading/body rules
│       │   ├── _components.scss    # Button, input, card overrides
│       │   ├── _layout.scss        # Navbar, sidebar, form view layout
│       │   └── main.scss           # Entry point — imports all partials
│       └── js/
│           ├── theme_service.js    # Light/dark toggle OWL service
│           ├── theme_toggle.js     # Navbar toggle button component
│           └── patches/
│               └── web/            # OWL patches per Odoo app
└── views/
    └── assets.xml                  # Injects assets into Odoo bundles
```

---

## Asset Injection

Odoo 19 uses a bundle-based asset system. Assets are declared in `assets.xml`:

```xml
<odoo>
  <template id="pan_theme_assets" inherit_id="web.assets_backend">
    <xpath expr="." position="inside">
      <!-- Fonts -->
      <link rel="stylesheet" href="/pan_theme/static/src/scss/main.scss"/>
      <script type="text/javascript" src="/pan_theme/static/src/js/theme_service.js"/>
      <script type="text/javascript" src="/pan_theme/static/src/js/theme_toggle.js"/>
    </xpath>
  </template>
</odoo>
```

This injects into `web.assets_backend` so all backend views are styled. A separate template targets `web.assets_frontend` for the portal/website.

---

## OWL Component Patches

OWL patches extend existing components without replacing them. Example pattern:

```js
// patches/web/action_manager.js
import { patch } from "@web/core/utils/patch";
import { ActionManager } from "@web/webclient/action_manager/action_manager";

patch(ActionManager.prototype, {
  // override specific methods
});
```

Patches live in `static/src/js/patches/` organized by Odoo app (e.g. `web/`, `mail/`, `account/`).

---

## Theme Toggle

The theme service (`theme_service.js`) is an OWL service registered in the service registry. It:

- Reads initial theme from `localStorage` → falls back to `prefers-color-scheme`
- Sets `document.documentElement.dataset.theme` to `"light"` or `"dark"`
- Exposes a `toggle()` method consumed by the navbar toggle component

---

## Community vs Enterprise

The module targets both editions:

- **Community:** full support, all overrides apply
- **Enterprise:** additional patch files in `patches/enterprise/` override enterprise-specific components (e.g. dashboard widgets, studio)

Enterprise-only patches are guarded so they load only when the relevant module is installed:

```xml
<template id="pan_theme_enterprise" inherit_id="web_enterprise.assets_backend"
          active="False">
  ...
</template>
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| CSS custom properties over SCSS variables | Runtime theme switching without recompilation |
| OWL patches over full component replacement | Upgradability — smaller diff against Odoo core |
| Self-hosted fonts | No Google CDN dependency, consistent with `pantalytics-website` |
| `data-theme` on `<html>` | Standard pattern, works with CSS cascade |
| No external CSS framework (Tailwind etc.) | Odoo's asset pipeline makes utility-class frameworks impractical; design tokens give the same flexibility |
