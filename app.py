"""Flask server that hosts the Fynd Receivables Insights dashboard.

The dashboard HTML is generated at Docker build time by build_v4.py and
placed in ./build/Fynd_Receivables_Insights.html.

Boltic serverless sets PORT (default 8080) and probes / for a 200 response.

Live-data auto-connect
----------------------
When AR_LIVE_URL is set in the environment (Boltic → Environment Variables),
this server rewrites the response HTML to inject:

    window.__DATA_URL__            = <that URL>
    window.__SERVED_BY_APPS_SCRIPT__ = true

...just before </head>. That means every visitor to the Boltic URL is
auto-connected to live data on first paint — no "Configure live data
source" prompt, no manual URL entry. The variable is intentionally
optional so the container still boots even if the URL isn't set yet.

Google Sign-In (GIS)
--------------------
When AR_GOOGLE_CLIENT_ID is set, we additionally inject:

    window.__REQUIRE_AUTH__     = true
    window.__GOOGLE_CLIENT_ID__ = <client_id>

This turns on the Google Identity Services (GIS) sign-in flow independent
of AR_LIVE_URL. With that in place, every visitor to the Boltic URL sees
the login screen with a "Sign in with Google" button, plus a One Tap
prompt that silently recognises already-signed-in @gofynd.com sessions.
"""

import html
import os
from flask import Flask, Response, jsonify, send_file

HERE      = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.environ.get("AR_OUT_DIR", os.path.join(HERE, "build"))
FULL_HTML = os.path.join(BUILD_DIR, "Fynd_Receivables_Insights.html")
SLIM_HTML = os.path.join(BUILD_DIR, "Fynd_Receivables_Insights__slim.html")

# The Apps Script /exec URL every visitor of this server should talk to.
# Set in boltic.yaml (Environment Variables → AR_LIVE_URL).
LIVE_URL = (os.environ.get("AR_LIVE_URL") or "").strip()

# Google OAuth 2.0 client ID for Google Identity Services (GIS).
# Set in boltic.yaml (Environment Variables → AR_GOOGLE_CLIENT_ID). Get
# one from https://console.cloud.google.com/apis/credentials — create an
# "OAuth 2.0 Client ID" of type "Web application", add the Boltic public
# URL as an authorised JavaScript origin.
GOOGLE_CLIENT_ID = (os.environ.get("AR_GOOGLE_CLIENT_ID") or "").strip()

# Force the login screen even when neither AR_LIVE_URL nor
# AR_GOOGLE_CLIENT_ID are set. Almost always leave this unset — the
# defaults do the right thing.
REQUIRE_AUTH = (os.environ.get("AR_REQUIRE_AUTH") or "").strip().lower() in ("1", "true", "yes", "on")

app = Flask(__name__)


def _pick_dashboard() -> str:
    """Prefer the FULL (data-embedded) HTML, fall back to slim if only that exists."""
    if os.path.exists(FULL_HTML):
        return FULL_HTML
    if os.path.exists(SLIM_HTML):
        return SLIM_HTML
    return ""


def _needs_injection() -> bool:
    """True when the response HTML must have any bootstrap flags injected."""
    return bool(LIVE_URL or GOOGLE_CLIENT_ID or REQUIRE_AUTH)


def _inject_bootstrap(html_text: str) -> str:
    """Splice bootstrap flags (`__DATA_URL__`, `__GOOGLE_CLIENT_ID__`,
    `__REQUIRE_AUTH__`) into the dashboard so shared viewers pick them up
    on first paint.

    Falls back to the untouched HTML when none of the relevant env vars
    are set — in that mode the app behaves exactly like a local file:
    viewers see the "Live Off" pill until an admin opens Settings and
    pastes the URL by hand, and no login screen is enforced.
    """
    if not _needs_injection():
        return html_text
    parts = ["<script>"]
    if LIVE_URL:
        # html.escape guards against HTML injection via the env var; the JS
        # side sees a plain string literal.
        parts.append(f"window.__DATA_URL__ = '{html.escape(LIVE_URL, quote=True)}';")
        parts.append("window.__SERVED_BY_APPS_SCRIPT__ = true;")
    if GOOGLE_CLIENT_ID:
        parts.append(
            f"window.__GOOGLE_CLIENT_ID__ = '{html.escape(GOOGLE_CLIENT_ID, quote=True)}';"
        )
    # __REQUIRE_AUTH__ is implied whenever GOOGLE_CLIENT_ID or LIVE_URL is
    # set (both cases mean "hosted", not local). REQUIRE_AUTH env var lets
    # ops force it on regardless.
    if REQUIRE_AUTH or GOOGLE_CLIENT_ID or LIVE_URL:
        parts.append("window.__REQUIRE_AUTH__ = true;")
    parts.append("</script>")
    injected = "".join(parts)
    # Insert immediately before </head> so it's parsed before the main app JS
    # runs. Case-insensitive replacement, one-shot.
    lower = html_text.lower()
    idx = lower.find("</head>")
    if idx == -1:
        # Odd: no </head>? Prepend as a last resort so behaviour still holds.
        return injected + html_text
    return html_text[:idx] + injected + html_text[idx:]


# Legacy alias — some callers / tests may still reference the old name.
_inject_live_url = _inject_bootstrap


@app.route("/")
def index():
    path = _pick_dashboard()
    if not path:
        return Response(
            "Dashboard HTML not built. Expected "
            f"{FULL_HTML} or {SLIM_HTML} — did the Docker build run "
            "`python build_v4.py`?",
            status=500,
            mimetype="text/plain",
        )
    # When any bootstrap env var is set, splice the flags into the HTML so
    # shared viewers pick them up on first paint. Otherwise stream the file
    # untouched (cheaper — no read into memory).
    if _needs_injection():
        with open(path, "r", encoding="utf-8") as f:
            body = _inject_bootstrap(f.read())
        return Response(body, mimetype="text/html")
    return send_file(path, mimetype="text/html")


@app.route("/health")
def health():
    path = _pick_dashboard()
    return jsonify(
        status="ok" if path else "degraded",
        dashboard=os.path.basename(path) if path else None,
        build_dir=BUILD_DIR,
        live_url_configured=bool(LIVE_URL),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
