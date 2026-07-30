# Fynd · Receivables Insights

Single-file dashboard for Fynd AR / receivables. Two deployment targets are
supported from the same source of truth, both auto-deployed from GitHub:

1. **Google Apps Script** — served as a bound web app off the AR spreadsheet
   (live data via JSONP, always reads the sheet fresh). Auto-pushed by the
   `Deploy · Apps Script` GitHub Actions workflow using [clasp].
2. **Boltic Serverless** — Flask + gunicorn image built from `Dockerfile`;
   Boltic auto-deploys on every push to the connected branch.

The dashboard itself is a self-contained HTML app (Tailwind + Chart.js) that
reads AR, PDD, and Bank Receipt tabs, computes DSO, ageing, follow-up queues,
SOA ledgers, and more, then renders everything client-side.

## Repo layout

| File | Purpose |
|------|---------|
| `build_v4.py` | Emits the dashboard HTML in two flavours: **FULL** (with embedded data from `data3.json`) and **SLIM** (no embedded data, meant to be served by Apps Script and populated live via JSONP). Output dir defaults to `./build/` inside Docker. Overridable via `AR_OUT_DIR`. |
| `build_codegs.py` | Reads the SLIM HTML, base64-encodes + chunks it, and wraps it in the Apps Script backend to produce a single `code.gs` file that hosts the dashboard, exposes the JSON data feed, and handles follow-up emails / auth / worklist / SOA email / workflows. |
| `app.py` | Minimal Flask server for Boltic Serverless. Serves the built HTML at `/`, health at `/health`. |
| `Dockerfile` | Builds the Boltic image: `pip install`, run `build_v4.py`, start `gunicorn` on `$PORT`. |
| `boltic.yaml` | Boltic app config — `builtin: dockerfile`, port 8080, region `asia-south1`, autoscale 1–2. |
| `requirements.txt` | Runtime deps: Flask 3, gunicorn 22. |
| `data3.json` | Baked-in AR snapshot embedded by `build_v4.py` (used by the Boltic image only; Apps Script always reads live from the sheet). Refresh + commit to redeploy with newer data. |
| `apps-script/appsscript.json` | Manifest clasp uses when pushing to the Apps Script project (timezone, OAuth scopes, web-app access). |
| `.github/workflows/deploy-appsscript.yml` | GitHub Actions job: on push to `main`, build `code.gs` and `clasp push` it into your Apps Script project. |

The generated `build/` directory is gitignored — everything in it is
regenerable from `build_v4.py` / `build_codegs.py`.

## Build (local sanity)

```bash
# FULL (embedded data — for local file preview)
python3 build_v4.py

# SLIM (no embedded data — required before build_codegs.py)
python3 build_v4.py --slim

# Wrap the SLIM HTML into a single Apps Script file
python3 build_codegs.py
```

You never need to run these by hand in normal ops — CI does it on every push.

## Deploy — Apps Script (auto-push from GitHub, zero manual paste)

`.github/workflows/deploy-appsscript.yml` handles the Apps Script deploy.
Every push to `main` that touches `build_v4.py`, `build_codegs.py`,
`data3.json`, or the workflow itself will:

1. Build `code.gs` (SLIM HTML embedded).
2. `clasp push` the fresh `code.gs` into your bound Apps Script project.
3. (Optional) Update the existing web-app deployment so the `/exec` URL
   stays stable — if you set the `DEPLOYMENT_ID` secret.

### One-time setup — three GitHub secrets

Do this once per repo, in **Settings → Secrets and variables → Actions →
New repository secret**:

| Secret name | What to paste | How to get it |
|-------------|---------------|---------------|
| `SCRIPT_ID` | The Apps Script project's script ID | In the Apps Script editor: **Project settings (⚙️) → IDs → Script ID**. |
| `CLASPRC_JSON` | Base64 of your `~/.clasprc.json` | See "Getting CLASPRC_JSON" below. |
| `DEPLOYMENT_ID` *(optional)* | The web-app deployment ID that owns your `/exec` URL | Apps Script editor: **Deploy → Manage deployments → copy the Deployment ID** of the row whose URL you want to keep stable. |

#### Getting `CLASPRC_JSON`

On any machine with Node:

```bash
npm install -g @google/clasp@2.4.2
clasp login          # opens a browser → sign in with the Google account
                     # that has edit access to the Apps Script project
base64 -i ~/.clasprc.json | pbcopy    # macOS
# base64 -w0 ~/.clasprc.json           # Linux (no line-wrap; then copy)
```

Paste the base64 blob into the `CLASPRC_JSON` GitHub secret. The workflow
decodes it into the runner's `~/.clasprc.json` before running `clasp push`.

That's it. From here on: **every `git push origin main` deploys the
dashboard**. No touching the Apps Script editor.

### Manual re-deploy

Trigger the workflow by hand from **Actions → Deploy · Apps Script →
Run workflow** — handy for redeploying without a code change (e.g., after
rotating a secret).

## Deploy — Boltic Serverless

Boltic reads `boltic.yaml` and builds the `Dockerfile` on every push to the
connected GitHub branch.

```bash
# Sanity-check the image locally
docker build -t fynd-ar .
docker run --rm -p 8080:8080 fynd-ar
# → open http://localhost:8080
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
  payload. **Live-only**: the CacheService read is disabled by default so
  every JSONP hit re-reads the sheet; `?cache=1` is an opt-in for future
  callers. The dashboard also appends `nocache=1` on every request and the
  Hard Refresh button additionally hits `?action=dataRefresh` to purge any
  cache written by an opt-in caller.
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

[clasp]: https://github.com/google/clasp
