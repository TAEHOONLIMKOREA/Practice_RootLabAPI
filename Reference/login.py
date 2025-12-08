import requests
import json
import sys, os
import ast
import traceback

# [3PDX] 공용 모듈 경로 계산
def _get_3pdx_root():
    """[3PDX] 공용 모듈 폴더 경로 반환"""
    file_path = globals().get('__file__', '<stdin>')
    if '<stdin>' not in file_path:
        current_dir = os.path.dirname(os.path.abspath(file_path))
        plugins_dir = os.path.dirname(os.path.dirname(current_dir))
        pdx_root = os.path.join(plugins_dir, '[3PDX]')
        if os.path.isdir(os.path.join(pdx_root, 'Modules')):
            return pdx_root
    python_dir = os.path.dirname(sys.executable)
    binaries_dir = os.path.dirname(python_dir)
    pdx_root = os.path.join(binaries_dir, 'resources', 'app', 'plugins', '[3PDX]')
    if os.path.isdir(os.path.join(pdx_root, 'Modules')):
        return pdx_root
    return os.path.join(os.getcwd(), 'resources', 'app', 'plugins', '[3PDX]')

sys.path.insert(0, _get_3pdx_root())

from Modules import aescrypto
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
KEY = aescrypto.KEY

from Modules.progress_utils import emit_error
from Modules.config_utils import (
    api_login_get_url, login_info_file_path, mode, version
)

def login(property_path):
    try:
        with open(property_path, "r", encoding="utf-8") as f:
            properties = json.load(f)
    except Exception as e:
        emit_error(f"{property_path} 파일을 읽는 중 오류 발생: {e}", traceback.format_exc())

    username = properties.get("userId")
    password = properties.get("userPw")

    aescipher = aescrypto.AESCipher(KEY)
    encrypted_pw = aescipher.encrypt(password)

    session = requests.Session()
    login_data = {
        "type": "login",
        "userId": username,
        "userPw": encrypted_pw,
    }
    print(f'LOGIN_URL: {api_login_get_url}')
    print(f'MODE: {mode}')
    
    print(f'VERSION: {version}')
    
    print("LOGIN_DATA: ",json.dumps(login_data, ensure_ascii=False, indent=2))
    response = session.post(api_login_get_url, json=login_data)
    


    # 먼저 stdout에 전체 응답 찍어둔다(디버그용)
    response_text = response.text

    try:
        res_json = response.json()
        print("LOGIN_RESPONSE", json.dumps(res_json, ensure_ascii=False, indent=2))
    except Exception as e:
        emit_error("로그인 실패: 응답을 JSON으로 해석할 수 없습니다.",
                   debug_msg=f"JSON 파싱 오류: {e}\nraw: {response_text}")

    # print(f"res_json: {res_json}", flush=True)  # stdout

    # (1) 서버가 넘겨주는 code 사용
    #     혹시 문자열일 수도 있으니 int 변환 시도
    try:
        resp_code = int(res_json.get("code", 0))
    except Exception:
        resp_code = 0

    # (2) 분기 로직
    if resp_code == 200:
        # 성공 케이스
        data_field = res_json.get("data")
        if isinstance(data_field, str) and data_field.strip().startswith("{"):
            try:
                data_dict = ast.literal_eval(data_field)
            except Exception as e:
                emit_error("로그인 실패: 데이터 파싱 오류",
                           debug_msg=f"ast.literal_eval 실패: {e}\n{data_field}")
        else:
            emit_error("로그인 정보가 정확하지 않습니다.\n아이디와 비밀번호를 다시 확인해 주세요.",
                       debug_msg=f"data_field 형식 이상: {data_field}")

        token = data_dict.get("token")
        endtime = data_dict.get("endtime")
        company_name = data_dict.get("comp_nm")

        updated_login_info = {
            "token": token,
            "endtime": endtime,
            "company_name": company_name
        }

        try:
            with open(login_info_file_path, "w", encoding="utf-8") as f:
                json.dump(updated_login_info, f, ensure_ascii=False, indent=4)
        except Exception as e:
            emit_error(f"로그인 정보 저장 중 오류 발생: {e}", traceback.format_exc())

        # print("로그인 성공.", flush=True)
        return updated_login_info

    elif resp_code == 201:
        emit_error("로그인 응답 포맷이 올바르지 않습니다. (code: 201)",
                   debug_msg=f"res_json: {res_json}")

    elif resp_code == 220:
        emit_error("내부 API 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요. (code: 220)",
                   debug_msg=f"res_json: {res_json}")

    elif resp_code == 300:
        emit_error("정의되지 않은 오류가 발생했습니다. 관리자에게 문의하세요. (code: 300)",
                   debug_msg=f"res_json: {res_json}")

    elif resp_code == 500:
        # data가 'Unknown Account'이면 로그인 정보 오류, 아니면 서버 문제
        data_val = res_json.get("data", "")
        if str(data_val).strip() == "Unknown Account":
            emit_error("로그인 정보가 정확하지 않습니다.\n아이디와 비밀번호를 다시 확인해 주세요.",
                       debug_msg=f"res_json: {res_json}")
        else:
            emit_error("서버 문제로 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요. (code: 500)",
                       debug_msg=f"res_json: {res_json}")

    else:
        # 정의되지 않은 code
        emit_error(f"로그인 실패: 알 수 없는 코드({resp_code})",
                   debug_msg=f"res_json: {res_json}")

if __name__ == "__main__":
    try:
        input_argv_path = sys.argv[2]

        login(input_argv_path)

    except Exception as e:
        emit_error(str(e), traceback.format_exc())
