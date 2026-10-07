# Option lists, plan (F15)

Status: **F15a done (2026-10-07)**, the rest planned (owner request 2026-10-02). Today (F7) a workspace has simple saved lists: the
palette **Lists** tab, "Fill from a list" / "Save as list" in a choice field, `GET/POST/PATCH/DELETE
/option-lists`. This document is the plan for everything after that, so it can be scheduled later.

## The five kinds of list

| Kind                         | What it is                                                   | Example                                                                           | How respondents pick                                                              |
| ---------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Static** (exists)          | A fixed list of options, copied into the field               | Priority, Departments                                                             | Dropdown, radio, checkboxes, multi-select                                         |
| **Large / autocomplete**     | Thousands of items, kept on the server, searched as you type | Products, airports, 5 000 branches                                                | "Search as you type" box, loads matches page by page                             |
| **Cascading (levels)**       | A tree with named levels; each choice narrows the next       | Region → Area → Site; State → City → Location                                     | One field per level; the next one opens with only the children of what was chosen |
| **With details (auto-fill)** | Items carry extra columns that fill other fields when chosen | Site → address, phone, manager; Product → price, unit                             | Choose one item, the linked fields fill themselves (optionally read-only)         |
| **Dynamic (live source)**    | Items come from somewhere else and refresh                   | Another form's responses, a connected database, a JSON URL, a CSV refreshed daily | Same as above; the list keeps itself up to date                                   |

Kinds combine: a cascading list can be large, have details on every level, and be dynamic.

## Data model

```ts
OptionList {
  id, name, description?
  kind: 'static' | 'tree' | 'dynamic'
  levels: { key: 'state', label: 'State' }[]        // tree only; 1–4 levels
  columns: { key: 'postcode', label: 'Postcode', type: 'text' | 'number' | 'email' | 'phone' }[]
  source?: {                                         // dynamic only
    type: 'form' | 'database' | 'http' | 'csv'
    config: …                                        // form id + fields | destination id + read-only query | URL + mapping | file
    refresh: 'manual' | 'hourly' | 'daily'
    last_synced_at, status, error?
  }
  items_count, created_by, created_at, updated_at
}

OptionItem {
  id, list_id, value, label
  level: 0 | 1 | …, parent_id: string | null         // tree: parent on the level above
  attrs: Record<column key, string | number>         // details for auto-fill
  translations?: Record<locale, string>              // label per language
  active: boolean                                    // retire without breaking old answers
  sort: number
}
```

Items live on the server (not inside the form schema) once a list is large, a tree or dynamic.
Small static lists may still be copied into the field as today.

## Fields that use a list (FormSchema)

```ts
field.option_source = {
  list_id: 'lst_…',
  level?: 1,                       // tree: which level this field shows
  parent_field?: 'fld_…',          // tree: the field holding the level above
  search?: boolean,                // autocomplete; on automatically above ~200 items
  min_chars?: 1, show_inactive?: false,
}
field.props.fills = [              // auto-fill from the chosen item's columns
  { column: 'postcode', target: 'fld_…', lock: true },   // lock = target becomes read-only
]
```

- **Builder:** a **Cascading choice** palette item asks for the list and adds one field per level,
  side by side (½ / ⅓) and already linked. The inspector shows the chain (State → City → Location)
  and lets you drop levels or change each field's label. "Fill other fields" lists the columns and a
  target field for each.
- **Respondents:** a child field stays disabled until its parent has an answer; changing the parent
  clears the children. Autocomplete shows "Type to search", results paged, keyboard friendly.
- **Answers** store value **and** label (and the full path for trees: `{ state, city, location }`),
  so exports stay readable even if the list changes later.
- **Formulas and logic** can use item columns: `{site.capacity}`, condition "Site's region is …".

## List manager (Option sets page)

Tabs per list: **Items** (tree editor: add / rename / move / retire, drag + keyboard, bulk paste),
**Columns** (details for auto-fill), **Import** (CSV / spreadsheet: map columns to levels, value,
label, details; preview before saving; replace or merge), **Source** (dynamic lists: pick the
source, test, refresh schedule, sync log), **Translations**, **Used in** (forms and fields).
Deleting or retiring items never breaks old responses.

## API (draft)

