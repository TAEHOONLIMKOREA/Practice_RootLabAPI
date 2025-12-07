import asyncio
import httpx
import json
from Modules.auth import AESCipher


async def test_login():
    BASE_URL = "http://114.108.139.100:8500"
    AES_KEY = "3dpdx!*#$rootlabaes!&$#2025&$#%5"

    cipher = AESCipher(AES_KEY)
    user_id = "corp03"
    user_pw = "*corp12#"
    encrypted_pw = cipher.encrypt(user_pw)

    print(f"User ID: {user_id}")
    print(f"Encrypted PW: {encrypted_pw}")

    payload = {
        "type": "login",
        "userId": user_id,
        "userPw": encrypted_pw
    }

    print(f"\nPayload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{BASE_URL}/api/info", json=payload)
            print(f"\nStatus Code: {resp.status_code}")
            print(f"Response: {resp.text}")

            result = resp.json()
            print(f"\nJSON Response: {json.dumps(result, indent=2, ensure_ascii=False)}")

        except Exception as e:
            import traceback
            print(f"Error: {e}")
            print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(test_login())
