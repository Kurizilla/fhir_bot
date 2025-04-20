import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app


client = TestClient(app)

def test_get_medications():
    response = client.get("/medicamentos", params={"patient": "Patient/39645b57-bf0b-4ddd-ac2a-96914a4459c8"})
    print("📥 Response status:", response.status_code)
    print("📦 Response body:", response.text)
    assert response.status_code in [200, 404]
