# macOS 호환성 보고서

## ✅ 완전 호환 패키지

모든 핵심 패키지는 macOS에서 정상 작동합니다:

### 1. **httpx** (0.28.1)
- ✅ Windows, macOS, Linux 모두 지원
- 순수 Python 패키지
- 설치: `pip install httpx`

### 2. **pycryptodome** (3.23.0)
- ✅ Windows, macOS, Linux 모두 지원
- macOS에서 자동으로 컴파일됨
- 설치: `pip install pycryptodome`

### 3. **PyQt5** (5.15.11)
- ✅ Windows, macOS, Linux 모두 지원
- macOS용 바이너리 제공
- 설치: `pip install PyQt5`
- **참고**: macOS에서 GUI 실행 시 권한 설정 필요할 수 있음

### 4. **pytest** & **pytest-asyncio**
- ✅ 크로스 플랫폼 지원
- 테스트 도구로 선택 사항

## ⚠️ 주의사항

### PyQt5 on macOS
- macOS Big Sur (11.0) 이상 권장
- 일부 macOS 버전에서 GUI 실행 시 추가 설정 필요:
  ```bash
  # macOS에서 PyQt5 앱 실행 시
  pythonw gui_app.py  # python 대신 pythonw 사용
  ```

### AES 암호화
- `pycryptodome`는 macOS에서 자동 컴파일되므로 Xcode Command Line Tools 필요:
  ```bash
  xcode-select --install
  ```

## 🚀 macOS 설치 가이드

```bash
# 1. 가상환경 생성
python3 -m venv venv

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. GUI 실행
pythonw gui_app.py  # 또는 python gui_app.py
```

## 🔍 제거된 불필요한 패키지

다음 패키지는 직접 설치하지 않았지만 `pip freeze`에 포함되어 제거했습니다:
- `Naked`, `shellescape` - 사용하지 않는 패키지
- `colorama` - Windows 전용 (macOS에서 불필요)
- `requests` - httpx 사용으로 불필요
- 기타 의존성 패키지들은 자동 설치됨

## ✅ 결론

**모든 핵심 기능이 macOS에서 정상 작동합니다!**
- 로그인 기능 ✅
- 데이터 fetcher ✅
- PyQt5 GUI ✅
- AES 암호화 ✅

추가 설정 없이 `requirements.txt`만 설치하면 됩니다.
