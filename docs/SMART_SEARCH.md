# Smart search (`pan_style_pro_search`)

Google-style search for every Odoo model: type words in any order, with typos,
and get the best match first. Standard Odoo search stays as it is; smart search
is one extra option on top of it.

```
"bout 70 m5"         -> Bout M5 x 70, Inbusbout M5 x 70 - 8.8          (products)
"schoohoven hartog"  -> Blonkstaal Schoonhoven BV, Richard Hartog     (contacts)
"lasbogt rvs"        -> Lasbocht 48.3x3.00 RVS, ...                   (products)
"gemini furnitre"    -> the sales orders of Gemini Furniture          (typo in the linked customer)
```

## Switching it on

Settings > Style Pro > Search > **Use smart search**. Off by default.

- The module installs automatically with `pan_style_pro`. Installing Style Pro
  never changes how search behaves until someone ticks the box.
- The box applies to all internal users at once. It is a standard Odoo group
  toggle (`group_pan_smart_search` implies `group_smart_search` on
  `base.group_user`); nothing is installed or uninstalled.
- A browser that is already open shows the change from its second reload. The
  web client serves its cached view once more, like every Odoo group setting.

## What the user sees

| Where | With smart search on |
|---|---|
| Search bar of a list, kanban or "Search: ..." dialog | **Smart search** is the first option in the autocomplete, so Enter uses it. "Product", "Name", filters, group-bys, favourites and custom filters are untouched and combine with it as usual. |
| Results | Best match first, unless the user clicks a column to sort. |
| Many2one dropdowns (a product on a quotation line, a contact on a task) | Smart matches first, ranked, then the standard matches that were not among them. |

## How it decides what to search

Nothing is configured per model. Each model tells us itself:

**Search bar: the model's own search view.** Every `<field>` of the default
search view counts. Where a field has a `filter_domain`, the field paths in it
count instead, so linked fields come along:

```xml
<!-- product.template: the "Product" field -->
<field name="name" filter_domain="['|', '|', '|',
    ('default_code', 'ilike', self), ('product_variant_ids.default_code', 'ilike', self),
    ('name', 'ilike', self), ('barcode', 'ilike', self)]"/>
```

gives `default_code`, `product_variant_ids.default_code`, `name`, `barcode`.

So **a field a customer adds to the search view, via Studio or custom code, is
searched by smart search automatically.** That is also the way to add a field:
put it in the search view. To keep a field out, keep it out of the search view.

A path is used only if the current user can search it:

- every field on the path exists and is searchable (stored, or has a search
  method; Odoo's own `searchable` flag),
- the user may read the field (`groups`) and the linked models,
- the last field is `char`, `many2one`, `many2many` or `one2many`. Text and
  html fields (descriptions, mail bodies) are left out: noise, and slow.

This check matters: every word is OR-ed over all paths, so one path the user
cannot search would break the whole search, not just that field.

At most 15 paths per model (`MAX_PATHS`), name field first.

**Dropdowns: Odoo's dropdown fields.** `_rec_names_search` if the model has it,
else `_rec_name`. That is what Odoo itself searches in that dropdown, and it
keeps a dropdown fast on every keystroke.

**Name field** (typos, ranking): `complete_name` if the model stores one
("Company, Person" on contacts, "All / Saleable" on categories), else
`_rec_name`.

**Reference field** (exact match ranks first): the first of `default_code`,
`ref`, `code`, `barcode` the model has.

**Which models:** every model with a name field, except abstract, transient
and technical `ir.*` models.

## How a search term matches

The term is split into words. **Every word must match**, in any order:

| Word | Matches |
|---|---|
| 4+ characters | literally (`ilike`) in any searched path, or, if only letters, with typos in the name or in the name of a directly linked record (a many2one in the searched paths: customer, project, salesperson) |
| 1-3 characters (`m5`, `70`, `rvs`) | literally in the name only. In a reference like `R0000062` or an email address, `62` matches nearly at random. |
| contains digits or punctuation (`3mm`, `M8x20`, `hp-rvs`) | literally only. pg_trgm splits `hp-rvs` into `hp` + `rvs` and would match every RVS product. |

Typos use PostgreSQL `pg_trgm`: `word <% name` (word similarity, default
threshold 0.5). Without `pg_trgm` in the database smart search still works,
literally only.

Swapped letters (`pijpbuegel`) are not caught at 0.5; at 0.4 they are, but then
`moer m8` also finds anchors and `slang` finds chains. Measured on 10,810 real
product names; 0.5 is the default.

## Ranking

Highest score first, then id:

1. reference equals the term (case-insensitive): +10
2. per word: word similarity with "name + reference"
3. tie-breaker: similarity of the whole term with the name, so "Plaat 3mm"
   comes before "Plaat 3mm RVS 304 1000x2000 geslepen"

Applies to list and kanban (`web_search_read`) when the domain has a smart
search term and the user did not sort on a column, and to dropdowns.

## Performance

Measured server-side.

| Data | Standard, 1 word | Smart |
|---|---|---|
| 10,806 products (JMB) | 35 ms | 129 ms (3 words, 7 fields) |
| 5,123 contacts (JMB) | 10 ms | 102 ms (2 words, 8 fields) |
| 500,000 contacts, no trigram index | 106 ms | 261 ms literal; typo match **563 ms per word** |
| 500,000 contacts, trigram index on the name | 1 ms | typo match **7 ms** |

Two things keep typo matching fast:

- **Translated names** (jsonb, e.g. the product name) are matched against the
  same expression Odoo's own trigram index uses (`index="trigram"`:
  `jsonb_path_query_array(name, '$.*')::text`), so that index is used.
  10,810 products: 44 ms -> 1.4 ms per typo word.
