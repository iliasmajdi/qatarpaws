#!/usr/bin/env python3
"""
Build images_input.json for the Tampermonkey image-rescue userscript.

Reads:
  business/*.html             — canonical site list (slug, name, lat, lng)
  ../../../Data/*.json        — Outscraper raw scrapes (name, coords, googleMapsUrl)

For each site business, matches the closest Data/ record by coordinates
(<= ~100m apart) and emits one input row with the best Maps URL to navigate.
Writes images_input.json next to this script. Prints a coverage summary so
we know which slugs need manual collection later.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT.parent.parent.parent / "Data"
COORD_TOLERANCE_DEG = 0.001  # ~100m at Qatar's latitude

LD_RE = re.compile(r'<script type="application/ld\+json">(\{[^<]*?"@type":\s*"LocalBusiness"[^<]*?\})</script>', re.DOTALL)


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))


def extract_site_businesses():
    out = []
    for f in sorted((ROOT / "business").glob("*.html")):
        html = f.read_text(encoding="utf-8")
        m = LD_RE.search(html)
        if not m:
            continue
        try:
            ld = json.loads(m.group(1))
        except Exception:
            continue
        if ld.get("@type") != "LocalBusiness":
            continue
        geo = ld.get("geo") or {}
        try:
            lat = float(geo.get("latitude", ""))
            lng = float(geo.get("longitude", ""))
        except Exception:
            continue
        out.append({"slug": f.stem, "name": ld.get("name", ""), "lat": lat, "lng": lng})
    return out


def extract_data_records():
    out = []
    if not DATA_DIR.exists():
        return out
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            arr = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        for r in arr:
            if not isinstance(r, dict):
                continue
            try:
                lat = float(r.get("latitude", "") or 0)
                lng = float(r.get("longitude", "") or 0)
            except Exception:
                continue
            if lat == 0 or lng == 0:
                continue
            out.append({
                "name": (r.get("name") or "").replace(" · Visited link", "").strip(),
                "lat": lat,
                "lng": lng,
                "googleMapsUrl": r.get("googleMapsUrl") or "",
                "photoUrls": r.get("photoUrls") or [],
                "_source_file": f.name,
            })
    return out


def main():
    site = extract_site_businesses()
    data = extract_data_records()
    print(f"Site businesses with coords: {len(site)}")
    print(f"Data records (with overlap):  {len(data)}")

    # Build coord-indexed best match per site slug
    rows = []
    matched = 0
    for sb in site:
        best = None
        best_d = 1e9
        for d in data:
            if abs(d["lat"] - sb["lat"]) > COORD_TOLERANCE_DEG: continue
            if abs(d["lng"] - sb["lng"]) > COORD_TOLERANCE_DEG: continue
            dist = haversine_m(sb["lat"], sb["lng"], d["lat"], d["lng"])
            if dist < best_d:
                best_d = dist
                best = d
        if best:
            matched += 1
            maps_url = best["googleMapsUrl"] or ""
        else:
            maps_url = ""
        # Always provide a fallback URL constructed from coords + name
        fallback_url = f"https://www.google.com/maps/search/?api=1&query={sb['lat']},{sb['lng']}"
        rows.append({
            "slug": sb["slug"],
            "name": sb["name"],
            "lat": sb["lat"],
            "lng": sb["lng"],
            "mapsUrl": maps_url or fallback_url,
            "hasPlaceUrl": bool(maps_url),
        })

    out_path = ROOT / "scripts" / "images_input.json"
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    no_place_url = [r for r in rows if not r["hasPlaceUrl"]]
    print()
    print(f"Matched to Data/ with place URL:   {matched}/{len(site)}")
    print(f"Will use coord-search fallback:    {len(no_place_url)}/{len(site)}")
    print(f"Wrote: {out_path.relative_to(ROOT)}")
    if no_place_url:
        print()
        print(f"First 10 slugs without Data/ match (will use coord fallback):")
        for r in no_place_url[:10]:
            print(f"  - {r['slug']}")


if __name__ == "__main__":
    main()
