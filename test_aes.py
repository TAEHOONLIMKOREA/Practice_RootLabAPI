"""AES 암호화 테스트 - C# 호환성 확인"""
from Modules.auth import AESCipher

# 테스트
key = "3dpdx!*#$rootlabaes!&$#2025&$#%5"
cipher = AESCipher(key)

# 다양한 입력 테스트
test_cases = [
    "*corp12#",
    "test123",
    "password",
]

print("AES 암호화 테스트")
print("=" * 50)
print(f"키: {key}")
print(f"키 길이: {len(key)}")
print("=" * 50)

for password in test_cases:
    encrypted = cipher.encrypt(password)
    print(f"\n원본: {password}")
    print(f"암호화: {encrypted}")
    print(f"길이: {len(encrypted)}")
