# WebSocket API 테스트 가이드

## 개요

이 프로젝트는 C# 코드로 만들어진 WebSocket API를 Python으로 테스트하기 위한 라이브러리입니다.

## 파일 구조

```
Practice_RootLabAPI/
├── log_fetcher.py          # 로그 데이터 가져오기
├── vision_fetcher.py       # 비전 데이터 가져오기  
├── test_log_fetcher.py     # 로그 테스트
├── test_vision_fetcher.py  # 비전 테스트
├── test_integration.py     # 통합 테스트
└── README.md
```

## 설치

```bash
pip install websockets httpx pytest pytest-asyncio
```

## 사용 방법

### 1. 로그 데이터 가져오기

```python
import asyncio
from log_fetcher import LogFetcher

async def get_log_data():
    fetcher = LogFetcher(
        token="your_token",
        selected_build_id="build_123"
    )
    
    # 로그 데이터 다운로드
    log_data = await fetcher.fetch_log_data()
    
    if log_data:
        with open("log_output.csv", "wb") as f:
            f.write(log_data)
        print(f"로그 저장됨: {len(log_data)} bytes")

asyncio.run(get_log_data())
```

### 2. 비전 데이터 가져오기

```python
import asyncio
from vision_fetcher import VisionFetcher, CompanyType

async def get_vision_data():
    fetcher = VisionFetcher(
        token="your_token",
        selected_build_id="build_123",
        company_id=CompanyType.CORP01.value
    )
    
    # 비전 데이터 다운로드
    scanning_image, deposition_image = await fetcher.fetch_vision_data(
        cur_layer=1,
        is_check_data=False
    )
    
    if scanning_image:
        with open("scanning_image.jpg", "wb") as f:
            f.write(scanning_image)
        print(f"스캐닝 이미지 저장됨: {len(scanning_image)} bytes")
    
    if deposition_image:
        with open("deposition_image.jpg", "wb") as f:
            f.write(deposition_image)
        print(f"디포지션 이미지 저장됨: {len(deposition_image)} bytes")

asyncio.run(get_vision_data())
```

### 3. 회사별 설정

```python
from vision_fetcher import CompanyType

# CORP01: 기본 설정
company_id = CompanyType.CORP01.value

# CORP02: 추가 처리
company_id = CompanyType.CORP02.value

# CORP03: Layer 패턴 검색
company_id = CompanyType.CORP03.value
```

## 테스트 실행

### 모든 테스트 실행
```bash
pytest
```

### 특정 테스트 파일 실행
```bash
pytest test_log_fetcher.py -v
pytest test_vision_fetcher.py -v
pytest test_integration.py -v
```

### 테스트 커버리지 확인
```bash
pytest --cov=log_fetcher --cov=vision_fetcher
```

## API 명세

### 로그 데이터 API

**요청:**
```json
{
    "type": "get",
    "token": "auth_token",
    "table": "tb_file",
    "table_name": "build_process",
    "table_sn": "build_id",
    "file_type": "PSTTLGF"
}
```

**응답:**
```json
{
    "data": "[{'file_sn': '12345', 'file_name': 'log.csv', ...}]",
    "status": "success"
}
```

### 비전 데이터 API

**RTISN 요청 (스캐닝):**
```json
{
    "type": "get",
    "token": "auth_token",
    "table": "tb_file",
    "table_name": "build_process",
    "table_sn": "build_id",
    "file_type": "RTISN"
}
```

**RTIDP 요청 (디포지션):**
```json
{
    "type": "get",
    "token": "auth_token",
    "table": "tb_file",
    "table_name": "build_process",
    "table_sn": "build_id",
    "file_type": "RTIDP"
}
```

**파일 다운로드 요청:**
```json
{
    "type": "view",
    "token": "auth_token",
    "file_sn": "12345"
}
```

## 주요 기능

### LogFetcher
- 로그 데이터 조회
- 파일 SN 추출
- 파일 바이트 데이터 다운로드
- 에러 처리

### VisionFetcher
- RTISN (스캐닝) 데이터 조회
- RTIDP (디포지션) 데이터 조회
- 회사별 파일명 패턴 검색
- 레이어별 이미지 추출
- 자동 폴백 처리 (jpg → png)

## 에러 처리

모든 Fetcher는 다음 상황을 자동으로 처리합니다:

- 네트워크 에러: `None` 반환
- 데이터 없음: `None` 반환
- JSON 파싱 실패: `None` 반환
- 파일 SN 없음: `None` 반환

## 참고사항

- 서버 주소: `http://114.108.139.100:8500`
- 모든 작업은 비동기(`async/await`)로 구현되어 있습니다
- 테스트는 Mock을 사용하여 실제 서버에 연결하지 않습니다
- 레이어가 0이면 자동으로 1로 변환됩니다
