"""Flask server that hosts the Fynd Receivables Insights dashboard.

The dashboard HTML is generated at Docker build time by build_v4.py and
placed in ./build/Fynd_Receivables_Insights.html.

Boltic serverless sets PORT (default 8080) and probes / for a 200 response.
"""

import os
from flask import Flask, Response, send_file, jsonify

HERE      = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.environ.get("AR_OUT_DIR", os.path.join(HERE, "build"))
FULL_HTML = os.path.join(BUILD_DIR, "Fynd_Receivables_Insights.html")
SLIM_HTML = os.path.join(BUILD_DIR, "Fynd_Receivables_Insights__slim.html")

app = Flask(__name__)


def _pick_dashboard() -> str:
    """Prefer the FULL (data-embedded) HTML, fall back to slim if only that exists."""
    if os.path.exists(FULL_HTML):
        return FULL_HTML
    if os.path.exists(SLIM_HTML):
        return SLIM_HTML
    return ""


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
    # send_file streams the ~4 MB file and sets Content-Type: text/html
    return send_file(path, mimetype="text/html")


@app.route("/health")
def health():
    path = _pick_dashboard()
    return jsonify(
        status="ok" if path else "degraded",
        dashboard=os.path.basename(path) if path else None,
        build_dir=BUILD_DIR,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
