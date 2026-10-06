# CLAUDE.md

## Project

`odoo-style-pro` — Style Pro by Pantalytics for Odoo 20 (Community + Enterprise). Odoo 19 lives on branch `19.0`.

Gives Odoo a modern, consumer-grade look and feel (think Linear/Vercel) using the Pantalytics brand. Three Odoo modules: `pan_style_pro` (Community-compatible base), `pan_style_pro_enterprise` (auto-install bridge for Enterprise features) and `pan_style_pro_search` (smart search in every model, off by default; see docs/SMART_SEARCH.md).

## Brand tokens (source of truth: `pantalytics-brand/src/pages/kleuren.astro`)

- **Light accent:** `#5b58d8` / hover `#4a47c4` (WCAG AA on white)
- **Dark accent:** `#9b99ff` / hover `#7370ff`
- **Light bg:** `#ffffff` / secondary `#f4f5f7`
- **Dark bg:** `#001d21` / secondary `#002328`
- **Text dark-on-light:** `#001d21` / secondary `rgba(0,29,33,0.6)`
- **Text light-on-dark:** `#ffffff` / secondary `rgba(255,255,255,0.6)`
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
| `pan_style_pro_search` | `pan_style_pro` | **Yes** | Smart search in every model: words in any order, typos (pg_trgm), best match first. Fields come from each model's search view. Off until switched on in Settings > Style Pro. See [docs/SMART_SEARCH.md](docs/SMART_SEARCH.md) |

## Conventions

### Odoo module
- Module technical name: `pan_style_pro`
- Module display name: "Style Pro" (like "Mail Pro"; the company is in `author`)
- All custom CSS/SCSS must use `--pan-` prefixed tokens — never hardcode colors or fonts. Accent tints: `rgba(var(--pan-accent-rgb), x)` (lint fails on a hardcoded accent in hex or rgb)
- OWL patches use `patch()` from `@web/core/utils/patch` — never replace components wholesale
- Enterprise-only code goes in `pan_style_pro_enterprise/`

### SCSS
- Partials prefixed with `_` (e.g. `_tokens.scss`, `_components.scss`)
- No `main.scss` entry point — each partial is registered individually in `__manifest__.py`
- Icons: Odoo 20 has no Font Awesome. Use `<i class="oi" data-icon="<material symbol>"/>` (names in `web/tooling/icons/icons_wishlist.txt`)

### JavaScript
- OWL 3: `props = useProps({...})`, `proxy()` not `useState`, `signal.ref()` not `useRef`, `this.` on every template expression
- OWL services accessed via `useService()` in `setup()`
- No jQuery — vanilla JS or OWL only
- Files named in snake_case

### Naming
- CSS classes: `pan-` prefix for any new classes (e.g. `.pan-navbar-search`)
- Do not prefix classes that purely override existing Odoo classes

## CI

`tools/ci.sh lint` before pushing — ruff, SCSS compile, asset-path and brand-token
checks. The workflows in `.github/workflows/` only wrap these scripts. Module code
changes need a manifest version bump, per module, or CI fails.

## Related repos

| Repo | Path | Purpose |
|---|---|---|
| `pantalytics-website` | `../pantalytics-website` | Brand token source of truth |
| `pantalytics-brand` | `../pantalytics-brand` | Logo and brand assets |
| `odoo-pantalytics` | `../odoo-pantalytics` | Main Pantalytics Odoo config |
| `odoo-core` | `../odoo-core` | Custom Pantalytics addons |
| `odoo-enterprise` | `../odoo-enterprise` | Odoo Enterprise source (reference) |

## What NOT to do

- Don't modify files in `odoo-enterprise` — reference only
- Don't add Tailwind or other utility CSS frameworks
- Don't use Google Fonts CDN — fonts must be self-hosted
- Don't hardcode `#9b99ff` or other brand values outside of `_tokens.scss`
- Don't add `web_enterprise` as a dependency to `pan_style_pro` — use the bridge module
