import httpx
import json
from typing import Optional, Tuple
from enum import Enum
from .auth import AESCipher


class Company(Enum):
    CORP01 = "corp01"
    CORP02 = "corp02"
    CORP03 = "corp03"


class DataFetcher:
    BASE_URL = "http://114.108.139.100:8500"
    AES_KEY = "3dpdx!*#$rootlabaes!&$#2025&$#%5"

    def __init__(self, token: str = None, build_id: str = None, company: str = "corp01"):
        self.token = token
        self.build_id = build_id
        self.company = company

    @classmethod
    async def login(cls, user_id: str, user_pw: str) -> Optional[str]:
        """로그인하여 토큰 가져오기"""
        cipher = AESCipher(cls.AES_KEY)
        encrypted_pw = cipher.encrypt(user_pw)

        payload = {
            "type": "login",
            "userId": user_id,
            "userPw": encrypted_pw
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{cls.BASE_URL}/api/info", json=payload)
                resp.raise_for_status()
                result = resp.json()
                data_str = result.get("data")

                if not data_str or data_str == "API Fail":
                    print("로그인 실패: 잘못된 ID 또는 비밀번호")
                    return None

                # JSON 파싱
                fixed_json = data_str.replace("'", '"')
                data = json.loads(fixed_json)
                token = data.get("token")

                if token:
                    print("로그인 성공")
                    return token
                else:
                    print("토큰을 찾을 수 없습니다")
                    return None

            except Exception as e:
                print(f"로그인 에러: {e}")
                return None

    async def _api_request(self, file_type: str) -> Optional[list]:
        """API에서 파일 정보 조회"""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "type": "get",
                    "token": self.token,
                    "table": "tb_file",
                    "table_name": "build_process",
                    "table_sn": self.build_id,
                    "file_type": file_type
                }
                resp = await client.post(f"{self.BASE_URL}/api/info", json=payload)
                resp.raise_for_status()
                data_str = resp.json().get("data", "[]")

                if data_str == "[]":
                    return None

                return json.loads(data_str.replace("'", '"'))
            except Exception as e:
                print(f"API error: {e}")
                return None

    async def _download_file(self, file_sn: str) -> Optional[bytes]:
        """파일 다운로드"""
        if not file_sn:
            return None

        async with httpx.AsyncClient() as client:
            try:
                payload = {"type": "view", "token": self.token, "file_sn": file_sn}
                resp = await client.post(f"{self.BASE_URL}/view", json=payload)
                resp.raise_for_status()
                return resp.content
            except Exception as e:
                print(f"Download error: {e}")
                return None

    def _find_file_sn(self, data: list, pattern: str) -> Optional[str]:
        """파일명으로 SN 검색"""
        if not data:
            return None

        for item in data:
            file_name = item.get("orgnl_file_nm", "")
            if pattern in file_name:
                return item.get("file_sn")
        return None

    async def fetch_log(self) -> Optional[bytes]:
        """로그 데이터 다운로드"""
        data = await self._api_request("PSTTLGF")
        if not data:
            return None

        file_sn = data[0].get("file_sn")
        return await self._download_file(file_sn)

    async def fetch_vision(self, layer: int = 1) -> Tuple[Optional[bytes], Optional[bytes]]:
        """스캐닝 & 디포지션 이미지 다운로드"""
        layer = max(1, layer)

        # 데이터 조회
        data_sn = await self._api_request("RTISN")
        data_dp = await self._api_request("RTIDP")

        # 스캐닝 이미지
        scanning = None
        if data_sn:
            patterns = [f"{layer}.jpg", f"{layer}.png"]
            if self.company == Company.CORP03.value:
                patterns.append(f"{layer}-Layer")

            for pattern in patterns:
                sn = self._find_file_sn(data_sn, pattern)
                if sn:
                    scanning = await self._download_file(sn)
                    break

        # 디포지션 이미지
        deposition = None
        if data_dp:
            patterns = [f"{layer}.jpg", f"{layer}.png"]
            if self.company == Company.CORP03.value:
                patterns.append(f"{layer}-Layer")

            for pattern in patterns:
                dp = self._find_file_sn(data_dp, pattern)
                if dp:
                    deposition = await self._download_file(dp)
                    break

        return (scanning, deposition)
