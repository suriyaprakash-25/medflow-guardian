import httpx
import asyncio
import websockets
import json

async def test_flow():
    print("--- Testing Real-time & REST Fallback ---")
    
    # 1. Login to get tokens
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        p_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient_token = p_resp.json()["access_token"]
        
        d_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor_token = d_resp.json()["access_token"]
        
        print("Tokens acquired.")

        # 2. Test REST Fallback (Persistence)
        # Post a reading
        read_resp = await client.post("/api/readings", json={
            "heart_rate": 80,
            "oxygen_level": 98,
            "blood_pressure_sys": 120,
            "blood_pressure_dia": 80,
            "is_simulated": True
        }, headers={"Authorization": f"Bearer {patient_token}"})
        assert read_resp.status_code == 200
        
        # Verify persistence
        get_read_resp = await client.get("/api/readings/1", headers={"Authorization": f"Bearer {doctor_token}"})
        assert get_read_resp.status_code == 200
        assert len(get_read_resp.json()) > 0
        print("REST Fallback (Persistence) Verified.")

    # 3. Test WebSockets
    ws_patient_url = f"ws://localhost:8080/ws?token={patient_token}"
    ws_doctor_url = f"ws://localhost:8080/ws?token={doctor_token}"

    async with websockets.connect(ws_patient_url) as ws_patient, \
               websockets.connect(ws_doctor_url) as ws_doctor:
        
        print("WebSockets connected.")
        
        # Patient sends a REST message, which should be broadcast to Doctor via WS
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            await client.post("/api/messages", json={
                "receiver_id": 2, # doctor id
                "content": "Hello Doctor!"
            }, headers={"Authorization": f"Bearer {patient_token}"})
            
        # Doctor should receive it over WS
        response = await ws_doctor.recv()
        data = json.loads(response)
        assert data["type"] == "message"
        assert data["data"]["content"] == "Hello Doctor!"
        print("WebSocket Broadcast (Message) Verified.")
        
        # Patient posts reading via REST, Doctor gets it via WS
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            await client.post("/api/readings", json={
                "heart_rate": 85,
                "oxygen_level": 99,
                "blood_pressure_sys": 110,
                "blood_pressure_dia": 70,
                "is_simulated": True
            }, headers={"Authorization": f"Bearer {patient_token}"})
            
        response2 = await ws_doctor.recv()
        data2 = json.loads(response2)
        assert data2["type"] == "reading"
        assert data2["data"]["heart_rate"] == 85
        print("WebSocket Broadcast (Live Vitals) Verified.")

    print("--- Phase 5 Verified Successfully! ---")

if __name__ == "__main__":
    asyncio.run(test_flow())
