import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app


client = TestClient(app)

def test_disponibilidad_recursos():
    response = client.get("/disponibilidad_recursos", params={"patient_id": "24fff615-f135-4a92-afc9-049e7467d277"})
    print("📥 Response status:", response.status_code)
    print("📦 Response body:", response.text)
    assert response.status_code in [200, 404]
