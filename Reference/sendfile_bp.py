import requests
import json
import sys, os
import asyncio
import ast
import webbrowser
import asyncio, time
from pathlib import Path
import re, tempfile, shutil
import traceback
from collections import defaultdict
from datetime import datetime, timezone

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

from Modules.progress_utils import (ProgressCtx, collect_all_paths, calc_total_bytes, emit_error, ensure_list,
                                    flush_failed_to_stderr, get_token_from_login_info, judge_send_file)
from Modules.config_utils import (
    api_url as uri,
    login_info_file_path,
    design_list_path,
    bp_property_path,
    input_file_path,
    response_file_path,
    webview_base_url
)
from Modules import RootLabAPI_Client
client = RootLabAPI_Client.Client()

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding="utf-8")

session = requests.Session()

# 전역 변수로 창 인스턴스 관리
window = None

        

# 한밭대 m160 전용
def handle_vision_files(paths, token, tableSn, pctx, skipped_files):
    # 1) layer 별로 파일을 모아둔다
    vision_pat = re.compile(
        r"^(?P<layer>\d+)-Layer Shot_(?P<shot>\d+)-trigger_count\.(?P<ext>jpg|png)$",
        re.IGNORECASE,
    )
    buckets = defaultdict(list)
    for raw in map(Path, ensure_list(paths)):
        m = vision_pat.match(raw.name)
        layer = m.group("layer") if m else "unknown"
        buckets[layer].append(raw)

    # 2) 임시 디렉토리 생성
    tmp_dep = tempfile.TemporaryDirectory()
    tmp_scn = tempfile.TemporaryDirectory()
    dep_files, scn_files = [], []

    # 3) layer 별로 첫 번째 → Deposition, 두 번째 → Scanning
    for layer, files in buckets.items():
        # (필요하면 shot 번호 순으로 정렬)
        files.sort(key=lambda p: int(vision_pat.match(p.name).group("shot")) 
                   if vision_pat.match(p.name) else 0)

        for idx, src in enumerate(files):
            ext = src.suffix.lstrip('.').lower()
            new_name = f"{layer}.{ext}"
            if idx == 0:
                dst = Path(tmp_dep.name) / new_name
                dep_files.append(dst)
                shutil.copy2(src, dst)
            elif idx == 1:
                dst = Path(tmp_scn.name) / new_name
                scn_files.append(dst)
                shutil.copy2(src, dst)
            else:
                # 세 번째 이상 파일은 무시하거나 별도 처리
                break

    # 4) 전송
    if dep_files:
        print(f"[INFO] Vision Deposition 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
        judge_send_file(dep_files, token, tableSn, "build_process", "RTIDP", pctx)
    if scn_files:
        print(f"[INFO] Vision Scanning 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
        judge_send_file(scn_files, token, tableSn, "build_process", "RTISN", pctx)

    # 5) 정리
    tmp_dep.cleanup()
    tmp_scn.cleanup()
           
if __name__ == "__main__":
    print("************start sendfile_bp************\n", flush=True)
    ts1 = datetime.now(timezone.utc)

    token = get_token_from_login_info(login_info_file_path)
    
    # JSON 파일에서 폴더 정보 불러오기
    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            input_files = json.load(f)
    except FileNotFoundError:
        emit_error(f"input_files.json 파일을 찾을 수 없습니다.", traceback.format_exc())

    try:
        with open(response_file_path, "r", encoding="utf-8") as f:
            response = json.load(f)
    except FileNotFoundError:
        emit_error(f"response.json 파일을 찾을 수 없습니다.", traceback.format_exc())
        
    data_str = response.get("data", "{}")
    try:
        data_dict = ast.literal_eval(data_str)
    except Exception as e:
        emit_error(f"data 필드를 파싱하는데 문제가 발생했습니다: {e}", traceback.format_exc())

    process_sn = data_dict.get("process_sn")
    
    # 프로그레스바 추가---
    groups = collect_all_paths(input_files)
    total_bytes = calc_total_bytes(groups)
    pctx = ProgressCtx(total_bytes)
    # ------------------
    
    # print("if:\n", input_files, flush=True)

    MachineLog = input_files.get("files").get("directoryPath_MachineLog")
    MeltpoolBright = input_files.get("files").get("directoryPath_MeltpoolBright")
    MeltpoolImage = input_files.get("files").get("directoryPath_MeltpoolImage")
    Scanning = input_files.get("files").get("directoryPath_RecoatingImage/Scanning")
    Deposition = input_files.get("files").get("directoryPath_RecoatingImage/Deposition")
    Vision = input_files.get("files").get("directoryPath_Vision")
    afterSitu_files = input_files.get("files").get("directoryPath_afterSitu_files")
    ChemicalComposition = input_files.get("files").get("directoryPath_afterSitu_files/ChemicalComposition")
    
    if MachineLog: print(f"MachineLogFiles: {len(MachineLog)}", flush=True)
    if MeltpoolBright: print(f"MeltpoolBrightFiles: {len(MeltpoolBright)}", flush=True)
    if MeltpoolImage: print(f"MeltpoolImageFiles: {len(MeltpoolImage)}", flush=True)
    if Scanning: print(f"ScanningFiles: {len(Scanning)}", flush=True)
    if Deposition: print(f"DepositionFiles: {len(Deposition)}", flush=True)
    if Vision: print(f"VisionFiles: {len(Vision)}", flush=True)
    if afterSitu_files: print(f"afterSitu_filesFiles: {len(afterSitu_files)}", flush=True)
    if ChemicalComposition: print(f"ChemicalCompositionFiles: {len(ChemicalComposition)}", flush=True)

    if Vision:
        print(f"[INFO] Vision 파일 처리 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
        handle_vision_files(Vision, token, process_sn, pctx)

    print(f"[INFO] Scanning 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    judge_send_file(Scanning,  token, process_sn, 'build_process', 'RTISN', pctx)
    
    print(f"[INFO] Deposition 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    judge_send_file(Deposition,  token, process_sn, 'build_process', 'RTIDP', pctx)
    
    print(f"[INFO] MeltpoolImage 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    judge_send_file(MeltpoolImage, token, process_sn, 'build_process', 'MEPIG', pctx)

    print(f"[INFO] MachineLog 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    for file in MachineLog:
        print(f"MachineLog file: {file}", flush=True)
        if Path(file).name.startswith("ProcessedLogsV1"):
            judge_send_file([file], token, process_sn, 'build_process', 'PSTTLGF', pctx)
        elif Path(file).name.startswith("ProcessedLogsV2"):
            judge_send_file([file], token, process_sn, 'build_process', 'PSTTLGS', pctx)
        else:
            judge_send_file([file], token, process_sn, 'build_process', 'STTLG', pctx)
    
    print(f"[INFO] MeltpoolBright 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    judge_send_file(MeltpoolBright, token, process_sn, 'build_process', 'MEPBR', pctx)
    
    print(f"[INFO] afterSitu_files 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    judge_send_file(afterSitu_files, token, process_sn, 'build_process', 'AFCOM', pctx)
    
    print(f"[INFO] ChemicalComposition 파일 전송 시작 - 현재 진행률: {pctx.get_progress()}%", flush=True)
    judge_send_file(ChemicalComposition, token, process_sn, 'build_process', 'CMCPN', pctx)
    
    print(f"[INFO] 모든 파일 전송 완료 - 최종 진행률: {pctx.get_progress()}%", flush=True)
    print("공정 파일 전송이 완료되었습니다.")

    ts2 = datetime.now(timezone.utc)
    progress_time = ts2 - ts1
    minutes, seconds = divmod(int(progress_time.total_seconds()), 60)
    print(f"🕛 작업 시간 : {minutes}m {seconds}s")
    
    
    # 전송 작업이 모두 완료되었으면 input_files.json과 response.json 파일 삭제
    # 파일 삭제 처리
    # for file_path in [input_file_path, response_file_path, design_list_path]:
    #     if os.path.exists(file_path):
    #         try:
    #             os.remove(file_path)
    #         except Exception as e:
    #             emit_error(f"{file_path} 파일 삭제 중 오류 발생: {e}", traceback.format_exc())