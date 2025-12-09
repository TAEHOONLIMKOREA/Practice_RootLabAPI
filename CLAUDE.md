# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RootLab API 클라이언트 - 반도체 제조 공정 모니터링을 위한 Python API 클라이언트 및 GUI 테스트 도구

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# GUI 앱 실행
python gui_app.py
```

## Architecture

```
Practice_RootLabAPI/
├── gui_app.py           # PyQt5 GUI 테스트 도구 (메인 진입점)
├── Modules/
│   ├── auth.py          # AES-CBC 암호화 (로그인용)
│   ├── fetcher.py       # HTTP API 클라이언트 (데이터 조회/다운로드)
│   └── uploader.py      # TCP 소켓 파일 업로드
└── Reference/           # 참고용 기존 코드 (수정하지 않음)
```

### Core Components

- **DataFetcher** (`Modules/fetcher.py`): 로그인, 테이블 조회, 파일 다운로드
  - 로그인: AES-CBC 암호화 (SHA256 해시 키, IV: 0x00*16, 블록 크기 32)
  - API 엔드포인트: `http://114.108.139.100:8500/api/info`
  - 테이블: tb_machine, tb_machine_retention, tb_build_process, tb_build_strategy, tb_design, tb_material, tb_file

- **DataUploader** (`Modules/uploader.py`): TCP 소켓 기반 파일 업로드
  - 업로드 서버: `114.108.139.100:8600`
  - 파일 타입: STTLG, PSTTLGF, PSTTLGS, RTISN, RTIDP, MEPIG, MEPBR

- **GUI** (`gui_app.py`): PyQt5 + QThread 비동기 작업
  - WorkerThread: 로그인, 다운로드, 업로드, API 테스트 수행

### API Request Format

```python
# 테이블 조회
{"type": "get", "token": token, "table": "tb_xxx", ...}

# 파일 다운로드
{"type": "view", "token": token, "file_sn": "xxx"}

# 로그인
{"type": "login", "userId": id, "userPw": encrypted_pw}
```

### Key Notes

- API 파라미터 (`retention_sn`, `table_sn` 등)는 문자열로 전달해야 함
- 로그인 시 company 값은 user_id와 동일하게 사용
- 응답 데이터는 `ast.literal_eval` 또는 `json.loads`로 파싱
