# Option lists — plan (F15)

Status: **planned** (owner request 2026-10-02). Today (F7) a workspace has simple saved lists: the
palette **Lists** tab, "Fill from a list" / "Save as list" in a choice field, `GET/POST/PATCH/DELETE
/option-lists`. This document is the plan for everything after that, so it can be scheduled later.

## The five kinds of list

| Kind                         | What it is                                                   | Example                                                                           | How respondents pick                                                              |
| ---------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Static** (exists)          | A fixed list of options, copied into the field               | Priority, Departments                                                             | Dropdown, radio, checkboxes, multi-select                                         |
| **Large / autocomplete**     | Thousands of items, kept on the server, searched as you type | Products, airports, 5 000 branches                                                | "Search as you type" box — loads matches page by page                             |
| **Cascading (levels)**       | A tree with named levels; each choice narrows the next       | Region → Area → Site; State → City → Location                                     | One field per level; the next one opens with only the children of what was chosen |
| **With details (auto-fill)** | Items carry extra columns that fill other fields when chosen | Site → address, phone, manager; Product → price, unit                             | Choose one item, the linked fields fill themselves (optionally read-only)         |
| **Dynamic (live source)**    | Items come from somewhere else and refresh                   | Another form's responses, a connected database, a JSON URL, a CSV refreshed daily | Same as above; the list keeps itself up to date                                   |

Kinds combine: a cascading list can be large, have details on every level, and be dynamic.

## Data model

```ts
OptionList {
  id, name, description?
  kind: 'static' | 'tree' | 'dynamic'
  levels: { key: 'state', label: 'State' }[]        // tree only; 1–5 levels
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

1. **F15a — List manager:** the Option sets page (DataView), items editor, bulk paste, CSV import, translations, "used in".
2. **F15b — Large lists + autocomplete:** server-side items, search-as-you-type field mode, paging.
3. **F15c — Cascading lists:** tree lists with levels, "Cascading choice" field group, parent → child loading.
4. **F15d — Details + auto-fill:** columns on items, "Fill other fields", formulas / logic on columns.
5. **F15e — Dynamic lists:** sources from forms, connected databases (after F12 Data sources), JSON URL, refreshed CSV; sync log.
