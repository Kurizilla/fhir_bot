import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app


client = TestClient(app)

def test_get_observaciones():
    response = client.get("/observaciones", params={"patient": "Patient/f24ea30c-f53a-485c-b4c5-1b76373f9953"})
    print("📥 Response status:", response.status_code)
    print("📦 Response body:", response.text)
    assert response.status_code in [200, 404]
