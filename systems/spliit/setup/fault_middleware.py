"""
fault_middleware.py
Flask proxy for Spliit (port 3002 → 3000) with ADVICE taxonomy fault injection.

Routes:
  /admin/fault/activate    POST  { fault_type, sensor? }
  /admin/fault/deactivate  POST  { fault_type, sensor? }
  /admin/fault/reset       POST
  /admin/fault/status      GET
  /admin/reset             POST  (clears faults + resets state)
  /*                       ALL   proxied to Spliit on localhost:3000

Fault behaviour:
  When ANY fault is active, all /api/trpc/* requests return 503.
  This forces the ioco algorithm to time out waiting for the
  SUT response and return FAIL.
"""

import threading
from typing import Optional
import requests as _req
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

SPLIIT_ORIGIN = "http://localhost:3000"

_active_faults: dict = {}
_fault_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Fault state helpers
# ---------------------------------------------------------------------------

def _any_fault_active() -> bool:
    with _fault_lock:
        return bool(_active_faults)


def _activate(fault_type: str, sensor: Optional[str]):
    key = f"{fault_type}:{sensor}" if sensor else fault_type
    with _fault_lock:
        _active_faults[key] = {"fault_type": fault_type, "sensor": sensor}
    return key


def _deactivate(fault_type: str, sensor: Optional[str]):
    key = f"{fault_type}:{sensor}" if sensor else fault_type
    with _fault_lock:
        _active_faults.pop(key, None)
    return key


def _reset():
    with _fault_lock:
        _active_faults.clear()


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@app.route("/admin/fault/activate", methods=["POST"])
def fault_activate():
    data = request.get_json(force=True, silent=True) or {}
    key = _activate(data.get("fault_type", "unknown"), data.get("sensor"))
    return jsonify({"status": "activated", "fault": key}), 200


@app.route("/admin/fault/deactivate", methods=["POST"])
def fault_deactivate():
    data = request.get_json(force=True, silent=True) or {}
    key = _deactivate(data.get("fault_type", "unknown"), data.get("sensor"))
    return jsonify({"status": "deactivated", "fault": key}), 200


@app.route("/admin/fault/reset", methods=["POST"])
def fault_reset():
    _reset()
    return jsonify({"status": "all_faults_cleared"}), 200


@app.route("/admin/fault/status", methods=["GET"])
def fault_status():
    with _fault_lock:
        return jsonify({"active_faults": dict(_active_faults)}), 200


@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    _reset()
    return jsonify({"status": "reset"}), 200


# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
def proxy(path: str):
    # Block tRPC when any fault is active
    if _any_fault_active() and path.startswith("api/trpc"):
        return Response(
            '{"error":"fault_injected","message":"Service unavailable — fault active"}',
            status=503,
            content_type="application/json",
        )

    target_url = f"{SPLIIT_ORIGIN}/{path}"
    if request.query_string:
        target_url += "?" + request.query_string.decode("utf-8")

    excluded_headers = {"host", "content-length", "transfer-encoding", "connection"}
    fwd_headers = {
        k: v for k, v in request.headers if k.lower() not in excluded_headers
    }

    try:
        resp = _req.request(
            method=request.method,
            url=target_url,
            headers=fwd_headers,
            data=request.get_data(),
            allow_redirects=False,
            timeout=30,
        )
    except _req.exceptions.ConnectionError:
        return Response("Spliit not reachable on port 3000", status=502)
    except _req.exceptions.Timeout:
        return Response("Upstream timeout", status=504)

    resp_headers = [
        (k, v) for k, v in resp.headers.items()
        if k.lower() not in {"content-encoding", "transfer-encoding", "connection"}
    ]
    return Response(resp.content, status=resp.status_code, headers=resp_headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3002, threaded=True)
