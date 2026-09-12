import httpx

def test_endpoints():
    base_url = "http://127.0.0.1:8080"
    
    with httpx.Client(timeout=30.0) as client:
        # Login
        response = client.post(f"{base_url}/api/auth/login", data={
            "username": "doctor@demo.com",
            "password": "password"
        })
        token = response.json().get("access_token")
        if not token:
            print("Login failed", response.text)
            return
            
        print(f"Logged in, token: {token[:10]}...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test auth/me
        res = client.get(f"{base_url}/api/auth/me", headers=headers)
        print("auth/me:", res.status_code, res.json())
        
        # Test visits/doctor
        res = client.get(f"{base_url}/api/visits/doctor", headers=headers)
        print("visits/doctor:", res.status_code, res.text[:200])
        
        # Test triage/
        res = client.get(f"{base_url}/api/triage/", headers=headers)
        print("triage/:", res.status_code, res.text[:200])

if __name__ == "__main__":
    test_endpoints()

if __name__ == "__main__":
    test_endpoints()
