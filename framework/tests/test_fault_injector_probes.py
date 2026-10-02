"""Self-test for the Android fault injector's verification probes.

No device: the adb and sqlite calls are replaced by fakes that answer from a
small in-memory "device". What is checked is the bookkeeping the walker and
the results depend on:

  * an inject whose probe agrees is confirmed and not in `unconfirmed`;
  * an inject whose probe disagrees is in `unconfirmed` (and the command still
    counts as active, so restore() will undo it);
  * a fault with no probe is assumed (None), never counted against;
  * a restore whose probe disagrees lands in `restore_failures`;
  * `manifested()` answers from the probe for a fault the name-keyed cases do
    not know, and still returns None for an unknown fault with no probe, so a
    mapping without probes behaves exactly as before.

    .venv/bin/python -m pytest framework/tests/test_fault_injector_probes.py -q
"""
import copy
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from concretization.fault_injector import AndroidFaultInjector  # noqa: E402

MAPPING = {
    "android": {"package": "com.example.sut", "db": "databases/sut.db"},
    "faults": {
        "DB_TRIGGER": {
            "timing": "gate", "mechanism": "sqlite",
            "inject": "CREATE TRIGGER t1 BEFORE INSERT ON T BEGIN SELECT RAISE(ABORT,'x'); END",
            "restore": "DROP TRIGGER IF EXISTS t1",
            "verify_injected": {"payload": "SELECT name FROM sqlite_master WHERE name='t1'", "equals": "t1"},
            "verify_restored": {"payload": "SELECT name FROM sqlite_master WHERE name='t1'", "equals": ""},
        },
        "FS_FLAG": {
            "timing": "gate", "mechanism": "adb",
            "inject": "run-as {pkg} touch files/flag",
            "restore": "run-as {pkg} rm -f files/flag",
            "verify_injected": {"payload": "run-as {pkg} test -f files/flag && echo present || echo absent", "equals": "present"},
            "verify_restored": {"payload": "run-as {pkg} test -f files/flag && echo present || echo absent", "equals": "absent"},
        },
        "NO_PROBE": {
            "timing": "gate", "mechanism": "adb",
            "inject": "run-as {pkg} touch files/other",
            "restore": "run-as {pkg} rm -f files/other",
        },
    },
}


class FakeDevice:
    """A device whose state is a set of triggers and files; commands and
    queries are interpreted just enough for the probes above. `lying` makes
    the inject commands report success without changing anything, which is
    the case the probes exist to catch."""

    def __init__(self, lying=False):
        self.triggers, self.files, self.lying = set(), set(), lying

    def sql(self, sql):
        if sql.startswith("CREATE TRIGGER"):
            if not self.lying:
                self.triggers.add("t1")
            return True
        if sql.startswith("DROP TRIGGER"):
            self.triggers.discard("t1")
            return True
        return True

    def scalar(self, sql):
        if "sqlite_master" in sql:
            return "t1" if "t1" in self.triggers else ""
        return None

    def shell(self, cmd, **kw):
        if "touch files/flag" in cmd:
            if not self.lying:
                self.files.add("flag")
            return True
        if "rm -f files/flag" in cmd:
            self.files.discard("flag")
            return True
        return True

    def shell_out(self, cmd):
        if "test -f files/flag" in cmd:
            return "present" if "flag" in self.files else "absent"
        return None


def make(lying=False):
    inj = AndroidFaultInjector(copy.deepcopy(MAPPING), device="fake", package="com.example.sut")
    dev = FakeDevice(lying)
    inj._sql = dev.sql
    inj._scalar = dev.scalar
    inj._adb_shell = dev.shell
    inj._adb_shell_out = dev.shell_out
    return inj, dev


def test_inject_confirmed_when_probe_agrees():
    inj, dev = make()
    inj.target = "DB_TRIGGER"
    inj.inject_gate("DB_TRIGGER")
    assert "t1" in dev.triggers
    assert inj.last_verification["DB_TRIGGER"] is True
    assert "DB_TRIGGER" not in inj.unconfirmed
    assert inj.manifested("DB_TRIGGER") is True


def test_inject_unconfirmed_when_probe_disagrees():
    inj, dev = make(lying=True)
    inj.target = "FS_FLAG"
    inj.inject_gate("FS_FLAG")
    assert "flag" not in dev.files                # the command lied
    assert inj.last_verification["FS_FLAG"] is False
    assert "FS_FLAG" in inj.unconfirmed
    assert inj.manifested("FS_FLAG") is False     # the walker can say UNEXECUTABLE, not FAIL


def test_manifested_keeps_the_injection_time_answer():
    inj, dev = make()
    inj.target = "FS_FLAG"
    inj.inject_gate("FS_FLAG")                    # confirmed at the gate
    dev.files.discard("flag")                     # the platform cleans up afterwards
    assert inj.manifested("FS_FLAG") is True      # the fault WAS in place when the walk passed
    inj2, _ = make()
    assert inj2.manifested("FS_FLAG") is False    # never injected in this run: the live probe answers


def test_no_probe_is_assumed_not_counted():
    inj, _ = make()
    inj.target = "NO_PROBE"
    inj.inject_gate("NO_PROBE")
    assert inj.last_verification["NO_PROBE"] is None
    assert not inj.unconfirmed
    assert inj.manifested("NO_PROBE") is None     # unchanged behaviour for probe-less mappings


def test_restore_confirmed_and_unconfirmed():
    inj, dev = make()
    inj.target = "FS_FLAG"
    inj.inject_gate("FS_FLAG")
    assert "flag" in dev.files
    inj.restore()
    assert "flag" not in dev.files
    assert inj.restore_failures == []

    inj, dev = make()
    inj.target = "FS_FLAG"
    inj.inject_gate("FS_FLAG")
    inj._adb_shell = lambda cmd, **kw: True      # restore now "succeeds" without removing the file
    inj.restore()
    assert "flag" in dev.files
    assert inj.restore_failures == ["FS_FLAG"]


def test_unknown_fault_without_probe_is_none():
    inj, _ = make()
    assert inj.manifested("SOMETHING_ELSE") is None
