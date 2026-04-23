#!/usr/bin/env python3
"""
Generate a self-contained JavaScript file the user can paste into
Chrome DevTools console. The script fetches every lh3.googleusercontent.com
image URL currently referenced in the site, and tries to save them to the
browser's Downloads folder.

Why browser-side? The 'gps-cs-s/...' tokens may be treated differently by
Google when requested from an actual Chrome browser (different TLS/HTTP
fingerprint, possibly different cookie handling) than from a server-side
curl/urllib. Worth attempting before giving up on the URLs.

Output: scripts/image_rescue.js  — open in any editor, copy its contents,
paste into Chrome DevTools Console on any https:// page, hit Enter.

Does NOT modify any site HTML. Read-only scan + code generation only.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# Scan business/ only (AR pages reference the same URLs; no new URLs in AR)
URL_RE = re.compile(r'src="(https://lh3\.googleusercontent\.com/[^"]+)"')
TOKEN_RE = re.compile(r"/gps-cs-s/([^/=]+)")  # "AHVA..." token

jobs: list[dict] = []
seen_urls: set[str] = set()

for f in sorted((ROOT / "business").glob("*.html")):
    slug = f.stem
    urls = URL_RE.findall(f.read_text(encoding="utf-8"))
    # Preserve order within page, but dedupe URLs across all pages
    local_idx = 0
    for u in urls:
        if u in seen_urls:
            continue
        seen_urls.add(u)
        local_idx += 1
        tok = TOKEN_RE.search(u)
        token12 = (tok.group(1)[:12] if tok else "unk")
        jobs.append({
            "slug": slug,
            "idx": local_idx,
            "token": token12,
            "url": u,
        })

print(f"Unique URLs to attempt: {len(jobs)}")
print(f"Across {len({j['slug'] for j in jobs})} businesses")

# Sanity: how long is the full JS going to be?
data_size = sum(len(j["url"]) + len(j["slug"]) + 20 for j in jobs)
print(f"Embedded URL data size: ~{data_size // 1024} KB")

# Render the JS file
JS = r"""// ============================================================
// QatarPaws image rescue — run inside Chrome DevTools console
// on ANY https:// page (your own site works, e.g. qatarpaws.com).
// Paste-and-enter. Wait. Files save to your Downloads folder.
// ============================================================
//
// Each file is named:  <slug>__<token12>.jpg
// Where:
//   slug    = the business-detail page stem (e.g. royal-veterinary-center)
//   token12 = first 12 chars of the Google "gps-cs-s/AHVA..." token,
//             which uniquely identifies the source URL.
// Plus the script downloads one extra file:
//   _download_report.json  — full URL -> filename mapping + ok/fail status.
//
// Sort those files into /images/business/<slug>/<idx>.jpg AFTER the run;
// a separate server-side script will do the sort + HTML rewrite once
// you confirm how many images actually came through.
//
// Settings you can edit:
//   TEST_ONLY — set to a positive number N to only try the first N URLs
//               (useful to verify tokens work before attempting all).
//   DELAY_MS  — ms to wait between requests (be polite to Google).
// ============================================================

(async () => {
  const TEST_ONLY = 0;     // 0 = all; e.g. 5 = try only the first 5
  const DELAY_MS  = 300;   // ms between downloads

  const JOBS = __JOBS_PLACEHOLDER__;
  const jobs = TEST_ONLY > 0 ? JOBS.slice(0, TEST_ONLY) : JOBS;

  if (!window.fetch || !window.URL || !window.Blob) {
    console.error("This browser is too old. Use recent Chrome or Edge.");
    return;
  }

  const results = [];
  let ok = 0, fail = 0;
  const t0 = Date.now();
  console.log(`%cQatarPaws image rescue: ${jobs.length} URLs to try`,
              "color:#7B1E1E;font-weight:bold;font-size:14px");

  // Helper: trigger a download of a blob with a specific filename
  function saveBlob(blob, filename) {
    const bUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = bUrl;
    a.download = filename;
    a.rel = "noopener";
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(bUrl); a.remove(); }, 1500);
  }

  for (let i = 0; i < jobs.length; i++) {
    const {slug, idx, token, url} = jobs[i];
    const fname = `${slug}__${token}.jpg`;
    const entry = {slug, idx, token, url, filename: fname};

    try {
      const r = await fetch(url, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        referrerPolicy: "no-referrer",
        cache: "no-store",
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const ct = (r.headers.get("content-type") || "").toLowerCase();
      if (!ct.startsWith("image/")) throw new Error(`not image: ${ct}`);
      const blob = await r.blob();
      if (blob.size < 500) throw new Error(`too small: ${blob.size}b`);

      // Use proper extension from content-type
      let ext = "jpg";
      if (ct.includes("png"))  ext = "png";
      else if (ct.includes("webp")) ext = "webp";
      else if (ct.includes("gif"))  ext = "gif";
      const finalName = `${slug}__${token}.${ext}`;
      saveBlob(blob, finalName);

      entry.ok = true;
      entry.size = blob.size;
      entry.filename = finalName;
      ok++;
    } catch (e) {
      entry.ok = false;
      entry.error = String(e && e.message || e);
      fail++;
    }
    results.push(entry);

    if ((i + 1) % 10 === 0 || i === jobs.length - 1) {
      const sec = ((Date.now() - t0) / 1000).toFixed(0);
      console.log(`${i+1}/${jobs.length} — ok:${ok} fail:${fail} — ${sec}s`);
    }

    if (DELAY_MS > 0 && i < jobs.length - 1) {
      await new Promise(r => setTimeout(r, DELAY_MS));
    }
  }

  // Write the mapping report
  const report = {
    site: location.origin,
    started: new Date(t0).toISOString(),
    finished: new Date().toISOString(),
    total: jobs.length,
    ok, fail,
    items: results,
  };
  saveBlob(
    new Blob([JSON.stringify(report, null, 2)], {type:"application/json"}),
    "_download_report.json"
  );

  console.log(
    `%cDONE — ok:${ok}  fail:${fail}  total:${jobs.length}`,
    `color:${ok > 0 ? "#0a7a3e" : "#7B1E1E"};font-weight:bold;font-size:14px`
  );
  console.log("Report saved as _download_report.json in your Downloads folder.");
  if (ok === 0) {
    console.log("%cZero downloads succeeded — tokens are probably expired.",
                "color:#7B1E1E");
  }
})();
"""

js_text = JS.replace("__JOBS_PLACEHOLDER__", json.dumps(jobs, ensure_ascii=False))
out = ROOT / "scripts" / "image_rescue.js"
out.write_text(js_text, encoding="utf-8")
print(f"\nWrote {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB)")
print(f"URLs embedded: {len(jobs)}")
