import sys
import os
import traceback

# Ensure the root project directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app import create_app
    app = create_app()
except Exception as e:
    err_msg = traceback.format_exc()
    print("FATAL ERROR ON STARTUP:\n", err_msg, file=sys.stderr)
    from flask import Flask, Response
    app = Flask(__name__)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def error_fallback(path):
        return Response(
            f"<html><body style='background:#0f172a;color:#f87171;font-family:monospace;padding:30px;'>"
            f"<h2>Application Startup Error</h2>"
            f"<pre style='background:#1e293b;padding:20px;border-radius:8px;overflow:auto;'>{err_msg}</pre>"
            f"</body></html>",
            mimetype='text/html',
            status=500
        )

