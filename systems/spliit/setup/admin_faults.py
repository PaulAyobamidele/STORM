from flask import Blueprint, request, jsonify
import threading

fault_blueprint = Blueprint('fault', __name__, url_prefix='/admin/fault')

_active_faults = {}
_fault_lock = threading.Lock()

def get_active_fault(fault_type, sensor=None):
    """Called by SUT business logic to check if a fault is active."""
    with _fault_lock:
        key = f"{fault_type}:{sensor}" if sensor else fault_type
        return _active_faults.get(key)

@fault_blueprint.route('/activate', methods=['POST'])
def activate_fault():
    data = request.get_json()
    fault_type = data.get('fault_type')
    sensor = data.get('sensor')
    key = f"{fault_type}:{sensor}" if sensor else fault_type

    with _fault_lock:
        _active_faults[key] = data

    return jsonify({"status": "activated", "fault": key}), 200

@fault_blueprint.route('/deactivate', methods=['POST'])
def deactivate_fault():
    data = request.get_json()
    fault_type = data.get('fault_type')
    sensor = data.get('sensor')
    key = f"{fault_type}:{sensor}" if sensor else fault_type

    with _fault_lock:
        _active_faults.pop(key, None)

    return jsonify({"status": "deactivated", "fault": key}), 200

@fault_blueprint.route('/status', methods=['GET'])
def fault_status():
    with _fault_lock:
        return jsonify({"active_faults": dict(_active_faults)}), 200

@fault_blueprint.route('/reset', methods=['POST'])
def reset_all():
    with _fault_lock:
        _active_faults.clear()
    return jsonify({"status": "all_faults_cleared"}), 200
