import os, sys, json, asyncio, time
from pathlib import Path
import traceback 
import tempfile, shutil, tarfile, io
from Modules import RootLabAPI_Client


FAILED_MARKER = "[[FAILED_FILES]]"
MAX_RETRY   = 2
RETRY_DELAY = 2

class ProgressCtx:
    def __init__(self, total: int):
        self.total = total
        self.sent = 0
        self.last_pct = -1

    def emit(self, inc: int = 0):
        """증분 바이트만큼 누적하고, 전체 대비 %를 출력"""
        self.sent += inc
        if self.total <= 0:
            pct = 100
        else:
            pct = int(self.sent * 100 / self.total)
        if pct != self.last_pct:
            self.last_pct = pct
            print(f"PROGRESS:{pct}", flush=True)
    
    def get_progress(self):
        """현재 진행률을 반환"""
        if self.total <= 0:
            return 100
        return int(self.sent * 100 / self.total)


def ensure_list(maybe):
    if maybe is None:
        return []
    if isinstance(maybe, (str, Path)):
        return [maybe]
    return list(maybe)


def expand_paths(paths):
    """파일/폴더 섞인 리스트를 모두 파일로 펼침"""
    out = []
    for p in map(Path, ensure_list(paths)):
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend([f for f in p.rglob('*') if f.is_file()])
    return out


def collect_all_paths(input_files: dict) -> dict[str, list[Path]]:
    """
    input_files['files']의 'directoryPath_'로 시작하는 키들의 모든 파일/폴더를
    Path 리스트로 변환 (존재하는 것만 필터링)
    """
    files_section = input_files.get("files", {}) or {}
    groups = {}
    for key, val in files_section.items():
        if not key.startswith("directoryPath_"):
            continue
        expanded = expand_paths(val)
        groups[key] = [p for p in expanded if p.exists()]
    return groups


def calc_total_bytes(groups: dict[str, list[Path]]) -> int:
    total = 0
    for paths in groups.values():
        for p in paths:
            try:
                total += p.stat().st_size
            except FileNotFoundError:
                pass
    return total

def emit_error(user_msg: str, debug_msg: str = None, exit_code: int = 1):
    if debug_msg:
        print(debug_msg, flush=True)
    sys.stderr.write(user_msg + "\n")
    sys.stderr.flush()
    sys.exit(exit_code)


# 실패한 파일 목록을 stderr에 한 번에 출력
def flush_failed_to_stderr(failed_names: list[str]):
    sys.stderr.flush()
    front_msg = f"다음 파일은 업로드에 실패하였습니다.\n{failed_names}"
    emit_error(user_msg=front_msg, exit_code=3)
    

