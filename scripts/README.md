# QatarPaws build scripts

## Active

- **`rebuild_site.py`** — master rebuild. Extracts business data from the
  LocalBusiness JSON-LD in each existing business detail page, and regenerates
  every HTML file in the site (homepages, category pages, business pages,
  about/blog/list-your-business) using the v2 editorial template. Also emits
  `/favicon.svg`, `/site.webmanifest`, `/images/og-default.svg`, and
  `/sitemap.xml`. Idempotent: safe to re-run after data edits.

  ```sh
  python scripts/rebuild_site.py
  ```

- **`generate-search-data.py`** — rebuilds `/js/search-data.json`, the
  Fuse.js index used by the on-site search. Run *after* `rebuild_site.py`
  (the search index follows the current HTML).

  ```sh
  python scripts/generate-search-data.py
  ```

## Typical edit flow

1. Add/remove/edit business data directly in a detail page's JSON-LD block, or
   drop a new business page into `/business/` with a minimal LocalBusiness
   script tag.
2. Run `python scripts/rebuild_site.py`.
3. Run `python scripts/generate-search-data.py`.
4. Commit.

## Legacy (`scripts/legacy/`)

One-shot migration scripts from the v1 teal design. They target the old
markup (`.card`, `.biz-hero`, etc.) and **will corrupt pages if re-run**
against v2 output. Kept for reference only.
