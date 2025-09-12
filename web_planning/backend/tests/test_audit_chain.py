import os
import json
import shutil
from pathlib import Path
from common import audit_chain as AC


def setup_module(_m):
    # put audit dir in a temp path for tests
    os.environ["EID_AUDIT_DIR"] = "web_planning/backend/state/audit_test"
    Path(os.environ["EID_AUDIT_DIR"]).mkdir(parents=True, exist_ok=True)


def teardown_module(_m):
    shutil.rmtree(os.environ["EID_AUDIT_DIR"], ignore_errors=True)


def test_happy_path_verify_single_day():
    d = AC._today_str()
    AC.append_event(
        actor="tester", action="plan.create", ctx={"x": 1}, payload={"a": 1}
    )
    AC.append_event(
        actor="tester", action="plan.approve", ctx={"x": 2}, payload={"a": 2}
    )
    rep = AC.verify_range(d)
    assert rep["ok"] is True
    assert rep["days"][0]["ok"] is True


def test_detect_tamper():
    d = AC._today_str()
    AC.append_event(
        actor="tester", action="broadcast.send", ctx={"ch": "s"}, payload={"b": 3}
    )
    # Tamper: edit the last line
    fp = AC._file_for(d)
    lines = fp.read_text(encoding="utf-8").splitlines(True)
    assert len(lines) >= 1
    last = json.loads(lines[-1])
    last["action"] = "broadcast.TAMPERED"
    lines[-1] = json.dumps(last) + "\n"
    fp.write_text("".join(lines), encoding="utf-8")
    rep = AC.verify_range(d)
    assert rep["ok"] is False
    assert rep["days"][0]["ok"] is False
    assert rep["days"][0]["reason"] in ("entry_hash_mismatch", "prev_hash_mismatch")
