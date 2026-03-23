# CLAUDE.md

## Project

`odoo-style-pro` — Pantalytics Style Pro for Odoo 19 (Community + Enterprise).

Gives Odoo a modern, consumer-grade look and feel (think Linear/Vercel) using the Pantalytics brand. Two Odoo modules: `pan_style_pro` (Community-compatible base) and `pan_style_pro_enterprise` (auto-install bridge for Enterprise features).

## Brand tokens (source of truth: `pantalytics-website/src/styles/global.css`)

- **Accent:** `#9b99ff` / hover `#7370ff`
- **Dark bg:** `#001d21` / secondary `#002328`
- **Light bg:** `#ffffff` / secondary `#f5f5f5`
- **Text dark:** `#001d21` | **Text light:** `#ffffff`
- **Heading font:** Lexend 500
- **Body font:** Instrument Sans 400–700
- **Prefix all tokens with:** `--pan-`

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full details.

- Design tokens via CSS custom properties (`--pan-*`) on `:root`
- Dark mode tokens in `pan_style_pro_enterprise` via `web.assets_web_dark` bundle
- SCSS partials in `pan_style_pro/static/src/scss/`
- OWL patches in `pan_style_pro/static/src/js/patches/`
- Asset registration via `__manifest__.py` `assets` dict (no separate `assets.xml`)

## Module split

| Module | Depends | auto_install | Purpose |
|---|---|---|---|
| `pan_style_pro` | `web` | No | All Community-compatible styling, navbar search bar, app icons |
| `pan_style_pro_enterprise` | `pan_style_pro`, `web_enterprise` | **Yes** | Home menu patch, dark mode tokens |

## Conventions

### Odoo module
- Module technical name: `pan_style_pro`
- Module display name: "Pantalytics Style Pro"
- All custom CSS/SCSS must use `--pan-` prefixed tokens — never hardcode colors or fonts
- OWL patches use `patch()` from `@web/core/utils/patch` — never replace components wholesale
- Enterprise-only code goes in `pan_style_pro_enterprise/`

### SCSS
- Partials prefixed with `_` (e.g. `_tokens.scss`, `_components.scss`)
- No `main.scss` entry point — each partial is registered individually in `__manifest__.py`
- Icon fonts (`oi`, `fa`) must be preserved — see `_typography.scss`

### JavaScript
- OWL services accessed via `useService()` in `setup()`
- No jQuery — vanilla JS or OWL only
- Files named in snake_case

### Naming
- CSS classes: `pan-` prefix for any new classes (e.g. `.pan-navbar-search`)
- Do not prefix classes that purely override existing Odoo classes

## Related repos

| Repo | Path | Purpose |
|---|---|---|
| `pantalytics-website` | `../pantalytics-website` | Brand token source of truth |
| `pantalytics-brand` | `../pantalytics-brand` | Logo and brand assets |
| `odoo-pantalytics` | `../odoo-pantalytics` | Main Pantalytics Odoo config |
| `odoo-core` | `../odoo-core` | Custom Pantalytics addons |
| `odoo-enterprise` | `../odoo-enterprise` | Odoo 19 Enterprise source (reference) |

## What NOT to do

- Don't modify files in `odoo-enterprise` — reference only
- Don't add Tailwind or other utility CSS frameworks
- Don't use Google Fonts CDN — fonts must be self-hosted
- Don't hardcode `#9b99ff` or other brand values outside of `_tokens.scss`
- Don't add `web_enterprise` as a dependency to `pan_style_pro` — use the bridge module