- **Other names on large tables** get a trigram index from the module: a daily
  cron (**Smart search: trigram indexes on large tables**, also triggered when
  the setting is switched on) adds a GIN trigram index on the name field of
  every eligible table above 50,000 rows (`INDEX_MIN_ROWS`) that has none.

A name inherited from a parent table (`product.product` gets its name from
`product.template`) is matched on the parent, with its index. The link to an
`_inherits` parent (`product_tmpl_id`) is never searched as a separate path: it
repeats fields the model already has.

End result on 10,810 real products (local, full search bar request including
the count Odoo adds): `product.product` 207 -> 58 ms, `product.template`
146 -> 83 ms.

Sweep over every eligible model of a demo database with 20 apps (250 models
as admin, 177 as a regular user): smart search works wherever standard search
works, no model above 300 ms except `iap.account`, whose own `web_read` calls
the IAP server.

## Settings

| Where | What | Default |
|---|---|---|
| Settings > Style Pro > Search | Use smart search | off |
| System parameter `pan_style_pro_search.word_similarity_threshold` | Typo tolerance: lower finds more, with more noise | 0.5 |

## Known behaviour

- Many2one paths match the linked record's name *and* what Odoo searches on it.
  Searching a company's reference on contacts also finds that company's
  people; the company itself ranks first.
- Programmatic `name_search` (imports, API) is untouched: only the web client's
  dropdowns (`web_name_search`) use smart search.
- A model whose own web methods fail for a user fails the same with smart search
  on or off (e.g. `iap.account` for non-admins in Odoo 19).

## Code map

| File | What |
|---|---|
| `models/base.py` | Everything above, on `base`: the `x_smart_search` field and its search method, field discovery, matching, ranking, the search view injection (`_get_view`), `web_search_read`, `web_name_search` |
| `models/ir_model.py` | Trigram index cron |
| `models/res_config_settings.py` | The setting |
| `security/pan_style_pro_search_groups.xml` | The group the setting implies |
| `tests/` | Products, contacts, generic (a model without configuration, a field added to a search view, setting off, index) |

Field discovery (`_pan_smart_search_view_candidates`) is cached per model in
the `templates` cache, which Odoo clears whenever a view changes.

### Odoo 19 and 20

Same code on both branches, with small shims: `query.table` is an alias string
in 19 and a `TableSQL` in 20; `ir.config_parameter.get_param` became typed
getters in 20 (the 20.0 branch uses `get_float` only); `company_registry` left
`res.partner` in 20 (paths that do not exist are skipped anyway). Odoo 18 is
not supported (no `Domain` class).

## Testing

```bash
tools/ci.sh install   # installs pan_style_pro, pan_style_pro_search and product, runs the tests
```

To check a whole database: switch the setting on and, per eligible model, run a
smart search for a word from one of its own records. See the sweep in
pantalytics/odoo-style-pro#19.
