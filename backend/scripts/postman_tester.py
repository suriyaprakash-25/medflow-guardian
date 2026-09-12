import httpx
import json

def test_endpoints():
    base_url = "http://127.0.0.1:8080"
    report = []
    
    with httpx.Client(timeout=10.0) as client:
        # 1. Login
        response = client.post(f"{base_url}/api/auth/login", data={
            "username": "doctor@demo.com",
            "password": "password"
        })
        if response.status_code != 200:
            report.append({"endpoint": "/api/auth/login", "status": response.status_code, "result": "FAIL"})
            print(json.dumps(report))
            return
            
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        report.append({"endpoint": "/api/auth/login", "status": 200, "result": "PASS"})
        
        # Endpoints to test
        endpoints = [
            ("/api/auth/me", "GET"),
            ("/api/triage/", "GET"),
            ("/api/visits/doctor", "GET"),
            ("/api/appointments/doctor/2", "GET"),
            ("/api/access-requests/doctor", "GET"),
            ("/api/access-grants/doctor", "GET"),
            ("/api/notifications", "GET"),
            ("/api/audit/doctor", "GET")
        ]
        
        for endpoint, method in endpoints:
            try:
                res = client.request(method, f"{base_url}{endpoint}", headers=headers)
                status = "PASS" if res.status_code in (200, 201) else "FAIL"
                report.append({"endpoint": endpoint, "status": res.status_code, "result": status})
            except Exception as e:
                report.append({"endpoint": endpoint, "status": str(e), "result": "FAIL"})
                
    with open("postman_report.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    test_endpoints()
