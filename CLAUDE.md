# CLAUDE.md

## Project

`odoo-style` — Pantalytics theme for Odoo 19 (Community + Enterprise).

Gives Odoo a modern, consumer-grade look and feel (think Linear/Vercel) using the Pantalytics brand. Implemented as a single Odoo module (`pan_theme`) with CSS design tokens and OWL component patches.

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

- Design tokens via CSS custom properties (`--pan-*`) on `:root` (light) and `[data-theme="dark"]`
- SCSS overrides in `pan_theme/static/src/scss/`
- OWL patches in `pan_theme/static/src/js/patches/`
- Asset injection via `pan_theme/views/assets.xml` into `web.assets_backend`

## Conventions

### Odoo module
- Module name: `pan_theme`
- All custom CSS/SCSS must use `--pan-` prefixed tokens — never hardcode colors or fonts
- OWL patches use `patch()` from `@web/core/utils/patch` — never replace components wholesale
- Enterprise-only patches go in `patches/enterprise/` and are guarded in `assets.xml`

### SCSS
- Partials prefixed with `_` (e.g. `_tokens.scss`, `_components.scss`)
- Entry point: `main.scss` imports all partials
- Override Odoo SCSS variables before `@import` where possible; use `:root` tokens for runtime switching

### JavaScript
- OWL services registered via `registry.category("services")`
- No jQuery — vanilla JS or OWL only
- Files named in snake_case

### Naming
- CSS classes: `pan-` prefix for any new classes (e.g. `.pan-btn`, `.pan-navbar`)
- Do not prefix classes that purely override existing Odoo classes

## Related repos

| Repo | Path | Purpose |
|---|---|---|
| `pantalytics-website` | `../pantalytics-website` | Brand token source of truth |
| `pantalytics-brand` | `../pantalytics-brand` | Logo and brand assets |
| `odoo-pantalytics` | `../odoo-pantalytics` | Main Pantalytics Odoo config |
| `odoo-core` | `../odoo-core` | Odoo 19 Community source (reference) |
| `odoo-enterprise` | `../odoo-enterprise` | Odoo 19 Enterprise source (reference) |

## What NOT to do

- Don't modify files in `odoo-core` or `odoo-enterprise` — reference only
- Don't add Tailwind or other utility CSS frameworks
- Don't use Google Fonts CDN — fonts must be self-hosted
- Don't hardcode `#9b99ff` or other brand values outside of `_tokens.scss`
