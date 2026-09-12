import requests
import json
import sys

BASE_URL = "http://localhost:8080/api"

def login(email, password):
    print(f"Logging in {email}...")
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if response.status_code != 200:
        print(f"FAILED TO LOGIN {email}: {response.text}")
        sys.exit(1)
    print(f"Login success: {email}")
    return response.json()

def get_me(token):
    print("Getting me...")
    response = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        print(f"FAILED TO GET ME: {response.text}")
        sys.exit(1)
    print("Got me.")
    return response.json()

def send_message(token, receiver_id, content):
    print(f"Sending message to {receiver_id}...")
    response = requests.post(
        f"{BASE_URL}/messages", 
        json={"receiver_id": receiver_id, "content": content},
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code != 200:
        print(f"FAILED TO SEND MESSAGE: {response.text}")
        return None
    print("Sent message.")
    return response.json()

def get_messages(token, other_user_id):
    print(f"Getting messages with {other_user_id}...")
    response = requests.get(
        f"{BASE_URL}/messages/{other_user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5
    )
    if response.status_code != 200:
        print(f"FAILED TO GET MESSAGES: {response.text}")
        return None
    print("Got messages.")
    return response.json()

def run_tests():
    report = []
    report.append("# Postman Messaging API Test Report")
    
    # 1. Login
    try:
        patient_auth = login("patient@demo.com", "password")
        doctor_auth = login("doctor@demo.com", "password")
        report.append("- [x] Successfully authenticated as Patient and Doctor")
    except Exception as e:
        report.append(f"- [ ] Authentication failed: {str(e)}")
        return "\n".join(report)

    patient_token = patient_auth['access_token']
    doctor_token = doctor_auth['access_token']

    patient_me = get_me(patient_token)
    doctor_me = get_me(doctor_token)
    
    patient_id = patient_me['id']
    doctor_id = doctor_me['id']
    
    report.append(f"- [x] Retrieved IDs: Patient ({patient_id}), Doctor ({doctor_id})")

    # 2. Patient sends message to Doctor
    msg_content = "Hello Doctor, this is a test from the patient."
    sent_msg = send_message(patient_token, doctor_id, msg_content)
    if sent_msg and sent_msg['content'] == msg_content:
        report.append("- [x] Patient successfully sent message to Doctor API (`POST /messages`)")
    else:
        report.append("- [ ] Patient failed to send message to Doctor API")

    # 3. Doctor fetches messages
    doctor_msgs = get_messages(doctor_token, patient_id)
    if doctor_msgs and any(m['content'] == msg_content for m in doctor_msgs):
        report.append("- [x] Doctor successfully fetched messages and verified receipt (`GET /messages/{user_id}`)")
    else:
        report.append("- [ ] Doctor failed to fetch or verify message receipt")

    # 4. Doctor sends reply to Patient
    reply_content = "Hello Patient, I have received your test message."
    sent_reply = send_message(doctor_token, patient_id, reply_content)
    if sent_reply and sent_reply['content'] == reply_content:
        report.append("- [x] Doctor successfully sent reply message to Patient API (`POST /messages`)")
    else:
        report.append("- [ ] Doctor failed to send reply to Patient API")

    # 5. Patient fetches messages
    patient_msgs = get_messages(patient_token, doctor_id)
    if patient_msgs and any(m['content'] == reply_content for m in patient_msgs):
        report.append("- [x] Patient successfully fetched messages and verified reply (`GET /messages/{user_id}`)")
    else:
        report.append("- [ ] Patient failed to fetch or verify reply receipt")

    # Final validation
    if all("[x]" in line for line in report if line.startswith("-")):
        report.append("\n**STATUS: PASS** - All endpoints are functioning correctly. Doctor and Patient are successfully connected.")
    else:
        report.append("\n**STATUS: FAIL** - Errors were encountered during messaging endpoint testing.")

    print("\n".join(report))
    
    with open("C:/Users/Suriy/.gemini/antigravity-ide/brain/229230bc-1e63-4902-b5c7-6a7e1fc185e8/postman_messaging_report.md", "w") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    run_tests()