| Method | Path                                                       | Notes                                                                                                                                       |
| ------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/option-lists/{id}/items?level=&parent=&q=&page=`         | search + paging for autocomplete and cascading                                                                                              |
| POST   | `/option-lists/{id}/items/bulk`                            | upsert / reorder / retire many items                                                                                                        |
| POST   | `/option-lists/{id}/import`                                | CSV or XLSX with a column mapping → job with progress                                                                                       |
| POST   | `/option-lists/{id}/refresh`                               | dynamic: sync now → job                                                                                                                     |
| GET    | `/option-lists/{id}/usage`                                 | forms and fields using the list                                                                                                             |
| GET    | `/public/forms/{slug}/options/{field_id}?parent=&q=&page=` | for respondents: no sign-in, rate limited, only lists used by the **published** version, only active items, only the columns the form fills |

## Security and performance

- Dynamic sources run **server-side only**; credentials never reach the browser. Database sources
  use a read-only connection from Destinations and a saved, parameterised query.
- Public option lookups are rate limited and cached; children load per parent, so a 100 000-item
  tree never ships whole.
- Every change to a list is in the audit trail (`forms.list_*`).
- Sample data stays neutral and international (e.g. Region → Area → Site).

## Phasing

1. **F15a, List manager:** the Option sets page (DataView), items editor, bulk paste, CSV import, translations, "used in".
2. **F15b, Large lists + autocomplete:** server-side items, search-as-you-type field mode, paging.
3. **F15c, Cascading lists:** tree lists with levels, "Cascading choice" field group, parent → child loading.
4. **F15d, Details + auto-fill:** columns on items, "Fill other fields", formulas / logic on columns.
5. **F15e, Dynamic lists:** sources from forms, connected databases (after F12 Data sources), JSON URL, refreshed CSV; sync log.

## F15a as built (2026-10-07)

- **Option sets page** in the locked list format: chart cards (options in all lists with the biggest lists; in use / not used yet, legend filters), table and cards, search, state filter, sort; ⋯ open, duplicate, delete (forms keep their copies).
- **List editor** (`/option-sets/{id}`): name and description; **Options** with label, value (shown on demand, made from the label for new options, locked once saved) and score, drag or ↑ / ↓ to reorder, retire / offer again (saved options are never removed, so old answers keep reading), 100 rows at a time with search; **Paste** and **Import** (CSV, TXT, Excel .xlsx first sheet, read in the browser without a library) with column mapping (label, value, score, label per language; guessed from the header) and a preview, add-and-update or replace (missing options are retired); **Translations** per form language with progress; **Used in** with up-to-date marks and Update (all or one form). Save / Discard, Ctrl / ⌘ + S, leave warning.
- **Builder:** fields filled from a list get its active options only, and say when the list changed since, with "Update from the list".

## F15c lists with levels, as built (M2, 2026-10-07)

- **Data:** `OptionList.levels?: { key, label }[]` (2 to 4, owner 2026-10-07; absent = a plain list); `OptionItem.level?` (0 = top, omitted) and `parent?` (the value of an option on the level above). The server refuses an option below the top without a parent on the level above (`422 FRM-FORM-1021`). Values stay unique across the whole list; imported children get `{parent}_{label}` values.
- **Fields:** one field per level, `option_set_id`, `option_level` and `option_parent` (the field id one level up); each level is `dropdown` (one choice) or `multi_select` (several), chosen in the form design. Options carry `parent`.
- **Rules (`shared/utils/forms/cascade.ts`, renderer and server alike):** a level offers only the options under what was chosen above (several chosen above: under any of them); with nothing chosen or nothing under it the level stays closed (hidden, not required); a changed choice drops answers that no longer fit. A retired option hides everything under it.
- **Editor:** Levels card (name levels, add up to 4, remove the last with its options), Options one level at a time with the option above (searchable), Under filter, "N under it" to go down; Import maps one column per level (rows are paths); Paste only for plain lists.
- **Builder:** Lists tab shows plain lists with their option count and lists with levels with a badge and the chain; clicking or dragging a list adds it with nothing to choose (owner 2026-10-07): a plain list as a dropdown, a list with levels as one linked field per level in one row (one choice, not required); each field is then set in the right panel: Show as (dropdown, multi-select, single choice, checkboxes) for plain lists, One / Several and Required per level (a level that never opens is never required). On the canvas the levels behave as in the form (a lower level locked with "Choose … first" until something is chosen above, then only what is under it). A chain is one block: deleting any level removes all of them (one Undo), duplicating copies the whole chain linked; a level's settings show the chain, what it filters by, one / several and Update from the list.
