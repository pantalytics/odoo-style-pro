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
| "Search More..." under a dropdown | The dialog opens with a **Smart search: term** filter holding the same matches as the dropdown. Odoo's own "Quick search" used a plain name_search and found nothing for words in another order. |

## Search everything at once

Style Pro's navbar search (and Ctrl+K, then `/`) opens Odoo's command palette
on menus. With smart search on, from 3 characters it also shows **Records**:
the best matches across the user's main models, ranked on one relevance scale,
at most 4 per model and 12 in total; Enter opens the record.

```
/gemini furnitre  ->  Gemini Furniture · Contact
                      Gemini Furniture, Oscar Morgan · Contact
                      [FURN_7777] Office Chair · Product      (supplier Gemini Furniture)
                      S00004 · Sales Order
```

Which models, without configuration: the window actions behind the menus this
user can see, limited to business documents (models with a chatter:
contacts, products, orders, invoices, tasks; not countries or units of
measure), a child of an `_inherits` parent dropped in favour of the parent
(products, not also variants), largest tables first, at most 8. Cached per
user. Typos are matched on each record's own name only here (not through
linked records), and the "does this word occur literally?" probe is cached per
request, so a search over 8 models costs ~27 SQL queries instead of 68. Demo
database with 20 apps: 61-102 ms per keystroke (after the palette's debounce).

Code: `models/global_search.py` (`pan.smart.search.global.search_everywhere`),
`static/src/js/smart_search_command_provider.js`.

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

- the user may read the models behind related and inherited fields too,
- and building an `ilike` search on the path actually works for this user.
  This last check catches what a field definition does not show
  (`website.menu.url` has a search method that reads `website.page`). It runs
  once per user and model, then the result is cached.

These checks matter: every word is OR-ed over all paths, so one path the user
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
| 4+ characters | literally (`ilike`) in any searched path; in the name accent-insensitive; and, if only letters, with typos in the name or in the name of a directly linked record (a many2one in the searched paths: customer, project, salesperson) |
| 3 characters (`rvs`) | literally in the name only, accent-insensitive |
| 1-2 characters (`m5`, `70`) | literally in the name only, accent-sensitive (a trigram index cannot serve patterns this short). In a reference like `R0000062` or an email address, `62` matches nearly at random. |
| contains digits or punctuation (`3mm`, `M8x20`, `hp-rvs`) | literally only. pg_trgm splits `hp-rvs` into `hp` + `rvs` and would match every RVS product. |

Names are matched **accent-insensitive**: "muller" finds "Müller", "spolka"
finds "SPÓŁKA", "köhler" finds "Kohler". Both sides are folded the same way
(PostgreSQL `translate()` with one table of accented Latin letters, both cases,
mirrored in Python), so this works without the `unaccent` extension, which
CloudPepper databases do not have, and it only affects smart search: standard
Odoo search keeps its own behaviour.

Typos use PostgreSQL `pg_trgm` on that folded name: `word <% name` (word
similarity, default threshold 0.5), and only for a word that occurs nowhere as
typed, like Google's "did you mean": "lasbogt" gets typo matching, "staal"
does not. For a common word typo matching only added near-misses (1,165 hits
instead of 1,070) at three times the cost. Without `pg_trgm` in the database smart search still works,
literally only.

Swapped letters (`pijpbuegel`, `verloposchakel`) are not caught by trigram
similarity at 0.5 (at 0.4 they are, but then `moer m8` also finds anchors and
`slang` finds chains). So a word of 5+ letters that occurs nowhere as typed
also tries every variant with two neighbouring letters swapped, as one regular
expression on the folded name (`text ~ 'pijpbeugel|ipjpbuegel|...'`), which
the trigram index serves: 25-65 ms. One `LIKE` per variant made PostgreSQL drop
the index (3.4 s).

## Ranking

Highest score first, then id:

1. reference equals the term (case-insensitive): +10
2. per word: word similarity with "name + reference"
3. tie-breaker: similarity of the whole term with the name, so "Plaat 3mm"
   comes before "Plaat 3mm RVS 304 1000x2000 geslepen"

4. usage, as a tie-breaker: up to +0.5 (`USAGE_WEIGHT`) for records people
   actually use, so among equally good text matches the product that is sold
   most comes first. Each word adds up to 1, so a clearly better text match
   still wins.

Applies to list and kanban (`web_search_read`) when the domain has a smart
search term and the user did not sort on a column, and to dropdowns.

### Usage

A nightly cron (**Smart search: usage statistics for ranking**, also triggered
when the setting is switched on and by the upgrade that introduced it) counts,
for every record of every eligible model, how often other records referred to
it in the last 365 days, through every stored many2one in the database. A
product counts the sale, purchase and stock lines that use it, a contact its
orders, invoices and tasks; custom models count too, nothing is configured.
Child models add up to their `_inherits` parent (variant usage counts for the
product). Left out: technical, messaging and logging tables (`ir.*`, `mail.*`,
...), the fields every record has (`create_uid`, `company_id`, ...), and
company-dependent fields (jsonb). The result is `ln(1 + uses)`, scaled to 0..1
per model, in `pan.smart.search.usage`.

Demo database: rebuild 0.2 s; "desk" now lists the desks that are sold first,
"table" and "office chair" keep their exact name match on top.

## Performance

Measured server-side.

| Data | Standard, 1 word | Smart |
|---|---|---|
| 10,806 products (JMB) | 35 ms | 129 ms (3 words, 7 fields) |
| 5,123 contacts (JMB) | 10 ms | 102 ms (2 words, 8 fields) |
| 500,000 contacts, no trigram index | 106 ms | 261 ms literal; typo match **563 ms per word** |
| 500,000 contacts, trigram index on the name | 1 ms | typo match **7 ms** |

Name matching (accents and typos) runs on one expression,
`translate(lower(<name>), <accented>, <plain>)`, for translated names on the
text Odoo indexes (`jsonb_path_query_array(name, '$.*')::text`). Folding every
row is expensive (10,810 products: 700-950 ms per search), so that expression
gets its own GIN trigram index:

- a daily cron (**Smart search: trigram indexes on large tables**, also
  triggered when the setting is switched on, and by the upgrade that
  introduced it) indexes the name of every eligible table with 1,000 rows or
  more (`INDEX_MIN_ROWS`); a table never analyzed yet is counted exactly;
- with the index: 10,810 products 41-88 ms per search bar request.

Two more rules keep it cheap:

- A name inherited from a parent table (`product.product` gets its name from
  `product.template`) is matched on the parent, restricted to the parent
  records of this model (`website.page` inherits from `ir.ui.view`; folding
  every view name took 300 ms). The link to an `_inherits` parent
  (`product_tmpl_id`) is never a separate path.
- Typos in linked records are only checked on models that take part in smart
  search themselves; technical comodels (`ir.model.fields`, ...) are large and
  unindexed (one goal-definition search took 450 ms because of it).

- Ranking uses plain `lower()` on the name, not the folded text: folding
  every matched row for every score term cost ~145 ms on a 1,070-hit word.

End result on 10,830 real products (local, full search bar request including
the count Odoo adds): 31-103 ms, dropdowns 33-73 ms. The broadest single word
("staal", 1,070 hits) is the 103 ms case; standard Odoo search takes 39 ms for
it.

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
