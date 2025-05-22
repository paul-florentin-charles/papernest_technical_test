import os
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_network_coverage_not_found(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"features": []}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
    response = client.get("/network_coverage?addr=InvalidAddress")
    assert response.status_code == 404
    assert response.json()["detail"] == "Address not found."


def test_address_from_wsg84_not_found(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"features": []}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
    response = client.get("/address_from_wsg84?lon=0&lat=0")
    assert response.status_code == 404
    assert response.json()["detail"] == "No address found for these coordinates."
