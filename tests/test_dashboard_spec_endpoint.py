import os
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.filterwarnings(
    "ignore:Deprecated import: 'dashboard':DeprecationWarning"
)


def get_client():
    os.environ.setdefault("SAFE_MODE", "1")
    from web_planning.backend.main import app

    return TestClient(app)


def test_dashboard_spec_includes_types_and_caps():
    client = get_client()
    r = client.get("/dashboard/spec")
    assert r.status_code == 200
    data = r.json()
    assert data.get("spec_version") == 1
    assert "kpi" in data.get("widget_types", {})
    assert "line_chart" in data.get("widget_types", {})
    assert "table" in data.get("widget_types", {})
    assert "html" in data.get("widget_types", {})
    assert "limits" in data and "max_widgets" in data["limits"]
