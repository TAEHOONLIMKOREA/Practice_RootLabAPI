import httpx
import json
import ast
from .auth import AESCipher


class DataFetcher:
    BASE_URL = "http://114.108.139.100:8500"
    AES_KEY = "3dpdx!*#$rootlabaes!&$#2025&$#%5"

    def __init__(self, token: str = None, build_id: str = None, company: str = None):
        self.token = token
        self.build_id = build_id
        self.company = company

    @classmethod
    def login(cls, user_id: str, user_pw: str):
        """로그인하여 토큰 반환"""
        cipher = AESCipher(cls.AES_KEY)
        payload = {
            "type": "login",
            "userId": user_id,
            "userPw": cipher.encrypt(user_pw)
        }
        with httpx.Client() as client:
            try:
                resp = client.post(f"{cls.BASE_URL}/api/info", json=payload)
                res_json = resp.json()

                resp_code = int(res_json.get("code", 0))
                if resp_code != 200:
                    return None

                data_field = res_json.get("data")
                if isinstance(data_field, str) and data_field.strip().startswith("{"):
                    data_dict = ast.literal_eval(data_field)
                    return data_dict.get("token")
                return None
            except:
                return None

    def _request(self, file_type: str):
        """파일 정보 조회"""
        with httpx.Client() as client:
            try:
                payload = {
                    "type": "get",
                    "token": self.token,
                    "table": "tb_file",
                    "table_name": "build_process",
                    "table_sn": self.build_id,
                    "file_type": file_type
                }
                resp = client.post(f"{self.BASE_URL}/api/info", json=payload)
                data_str = resp.json().get("data", "[]")
                if data_str == "[]":
                    return None
                return ast.literal_eval(data_str)
            except:
                return None

    def _download(self, file_sn: str):
        """파일 다운로드"""
        if not file_sn:
            return None
        with httpx.Client() as client:
            try:
                payload = {"type": "view", "token": self.token, "file_sn": file_sn}
                resp = client.post(f"{self.BASE_URL}/view", json=payload)
                return resp.content
            except:
                return None

    def _find_sn(self, data: list, layer: int):
        """레이어에 맞는 파일 SN 검색"""
        if not data:
            return None
        patterns = [f"{layer}.jpg", f"{layer}.png"]
        if self.company == "corp03":
            patterns.append(f"{layer}-Layer")
        for item in data:
            name = item.get("orgnl_file_nm", "")
            for p in patterns:
                if p in name:
                    return item.get("file_sn")
        return None

    def fetch_log(self):
        """로그 데이터 다운로드"""
        data = self._request("PSTTLGF")
        if not data:
            return None
        return self._download(data[0].get("file_sn"))

    def fetch_vision(self, layer: int = 1):
        """스캐닝 & 디포지션 이미지 다운로드"""
        layer = max(1, layer)
        data_sn = self._request("RTISN")
        data_dp = self._request("RTIDP")
        scanning = self._download(self._find_sn(data_sn, layer))
        deposition = self._download(self._find_sn(data_dp, layer))
        return scanning, deposition

    def _get_table(self, table, **kwargs):
        """테이블 데이터 조회"""
        with httpx.Client() as client:
            try:
                payload = {"type": "get", "token": self.token, "table": table}
                payload.update(kwargs)
                resp = client.post(f"{self.BASE_URL}/api/info", json=payload)
                data_str = resp.json().get("data", "[]")
                
                data = ast.literal_eval(data_str)
                return data
            except Exception as e:
                print(e)
                return data_str

    def get_machines(self):
        """장비 목록 조회"""
        return self._get_table("tb_machine")

    def get_machine_retentions(self):
        """보유 장비 목록 조회"""
        return self._get_table("tb_machine_retention")

    def get_build_processes(self, retention_sn):
        """BP 목록 조회"""
        return self._get_table("tb_build_process", retention_sn=retention_sn)

    def get_build_strategies(self):
        """BS 목록 조회"""
        return self._get_table("tb_build_strategy")

    def get_designs(self):
        """디자인 목록 조회"""
        return self._get_table("tb_design")

    def get_materials(self):
        """소재 목록 조회"""
        return self._get_table("tb_material")

    def get_files(self, table_name, table_sn, file_type):
        """파일 목록 조회"""
        return self._get_table(
            "tb_file", table_name=table_name, table_sn=table_sn, file_type=file_type
        )
