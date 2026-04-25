#!/usr/bin/env python3
"""
Generate the production Tampermonkey userscript with all 203 businesses
baked in. Reads scripts/images_input.json (built by build_image_input.py).

Output: scripts/qatarpaws-image-rescue.user.js
"""
from __future__ import annotations
import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
INPUT = SCRIPTS / "images_input.json"
OUTPUT = SCRIPTS / "qatarpaws-image-rescue.user.js"

TEMPLATE = r"""// ==UserScript==
// @name         QatarPaws image rescue (production)
// @namespace    https://qatarpaws.com/
// @version      1.1.0
// @description  Walks every business's Maps page, downloads cover photo, writes manifest.
// @match        https://www.google.com/maps/*
// @grant        GM_xmlhttpRequest
// @grant        GM_download
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @run-at       document-idle
// @connect      lh3.googleusercontent.com
// @connect      lh4.googleusercontent.com
// @connect      lh5.googleusercontent.com
// @connect      googleusercontent.com
// ==/UserScript==

(function () {
  'use strict';

  // ---- baked-in business list ------------------------------------------ //
  const BUSINESSES = __BUSINESSES_JSON__;

  // ---- tunables -------------------------------------------------------- //
  const PER_BIZ_TIMEOUT_MS = 25000;   // give up waiting for a photo after this
  const POLL_MS            = 750;
  const MIN_DIM            = 200;
  const POST_DOWNLOAD_MS   = 1500;    // pause after save before navigating
  const NAV_DELAY_MS       = 4000;    // pause between businesses (be polite)

  // ---- state keys ------------------------------------------------------ //
  const K_RUNNING       = 'qpaws_running';
  const K_INDEX         = 'qpaws_index';
  const K_RESULTS       = 'qpaws_results';
  const K_NAV_ATTEMPTS  = 'qpaws_nav_attempts';   // for current index
  const K_NAV_INDEX     = 'qpaws_nav_index';      // index the attempts apply to
  const K_SKIP_REQ      = 'qpaws_skip_request';
  const MAX_NAV_ATTEMPTS = 2;

  // ---- main ------------------------------------------------------------ //
  if (window.__QPAWS_RAN__) return;
  window.__QPAWS_RAN__ = true;

  const running = GM_getValue(K_RUNNING, false);

  // Always render the control panel so user can start / resume / stop.
  renderPanel();

  if (!running) return;

  const idx = GM_getValue(K_INDEX, 0);
  if (idx >= BUSINESSES.length) {
    finishJob();
    return;
  }

  const cur = BUSINESSES[idx];
  updateStatus('Business ' + (idx + 1) + ' / ' + BUSINESSES.length +
               ': ' + cur.slug);

  // Honor a manual skip request.
  if (GM_getValue(K_SKIP_REQ, false)) {
    GM_deleteValue(K_SKIP_REQ);
    recordResult(idx, cur, false, null, 'manually skipped');
    advance(idx);
    return;
  }

  // Auto-skip businesses without a real place URL (service-only, no Maps page).
  if (!cur.hasPlaceUrl) {
    recordResult(idx, cur, false, null, 'no place URL — service business');
    advance(idx);
    return;
  }

  // If we're not on the right place page yet, navigate there — but bound the
  // number of attempts so a bad URL can't infinite-loop the queue.
  if (!locationMatches(cur)) {
    let attempts = (GM_getValue(K_NAV_INDEX, -1) === idx)
      ? GM_getValue(K_NAV_ATTEMPTS, 0)
      : 0;
    if (attempts >= MAX_NAV_ATTEMPTS) {
      recordResult(idx, cur, false, null,
        'navigation never landed on a place page after ' +
        MAX_NAV_ATTEMPTS + ' attempts');
      GM_deleteValue(K_NAV_ATTEMPTS);
      GM_deleteValue(K_NAV_INDEX);
      advance(idx);
      return;
    }
    GM_setValue(K_NAV_INDEX, idx);
    GM_setValue(K_NAV_ATTEMPTS, attempts + 1);
    updateStatus('Navigating to ' + cur.slug +
                 ' (attempt ' + (attempts + 1) + '/' + MAX_NAV_ATTEMPTS + ') ...');
    setTimeout(() => { location.href = cur.mapsUrl; }, 500);
    return;
  }

  // Got to the right page — clear nav-attempt tracking, do the work.
  GM_deleteValue(K_NAV_ATTEMPTS);
  GM_deleteValue(K_NAV_INDEX);
  processCurrent(cur, idx);

  // ---- core flow ------------------------------------------------------- //

  function processCurrent(biz, idx) {
    const t0 = Date.now();
    const poll = setInterval(() => {
      const pick = findHeroPhotoUrl();
      if (pick) {
        clearInterval(poll);
        download(biz, pick, idx);
      } else if (Date.now() - t0 > PER_BIZ_TIMEOUT_MS) {
        clearInterval(poll);
        recordResult(idx, biz, false, null, 'no large photo found in DOM');
        advance(idx);
      }
    }, POLL_MS);
  }

  function download(biz, picked, idx) {
    const ext = guessExt(picked.url);
    const filename = biz.slug + '.' + ext;
    updateStatus('Downloading ' + filename + ' (' + picked.w + 'x' +
                 picked.h + ', ' + picked.source + ') ...');

    GM_download({
      url: picked.url,
      name: filename,
      saveAs: false,
      onload: () => {
        recordResult(idx, biz, true, filename, null, picked);
        setTimeout(() => advance(idx), POST_DOWNLOAD_MS);
      },
      onerror: (e) => {
        // Fallback: GM_xmlhttpRequest -> blob -> <a download>
        xhrFallback(biz, picked, idx, filename);
      },
      ontimeout: () => {
        recordResult(idx, biz, false, null, 'GM_download timeout');
        advance(idx);
      },
    });
  }

  function xhrFallback(biz, picked, idx, filename) {
    GM_xmlhttpRequest({
      method: 'GET',
      url: picked.url,
      responseType: 'blob',
      onload: (r) => {
        if (r.status !== 200) {
          recordResult(idx, biz, false, null, 'XHR HTTP ' + r.status);
          advance(idx);
          return;
        }
        const blobUrl = URL.createObjectURL(r.response);
        const a = document.createElement('a');
        a.href = blobUrl; a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { URL.revokeObjectURL(blobUrl); a.remove(); }, 1000);
        recordResult(idx, biz, true, filename, 'xhr-fallback', picked);
        setTimeout(() => advance(idx), POST_DOWNLOAD_MS);
      },
      onerror: () => {
        recordResult(idx, biz, false, null, 'XHR failed');
        advance(idx);
      },
    });
  }

  function advance(idx) {
    const next = idx + 1;
    GM_setValue(K_INDEX, next);
    if (next >= BUSINESSES.length) {
      finishJob();
      return;
    }
    setTimeout(() => { location.href = BUSINESSES[next].mapsUrl; },
               NAV_DELAY_MS);
  }

  function finishJob() {
    const results = GM_getValue(K_RESULTS, []);
    const ok   = results.filter(r => r.ok).length;
    const fail = results.length - ok;
    updateStatus('DONE — ' + ok + ' ok, ' + fail + ' failed. Saving manifest...');
    const blob = new Blob(
      [JSON.stringify(results, null, 2)],
      { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'image_rescue_manifest.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 1500);
    GM_setValue(K_RUNNING, false);
    updateStatus('DONE — ' + ok + ' / ' + results.length +
                 ' downloaded. Manifest saved.');
  }

  function recordResult(idx, biz, ok, filename, err, picked) {
    const results = GM_getValue(K_RESULTS, []);
    results[idx] = {
      idx, slug: biz.slug, name: biz.name, ok,
      filename: filename || null,
      url: picked ? picked.url : null,
      width: picked ? picked.w : null,
      height: picked ? picked.h : null,
      source: picked ? picked.source : null,
      error: err || null,
    };
    GM_setValue(K_RESULTS, results);
  }

  // ---- DOM detection --------------------------------------------------- //

  function urlSize(u) {
    const m = u.match(/=w(\d+)-h(\d+)/);
    if (!m) return { w: 0, h: 0 };
    return { w: +m[1], h: +m[2] };
  }

  function findHeroPhotoUrl() {
    const cands = [];
    for (const img of document.querySelectorAll('img')) {
      const src = img.currentSrc || img.src || '';
      if (!/lh[345]\.googleusercontent\.com/.test(src)) continue;
      const w = img.naturalWidth || 0;
      const h = img.naturalHeight || 0;
      if (w < MIN_DIM || h < MIN_DIM) continue;
      cands.push({ url: src, w, h, area: w * h, source: 'img' });
    }
    for (const el of document.querySelectorAll('[style*="background-image"]')) {
      const m = (el.getAttribute('style') || '').match(
        /background-image:\s*url\(["']?(https:\/\/lh[345]\.googleusercontent\.com\/[^"' )]+)/);
      if (!m) continue;
      const sz = urlSize(m[1]);
      if (sz.w < MIN_DIM || sz.h < MIN_DIM) continue;
      cands.push({ url: m[1], w: sz.w, h: sz.h, area: sz.w * sz.h, source: 'bg' });
    }
    if (!cands.length) return null;
    cands.sort((a, b) => b.area - a.area);
    return cands[0];
  }

  function guessExt(url) {
    if (/\.png/i.test(url)) return 'png';
    if (/\.webp/i.test(url)) return 'webp';
    return 'jpg';
  }

  function locationMatches(biz) {
    // Must be on a /maps/place/... URL (not /maps/search/, /maps/dir/, etc.)
    if (!location.pathname.includes('/place/')) return false;
    // Even a loose slug overlap is acceptable — Maps may rewrite the slug
    // (e.g. capitalization, transliteration). If pathname has /place/ at all
    // after we navigated to this biz, treat it as "good enough" and let the
    // photo detector run. Better to attempt and fail at photo-find than loop.
    return true;
  }

  // ---- floating control panel ----------------------------------------- //

  function renderPanel() {
    if (document.getElementById('qpaws-panel')) return;
    const css = `
      #qpaws-panel { position:fixed; top:12px; right:12px; z-index:2147483647;
        background:#141210; color:#F6F1E8; padding:12px 14px; border-radius:8px;
        font:13px/1.4 -apple-system,BlinkMacSystemFont,sans-serif;
        min-width:280px; max-width:340px; box-shadow:0 6px 24px rgba(0,0,0,0.4); }
      #qpaws-panel h4 { margin:0 0 6px; font-size:13px; color:#0d9488; }
      #qpaws-panel button { margin:4px 4px 0 0; padding:6px 10px; border:0;
        border-radius:4px; cursor:pointer; font:600 12px sans-serif; }
      #qpaws-panel .start { background:#0a7a3e; color:#fff; }
      #qpaws-panel .stop  { background:#7B1E1E; color:#fff; }
      #qpaws-panel .skip  { background:#b85c00; color:#fff; }
      #qpaws-panel .reset { background:#444; color:#fff; }
      #qpaws-status { margin-top:6px; font-size:12px; color:#F6F1E8; opacity:0.9;
        word-break:break-all; }`;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    const wrap = document.createElement('div');
    wrap.id = 'qpaws-panel';
    const total = BUSINESSES.length;
    const idx = GM_getValue(K_INDEX, 0);
    const results = GM_getValue(K_RESULTS, []);
    const ok = results.filter(r => r && r.ok).length;
    const isRunning = GM_getValue(K_RUNNING, false);

    wrap.innerHTML =
      '<h4>QatarPaws image rescue</h4>' +
      '<div>' + total + ' businesses · ' + idx + ' processed · ' + ok + ' downloaded</div>' +
      '<div>' +
        (isRunning
          ? '<button class="stop" id="qpaws-stop">⏸ Pause</button>'
          : '<button class="start" id="qpaws-start">▶ ' + (idx > 0 ? 'Resume' : 'Start') + '</button>'
        ) +
        '<button class="skip" id="qpaws-skip">⏭ Skip</button>' +
        '<button class="reset" id="qpaws-reset">Reset</button>' +
      '</div>' +
      '<div id="qpaws-status"></div>';

    document.body.appendChild(wrap);

    const startBtn = document.getElementById('qpaws-start');
    if (startBtn) startBtn.addEventListener('click', () => {
      GM_setValue(K_RUNNING, true);
      const startIdx = GM_getValue(K_INDEX, 0);
      if (startIdx >= BUSINESSES.length) GM_setValue(K_INDEX, 0);
      location.href = BUSINESSES[GM_getValue(K_INDEX, 0)].mapsUrl;
    });
    const stopBtn = document.getElementById('qpaws-stop');
    if (stopBtn) stopBtn.addEventListener('click', () => {
      GM_setValue(K_RUNNING, false);
      updateStatus('Paused at index ' + GM_getValue(K_INDEX, 0));
    });
    const skipBtn = document.getElementById('qpaws-skip');
    if (skipBtn) skipBtn.addEventListener('click', () => {
      const i = GM_getValue(K_INDEX, 0);
      if (i >= BUSINESSES.length) {
        updateStatus('Nothing to skip — already done.');
        return;
      }
      // Mark the current biz as skipped, advance, and either continue or pause.
      const biz = BUSINESSES[i];
      const results = GM_getValue(K_RESULTS, []);
      results[i] = {
        idx: i, slug: biz.slug, name: biz.name, ok: false,
        filename: null, url: null, width: null, height: null, source: null,
        error: 'manually skipped',
      };
      GM_setValue(K_RESULTS, results);
      GM_setValue(K_INDEX, i + 1);
      GM_deleteValue(K_NAV_ATTEMPTS);
      GM_deleteValue(K_NAV_INDEX);
      if (GM_getValue(K_RUNNING, false) && i + 1 < BUSINESSES.length) {
        location.href = BUSINESSES[i + 1].mapsUrl;
      } else {
        location.reload();
      }
    });
    const resetBtn = document.getElementById('qpaws-reset');
    if (resetBtn) resetBtn.addEventListener('click', () => {
      if (!confirm('Reset progress? You will lose the queue position and ' +
                   'in-memory manifest. Files in Downloads stay.')) return;
      GM_deleteValue(K_RUNNING);
      GM_deleteValue(K_INDEX);
      GM_deleteValue(K_RESULTS);
      location.reload();
    });
  }

  function updateStatus(msg) {
    const el = document.getElementById('qpaws-status');
    if (el) el.textContent = msg;
    console.log('[qpaws] ' + msg);
  }
})();
"""


def main():
    if not INPUT.exists():
        raise SystemExit(f"Missing {INPUT}. Run build_image_input.py first.")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    out = TEMPLATE.replace("__BUSINESSES_JSON__", payload)
    OUTPUT.write_text(out, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(SCRIPTS.parent)}  ({len(out)//1024} KB, "
          f"{len(data)} businesses embedded)")


if __name__ == "__main__":
    main()