def get_token_from_login_info(file_path: str) -> str:
    """
    지정된 파일에서 token 값을 추출합니다.
    오류 시 emit_error 호출.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            token = data.get("token")
            if not token:
                emit_error("token 값이 존재하지 않습니다.", None, exit_code=1)
            return token
    except Exception as e:
        emit_error(f"{file_path} 파일을 읽는 중 오류 발생: {e}", traceback.format_exc())


def process_files(file_paths, token: str, tableSn, tableNm: str, fileType: str, pctx: ProgressCtx):
     """
     파일 전송 루프 + 재시도 로직.
     on_total_inc=pctx.emit 을 쓰도록 고정.
     """
     paths = ensure_list(file_paths)
     paths = [Path(p) for p in paths if p and Path(p).exists()]
     failed_files = []
     for src in paths:
        file_size = src.stat().st_size
        for attempt in range(1, MAX_RETRY+1):
            attempt_start = pctx.sent
            try:
                # 파일 크기에 따른 동적 타임아웃 계산 (최소 60초, 1MB당 10초 추가)
                file_size_mb = file_size / (1024 * 1024)
                dynamic_timeout = max(60, int(60 + file_size_mb * 10))
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')} CALCULATE] File size: {file_size_mb:.1f}MB, Timeout: {dynamic_timeout}s", flush=True)
                
                client = RootLabAPI_Client.Client()
                asyncio.run(
                    asyncio.wait_for(
                        client.run(
                            str(src),
                            token,
                            tableSn,
                            tableNm,
                            fileType,
                            on_total_inc=pctx.emit
                        ), timeout=dynamic_timeout
                    )
                )                
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n ========= SEND SUCCESS SUMMARY ========", flush=True)
                print(f" TIME        : {timestamp}", flush=True)
                print(f" FILENAME    : {src.name}", flush=True)
                print(f" TABLE_SN    : {tableSn}", flush=True)
                print(f" TABLE_NAME  : {tableNm}", flush=True)
                print(f" FILE_TYPE   : {fileType}", flush=True)
                print(f" ATTEMPT     : {attempt}/{MAX_RETRY}", flush=True)
                print(f" ======================================\n", flush=True)
                break
            except (asyncio.TimeoutError, ConnectionError, Exception) as e:
                print(f"⚠️  [{time.strftime('%Y-%m-%d %H:%M:%S')}] {src.name} Send Failed  (Attempt {attempt}/{MAX_RETRY}) → {e}", flush=True)
                partial = pctx.sent - attempt_start
                if partial > 0:
                    pctx.emit(-partial)
                    
                if attempt < MAX_RETRY:
                    print(f"   {RETRY_DELAY} seconds later retry...", flush=True)
                    time.sleep(RETRY_DELAY)
                else:
                    msg = f"❌ [{time.strftime('%Y-%m-%d %H:%M:%S')}] {src.name} {MAX_RETRY} times failed Skip"
                    print(msg, flush=True)
                    failed_files.append(src.name)
                    pctx.total -= file_size
                    pctx.emit(0)
                    break
    
     if failed_files:
        flush_failed_to_stderr(failed_files)


def judge_send_file(paths, token, tableSn, tableNm: str, fileType: str, pctx) :
    if not paths:
        print(f"[INFO] 입력된 경로가 없습니다. (fileType={fileType})", flush=True)
        return

    files = []
    for item in paths:
        p = Path(item)
        if p.is_dir():
            files.extend([c for c in p.iterdir() if c.is_file()])
        elif p.is_file():
            files.append(p)

    if not files:
        print(f"[INFO] No files to send (fileType={fileType})", flush=True)
        return False

    tar_path = None
    if len(files) > 1:
        print(f'[INFO] {len(files)} zip start...', flush=True)
        # 압축 과정을 위한 총 크기 계산 (복사 + 압축)
        total_zip_size = sum(f.stat().st_size for f in files if f.exists()) * 2
        zip_process = ProgressCtx(total_zip_size)
        tar_path = tar_packing_and_process_files(files, tableSn, tableNm, fileType, zip_process)
        files = [tar_path]

    process_files(files, token, tableSn, tableNm, fileType, pctx)

    # 전송 완료 후 임시 tar.gz 파일 삭제
    if tar_path and tar_path.exists():
        try:
            tar_path.unlink()
            print(f"[CLEANUP] Deleted temporary tar file: {tar_path}", flush=True)
        except Exception as e:
            print(f"[CLEANUP] Failed to delete temporary tar file: {tar_path}, error: {e}", flush=True)


def normalize_name(path: Path) -> str:
    """
    • SIxxxxxxxxxxxx_<n>_....jpg  →  <n>.jpg   (선행 0 제거)
    • 00415.png                  →  415.png    (파일명 전체가 숫자일 때 선행 0 제거)
    그 외엔 원본 이름 유지
    """
    stem, ext = path.stem, path.suffix
    # Case 1: SI…_
    if stem.startswith("SI") and "_" in stem:
        num_token = stem.split("_", 1)[1].split("_", 1)[0]  # 첫 토큰
        return f"{int(num_token)}{ext}"      # int() 로 선행 0 제거

    # Case 2: ‘숫자만’ 파일명
    if stem.isdigit():
        return f"{int(stem)}{ext}"

    return path.name

def tar_packing_and_process_files(paths, tableSn, tableNm, fileType, pctx):
    """
    ① paths 를 temp 디렉터리에 복사하며 이름 정규화
    ② 정규화된 파일들을 tar.gz로 묶고(manifest 포함)
    ③ tar 파일을 내 로컬(Downloads/KBDF_Tars)에도 저장
    ④ 저장된 tar 1개를 process_files()로 전송
    """
    if isinstance(paths, (str, Path)):
        paths = [Path(paths)]

    def unique_target_name(src: Path, used: set[str]) -> str:
        base = normalize_name(src)           # 사용자 제공 함수
        root, ext = os.path.splitext(base)
        if not ext:
            ext = src.suffix  # 정규화 과정에서 확장자가 빠졌다면 원본 확장자 보존
        cand = f"{root}{ext}"
        i = 1
        while cand in used:
            cand = f"{root}__{i}{ext}"
            i += 1
        used.add(cand)
        return cand

    tmp_files = []
    with tempfile.TemporaryDirectory() as tdir:
        tdir_path = Path(tdir)
        used_names: set[str] = set()

        # 전체 파일 크기 계산 (복사 + 압축)
        total_file_size = 0
        valid_paths = []
        for p in paths:
            p = Path(p)
            if p.exists() and p.is_file():
                total_file_size += p.stat().st_size
                valid_paths.append(p)
        
        if not valid_paths:
            print("[INFO] No files to send.")
            return

        # ① 복사 + 이름 정규화(충돌 방지)
        for idx, p in enumerate(valid_paths):
            new_name = unique_target_name(p, used_names)
            dst = tdir_path / new_name
            shutil.copy2(p, dst)
            tmp_files.append(dst)
            
            # 실제 복사된 크기만큼 진행률 업데이트
            file_size = dst.stat().st_size
            pctx.emit(file_size)  # 복사된 바이트만큼 진행률 증가

        # ② tar.gz 묶기
        tar_name = f"{tableNm}_{fileType}_{len(tmp_files)}files.tar.gz"
        tar_path = tdir_path / tar_name
        
        with tarfile.open(tar_path, "w:gz") as tar:
            for f in tmp_files:
                tar.add(f, arcname=f.name)  # arcname 충돌 없음(위에서 유니크 보장)
                
                # 압축 과정도 실제 파일 크기만큼 진행률 업데이트
                file_size = f.stat().st_size
                pctx.emit(file_size)  # 압축된 바이트만큼 진행률 증가

        # 임시 디렉터리가 삭제되기 전에 임시 파일을 외부로 이동
        temp_tar_path = Path(tempfile.gettempdir()) / tar_name
        shutil.move(tar_path, temp_tar_path)
        
        print(f"[TAR] Temporary Save → {temp_tar_path}", flush=True)
        return temp_tar_path

