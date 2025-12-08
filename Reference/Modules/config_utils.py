# Modules/config_utils.py
import os
import sys
import json
import traceback

try:
    from Modules.progress_utils import emit_error
except ModuleNotFoundError:
    # stdin으로 실행될 때 상대 import 시도
    try:
        from .progress_utils import emit_error
    except ImportError:
        # fallback: emit_error 함수 정의
        def emit_error(user_msg, debug_msg=None, exit_code=1):
            if debug_msg:
                print(debug_msg, flush=True)
            import sys
            sys.stderr.write(user_msg + "\n")
            sys.stderr.flush()
            sys.exit(exit_code)

# ──────────── 1) 베이스 디렉토리, config 파일 경로 ────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_config_file_path():
    """[3PDX]/config.json 경로 반환"""
    # BASE_DIR = [3PDX] 폴더 (Modules의 부모)
    # config.json은 BASE_DIR과 같은 위치
    return os.path.join(BASE_DIR, "config.json")

CONFIG_FILE  = _get_config_file_path()

# ──────────── 1-1) 경로 템플릿 해석 함수 ────────────
def get_project_root():
    """
    프로젝트 루트 디렉토리 찾기 (KBDF.exe가 있는 Binaries 폴더)
    Modules가 resources/app/plugins/[3PDX]/Modules에 있다고 가정
    [3PDX] → plugins → app → resources → Binaries (3단계 상위)
    """
    current = BASE_DIR
    for _ in range(3):  # 3단계 상위로 이동 (Binaries 폴더)
        current = os.path.dirname(current)
    return current

def resolve_path_template(path_template, context):
    """
    경로 템플릿 해석
    예: {PROJECT_ROOT}\\.3PDX_Data → C:\\_series\\_kbdf2025_trunk\\.3PDX_Data
    """
    if not isinstance(path_template, str):
        return path_template

    result = path_template
    for key, value in context.items():
        placeholder = f"{{{key}}}"
        result = result.replace(placeholder, value)

    return os.path.normpath(result)

# ──────────── 2) config.json 읽기 함수 ────────────
def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 프로젝트 루트 계산
        project_root = get_project_root()

        # 데이터 루트 디렉토리 결정
        if "data_root" in config:
            data_root = resolve_path_template(config["data_root"], {
                "PROJECT_ROOT": project_root,
                "BASE_DIR": BASE_DIR
            })
        else:
            # 기본값: 프로젝트 루트의 .3PDX_Data
            data_root = os.path.join(project_root, ".3PDX_Data")

        # 모든 경로 필드 해석
        context = {
            "PROJECT_ROOT": project_root,
            "BASE_DIR": BASE_DIR,
            "data_root": data_root
        }

        path_fields = [
            "login_info_file_path",
            "bp_list_path",
            "bs_list_path",
            "bp_property_path",
            "design_list_path",
            "machine_list_path",
            "machine_retention_list_path",
            "input_file_path",
            "response_file_path",
            "retention_file_path",
            "log_path"
        ]

        for field in path_fields:
            if field in config:
                config[field] = resolve_path_template(config[field], context)

        return config

    except Exception as e:
        emit_error(f"{CONFIG_FILE} 구성 파일을 읽는 중 오류 발생: {e}",
                   traceback.format_exc())
        return {}  # 빈 딕셔너리 반환하여 .get() 호출 시 오류 방지

# ──────────── 3) 실제 사용 변수 ────────────
config               = _load_config()
mode                 = config.get("mode")
version              = config.get("version")
file_host            = config.get("file_host")
file_port            = config.get("file_port")
api_url              = config.get("api_url")
api_login_get_url    = config.get("api_login_get_url")
engine_url           = config.get("engine_url")
login_info_file_path = config.get("login_info_file_path")
bp_list_path        = config.get("bp_list_path")
bs_list_path        = config.get("bs_list_path")
bp_property_path    = config.get("bp_property_path")
design_list_path    = config.get("design_list_path")
machine_list_path   = config.get("machine_list_path")
retention_file_path = config.get("retention_file_path")
log_path            = config.get("log_path")
response_file_path   = config.get("response_file_path")
input_file_path      = config.get("input_file_path")
webview_base_url     = config.get("webview_base_url")
machine_retention_list_path     = config.get("machine_retention_list_path")

# ──────────── 4) 필요한 폴더 자동 생성 ────────────
if login_info_file_path:
    os.makedirs(os.path.dirname(login_info_file_path), exist_ok=True)
if bp_list_path:
    os.makedirs(os.path.dirname(bp_list_path), exist_ok=True)
if bs_list_path:
    os.makedirs(os.path.dirname(bs_list_path), exist_ok=True)
if bp_property_path:
    os.makedirs(os.path.dirname(bp_property_path), exist_ok=True)
if design_list_path:
    os.makedirs(os.path.dirname(design_list_path), exist_ok=True)
if machine_list_path:
    os.makedirs(os.path.dirname(machine_list_path), exist_ok=True)
if retention_file_path:
    os.makedirs(os.path.dirname(retention_file_path), exist_ok=True)
if log_path:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
if response_file_path:
    os.makedirs(os.path.dirname(response_file_path), exist_ok=True)
if input_file_path:
    os.makedirs(os.path.dirname(input_file_path), exist_ok=True)
if machine_retention_list_path:
    os.makedirs(os.path.dirname(machine_retention_list_path), exist_ok=True)
