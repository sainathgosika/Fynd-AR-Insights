# Fynd · Receivables Insights

Single-file dashboard for Fynd AR / receivables, served from a Google Sheet via
Google Apps Script. The dashboard is a self-contained HTML app (Tailwind +
Chart.js) that reads AR, PDD, and Bank Receipt tabs, computes DSO, ageing,
follow-up queues, SOA ledgers, and more, then renders everything client-side.

## Repo layout

| File | Purpose |
|------|---------|
| `build_v4.py` | Emits the dashboard HTML in two flavours: **FULL** (with embedded seed data for local file preview) and **SLIM** (no embedded data, meant to be served by Apps Script and populated live via JSONP). |
| `build_codegs.py` | Reads the SLIM HTML, base64-encodes + chunks it, and wraps it in the Apps Script backend to produce a single `code.gs` file that hosts the dashboard, exposes the JSON data feed, and handles follow-up emails / auth / worklist / SOA email / workflows. |

Both scripts write to `./mnt/outputs/` in the working session; the outputs are
gitignored because they are regenerable.

## Build

```bash
# FULL (embedded data — for local file preview)
python3 build_v4.py

# SLIM (no embedded data — required before build_codegs.py)
python3 build_v4.py --slim

# Wrap the SLIM HTML into a single Apps Script file
python3 build_codegs.py
```

The `code.gs` output is what you paste into the Apps Script editor and deploy
as a web app.

## Deploy

1. Open the Apps Script project bound to the AR spreadsheet.
2. Replace the contents of `code.gs` with the freshly generated one.
3. **Deploy → Manage deployments → Edit (pencil) → Version: New version → Deploy.**
   Keeping the same deployment edit preserves the existing `/exec` URL.
4. Hard-refresh the browser (Cmd/Ctrl-Shift-R).

## Architecture notes

* **Data feed** — `serveData_()` reads three tabs and returns a single JSON
  payload. The result is memoised in `CacheService.getScriptCache()` for 5
  minutes, chunked across `payload_c0..cN` keys to fit the 100 KB / key cap.
  The Hard Refresh button hits `?action=dataRefresh` to purge the cache.
* **Auth** — application-level username/password, backed by an ACL sheet, with
  session tokens forwarded on every JSONP call. The admin (Google identity)
  bypasses the login screen.
* **Boot progress overlay** — head-inline controller with a 12-second safety
  net so the dashboard never sits stuck on "Connecting…". Every `wire*()` call
  is wrapped in `_bootSafe(label, fn)` so one bad module can't break the whole
  boot.
* **Apps Script hosting fallback** — if `serveDashboard_()`'s `<head>` inject
  ever fails to reach the browser, a client-side detector reads
  `document.referrer` to recover the `/exec` URL and back-fills
  `window.__DATA_URL__` / `window.__SERVED_BY_APPS_SCRIPT__`, so live data
  loads even from stale deployments.
