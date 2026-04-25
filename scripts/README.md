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

## Image pipeline (run once per fresh image batch)

When new business photos arrive (collected via the Tampermonkey rescue
userscript, then placed flat in `/images/<slug>.jpg`):

- **`add_watermark.py`** — stamps every `images/*.jpg` with the QatarPaws
  paw-print + `qatarpaws.com` watermark, bottom-right corner. Overwrites
  in place. Does **not** resize. Re-running double-stamps, so run once.

  ```sh
  pip install Pillow
  python scripts/add_watermark.py
  ```

After watermarking, run `rebuild_site.py` so business pages pick up the
new local image paths.

### Userscript pipeline (collecting fresh photos)

Reusable across future directories:

- **`build_image_input.py`** — reads `/business/*.html` and the
  `Data/*.json` raw scrapes to produce `images_input.json` (one row per
  business: slug, name, lat/lng, googleMapsUrl).
- **`build_image_rescue_userscript.py`** — bakes that JSON into
  `qatarpaws-image-rescue.user.js`, the Tampermonkey script that walks
  every business's Maps page, downloads the cover photo, and writes a
  manifest. Install in Tampermonkey → click ▶ Start on a Maps tab.

## Typical edit flow

1. Add/remove/edit business data directly in a detail page's JSON-LD block, or
   drop a new business page into `/business/` with a minimal LocalBusiness
   script tag.
2. Run `python scripts/rebuild_site.py`.
3. Run `python scripts/generate-search-data.py`.
4. Commit.
