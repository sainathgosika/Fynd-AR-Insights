# Fynd · Receivables Insights

Single-file dashboard for Fynd AR / receivables. Two deployment targets are
supported from the same source of truth:

1. **Google Apps Script** — served as a bound web app off the AR spreadsheet
   (live data via JSONP, cache-backed).
2. **Boltic Serverless** — Flask + gunicorn image built from `Dockerfile`, ships
   the FULL HTML with data baked in at build time.

The dashboard itself is a self-contained HTML app (Tailwind + Chart.js) that
reads AR, PDD, and Bank Receipt tabs, computes DSO, ageing, follow-up queues,
SOA ledgers, and more, then renders everything client-side.

## Repo layout

| File | Purpose |
|------|---------|
| `build_v4.py` | Emits the dashboard HTML in two flavours: **FULL** (with embedded data from `data3.json`) and **SLIM** (no embedded data, meant to be served by Apps Script and populated live via JSONP). Output dir defaults to `./build/` inside Docker, or `./mnt/outputs/` in the original sandbox. Overridable via `AR_OUT_DIR`. |
| `build_codegs.py` | Reads the SLIM HTML, base64-encodes + chunks it, and wraps it in the Apps Script backend to produce a single `code.gs` file that hosts the dashboard, exposes the JSON data feed, and handles follow-up emails / auth / worklist / SOA email / workflows. |
| `app.py` | Minimal Flask server for Boltic Serverless. Serves the built HTML at `/`, health at `/health`. |
| `Dockerfile` | Builds the Boltic image: `pip install`, run `build_v4.py`, start `gunicorn` on `$PORT`. |
| `boltic.yaml` | Boltic app config — `builtin: dockerfile`, port 8080, region `asia-south1`, autoscale 1–2. |
| `requirements.txt` | Runtime deps: Flask 3, gunicorn 22. |
| `data3.json` | Baked-in AR snapshot embedded by `build_v4.py`. Refresh + commit to redeploy with newer data. |

The generated `build/` directory is gitignored — everything in it is
regenerable from `build_v4.py`.

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

## Deploy — Apps Script

1. Open the Apps Script project bound to the AR spreadsheet.
2. Replace the contents of `code.gs` with the freshly generated one.
3. **Deploy → Manage deployments → Edit (pencil) → Version: New version → Deploy.**
   Keeping the same deployment edit preserves the existing `/exec` URL.
4. Hard-refresh the browser (Cmd/Ctrl-Shift-R).

## Deploy — Boltic Serverless

Boltic reads `boltic.yaml` and builds the `Dockerfile` on every push to the
connected GitHub branch.

```bash
# 1. Sanity-check the image locally
docker build -t fynd-ar .
docker run --rm -p 8080:8080 fynd-ar
# → open http://localhost:8080

# 2. Push to GitHub — Boltic auto-deploys via the connected app.
git push origin main
```

Refresh the baked-in data by regenerating `data3.json`, committing it, and
pushing — the next build re-runs `build_v4.py` inside the container.

Env vars respected by the app:
- `PORT` — HTTP port (Boltic sets this to 8080).
- `AR_OUT_DIR` — where `build_v4.py` writes the HTML and where `app.py` reads
  it from. Defaults to `/app/build` inside the container.
- `AR_DATA_PATH` — override for the input JSON path (defaults to
  `./data3.json` next to `build_v4.py`).

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
