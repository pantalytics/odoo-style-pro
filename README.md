# odoo-style

A modern theme for Odoo 19 (Community & Enterprise) built on the Pantalytics brand. Replaces Odoo's default UI with a clean, consumer-grade look and feel using OWL (Odoo Web Language) component overrides and a CSS design token system.

## Goals

- Modern, minimal UI inspired by tools like Linear and Vercel
- Full Pantalytics brand integration (colors, typography, spacing)
- Light and dark theme with toggle support
- Compatible with Odoo 19 Community and Enterprise
- No external CSS framework dependency — pure design tokens + SCSS

## Brand

| Token | Light | Dark |
|---|---|---|
| Accent | `#9b99ff` | `#9b99ff` |
| Background | `#ffffff` | `#001d21` |
| Background secondary | `#f5f5f5` | `#002328` |
| Text primary | `#001d21` | `#ffffff` |
| Heading font | Lexend 500 | Lexend 500 |
| Body font | Instrument Sans 400–700 | Instrument Sans 400–700 |

## Structure

```
odoo-style/
├── pan_theme/               # Main Odoo module
│   ├── __manifest__.py
│   ├── static/
│   │   ├── src/
│   │   │   ├── scss/        # Design tokens + overrides
│   │   │   ├── js/          # OWL component patches
│   │   │   └── fonts/       # Self-hosted Lexend + Instrument Sans
│   │   └── tests/
│   └── views/
│       └── assets.xml       # Asset bundle declarations
└── docs/
    └── ARCHITECTURE.md
```

## Getting Started

### Prerequisites

- Odoo 19 (Community or Enterprise)
- Python 3.11+
- Node.js (for SCSS compilation during development)

### Installation

1. Clone this repo into your Odoo addons path:
   ```bash
   git clone https://github.com/pantalytics/odoo-style /path/to/addons/odoo-style
   ```

2. Add the path to `odoo.conf`:
   ```ini
   addons_path = /path/to/addons/odoo-style,...
   ```

3. Install the `pan_theme` module via Odoo Apps or:
   ```bash
   odoo -c odoo.conf -i pan_theme
   ```

## Development

SCSS source files are compiled by Odoo's built-in asset pipeline. Run Odoo in dev mode for automatic recompilation:

```bash
odoo -c odoo.conf --dev=assets
```

## Related Repos

| Repo | Purpose |
|---|---|
| `odoo-pantalytics` | Main Pantalytics Odoo configuration |
| `pantalytics-website` | Marketing website (Astro) — source of truth for brand tokens |
| `pantalytics-brand` | Brand assets |
