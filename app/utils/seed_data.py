import requests
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:1234@localhost:5433/travel-connect"
engine      = create_engine(DATABASE_URL)
BASE_URL    = "http://localhost:8000"
RANGE_START = 600
RANGE_END   = 700  

for i in range(RANGE_START, RANGE_END):
    requests.post(f"{BASE_URL}/users", json={
        "firstname":               f"user_{i}",
        "lastname":                f"user_{i}",
        "email":                   f"user_{i}@test.com",
        "password":                "testpassword123",
        "confirm_password":        "testpassword123",
        "gender":                  "male"
    })
print("✅ users registered")

with engine.connect() as conn:
    conn.execute(text("""
        UPDATE "user" 
        SET 
            status                   = 'active',
            is_confirmed             = 'Confirmed',
            has_completed_onboarding = 'Onboarded'
        WHERE firstname LIKE 'user_%'
    """))
    conn.commit()
print("✅ mock users activated")

session_1 = requests.Session()
res = session_1.post(f"{BASE_URL}/login", data={
    "username": "eb@yopmail.com",
    "password": "string"
})
print(f"✅ logged in as main user: {res.json().get('message')}")

request_ids = []
for i in range(RANGE_START, RANGE_END):
    with engine.connect() as conn:
        result = conn.execute(text(
            f"SELECT id FROM \"user\" WHERE email = 'user_{i}@test.com'"
        )).fetchone()

    if not result:
        print(f"  → user_{i} not found in DB, skipping")
        request_ids.append(None)
        continue

    receiver_id = result[0]
    res = session_1.post(f"{BASE_URL}/friendship-requests",
        json={"receiver_id": receiver_id}
    )
    data = res.json()
    request_ids.append(data.get("id"))
    print(f"  → request to user_{i} (id={receiver_id}): {data.get('message')}")

print("✅ friend requests sent")

for i, request_id in zip(range(RANGE_START, RANGE_END), request_ids):
    if not request_id:
        continue

    session_i = requests.Session()
    session_i.post(f"{BASE_URL}/login", data={
        "username": f"user_{i}@test.com",
        "password": "testpassword123"
    })

    res = session_i.patch(
        f"{BASE_URL}/friendship-requests/{request_id}/accept"
    )
    print(f"  → user_{i} accepted: {res.json().get('message')}")

print("✅ all friendships created")