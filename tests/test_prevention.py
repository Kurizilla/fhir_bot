import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

client = TestClient(app)

def test_get_prevention():
    response = client.get("/prevention", params={"patient": "Patient/d9774db8-c2ba-4386-85ca-440340a551e3"})
    print("📥 Response status:", response.status_code)
    print("📦 Response body:", response.text)
    assert response.status_code in [200, 404]