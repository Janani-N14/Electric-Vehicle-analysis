import pytest

def test_register_driver_success(client):
    payload = {
        "id": "D999",
        "email": "driver999@evfleet.com",
        "password": "PassPassword123",
        "role": "driver",
        "name": "Test Driver",
        "vehicle_id": "EV-D999"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert "Registration successful" in response.json()["message"]
    assert "verification_link" in response.json()

def test_register_duplicate_fail(client):
    payload = {
        "id": "D888",
        "email": "driver888@evfleet.com",
        "password": "PassPassword123",
        "role": "driver",
        "name": "Test Driver 2",
        "vehicle_id": "EV-D888"
    }
    # First registration
    response1 = client.post("/api/auth/register", json=payload)
    assert response1.status_code == 201
    
    # Duplicate registration (same id)
    response2 = client.post("/api/auth/register", json=payload)
    assert response2.status_code == 400  # validation error mapped to 400 Bad Request

def test_login_unverified_fails(client):
    # Register first
    payload = {
        "id": "D777",
        "email": "driver777@evfleet.com",
        "password": "PassPassword123",
        "role": "driver",
        "name": "Test Driver 3",
        "vehicle_id": "EV-D777"
    }
    client.post("/api/auth/register", json=payload)
    
    # Try logging in directly
    login_payload = {
        "id": "D777",
        "email": "driver777@evfleet.com",
        "password": "PassPassword123"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "verify your email" in response.json()["detail"]

def test_verify_and_login_success(client):
    # Register first
    payload = {
        "id": "D666",
        "email": "driver666@evfleet.com",
        "password": "PassPassword123",
        "role": "driver",
        "name": "Test Driver 4",
        "vehicle_id": "EV-D666"
    }
    register_res = client.post("/api/auth/register", json=payload)
    assert register_res.status_code == 201
    
    # Extract verification link
    link = register_res.json()["verification_link"]
    token = link.split("/")[-1]
    
    # Verify email
    verify_res = client.get(f"/api/auth/verify/{token}")
    assert verify_res.status_code == 200
    assert "successfully verified" in verify_res.json()["message"]
    
    # Login successfully
    login_payload = {
        "id": "D666",
        "email": "driver666@evfleet.com",
        "password": "PassPassword123"
    }
    login_res = client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
    assert login_res.json()["role"] == "driver"
    
    # Check that HTTP-Only cookie was set
    assert "access_token" in login_res.cookies
    
    # Test /api/auth/me using the session cookies
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["id"] == "D666"
    assert me_res.json()["role"] == "driver"
    
    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    # Cookie should be deleted
    assert logout_res.cookies.get("access_token") is None
