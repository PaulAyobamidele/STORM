"""Mechanism `host` of the Android fault injector: the command runs on the
tester's machine, and its probes are read the same way. No device needed.

    PYTHONPATH=framework .venv/bin/python -m pytest framework/tests/test_fault_injector_host.py -q
"""
from concretization.fault_injector import AndroidFaultInjector


def _inj(tmp_path, spec):
    return AndroidFaultInjector({"faults": {"HOST_FAULT": spec}}, device="none",
                                package="none.pkg", project_root=str(tmp_path))


def test_inject_confirm_restore_confirm(tmp_path):
    flag = tmp_path / "flag"
    inj = _inj(tmp_path, {
        "timing": "gate", "mechanism": "host",
        "inject": f"touch {flag}", "restore": f"rm -f {flag}",
        "verify_injected": {"payload": f"test -f {flag} && echo on || echo off", "equals": "on"},
        "verify_restored": {"payload": f"test -f {flag} && echo on || echo off", "equals": "off"},
    })
    inj.target = "HOST_FAULT"
    inj.inject_gate("HOST_FAULT")
    assert flag.exists()
    assert inj.last_verification["HOST_FAULT"] is True
    assert "HOST_FAULT" not in inj.unconfirmed
    assert inj.manifested("HOST_FAULT") is True
    inj.restore()
    assert not flag.exists()
    assert inj.restore_failures == []


def test_probe_disagreement_is_recorded(tmp_path):
    inj = _inj(tmp_path, {
        "timing": "gate", "mechanism": "host", "inject": "true", "restore": "true",
        "verify_injected": {"payload": "echo off", "equals": "on"},
        "verify_restored": {"payload": "echo on", "equals": "off"},
    })
    inj.target = "HOST_FAULT"
    inj.inject_gate("HOST_FAULT")
    assert "HOST_FAULT" in inj.unconfirmed
    inj.restore()
    assert inj.restore_failures == ["HOST_FAULT"]


def test_probe_mechanism_can_differ_from_the_fault(tmp_path):
    flag = tmp_path / "f2"
    inj = _inj(tmp_path, {
        "timing": "gate", "mechanism": "adb", "inject": "", "restore": "",
        "verify_injected": {"mechanism": "host", "payload": f"touch {flag} && echo ok", "equals": "ok"},
    })
    inj.target = "HOST_FAULT"
    inj.inject_gate("HOST_FAULT")
    assert flag.exists() and inj.last_verification["HOST_FAULT"] is True
