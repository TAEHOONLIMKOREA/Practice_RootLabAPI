import asyncio
from Modules import DataFetcher


async def test_api(token: str, build_id: str, layer: int = 1, company: str = "corp01"):
    """API 통합 테스트"""
    fetcher = DataFetcher(token, build_id, company)

    print("\n" + "="*50)
    print("API 테스트 시작")
    print("="*50)

    # 로그 데이터 테스트
    print("\n=== 로그 데이터 ===")
    log_data = await fetcher.fetch_log()
    if log_data:
        print(f"✓ 수신: {len(log_data)} bytes")
        with open("log_data.csv", "wb") as f:
            f.write(log_data)
        print("✓ 저장: log_data.csv")
        log_success = True
    else:
        print("✗ 조회 실패")
        log_success = False

    # 비전 데이터 테스트
    print("\n=== 비전 데이터 ===")
    scanning, deposition = await fetcher.fetch_vision(layer)
    vision_success = False

    if scanning:
        print(f"✓ 스캐닝 수신: {len(scanning)} bytes")
        with open("scanning_image.jpg", "wb") as f:
            f.write(scanning)
        print("✓ 저장: scanning_image.jpg")
        vision_success = True
    else:
        print("✗ 스캐닝 조회 실패")

    if deposition:
        print(f"✓ 디포지션 수신: {len(deposition)} bytes")
        with open("deposition_image.jpg", "wb") as f:
            f.write(deposition)
        print("✓ 저장: deposition_image.jpg")
        vision_success = True
    else:
        print("✗ 디포지션 조회 실패")

    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과")
    print("="*50)
    print(f"로그 데이터: {'성공' if log_success else '실패'}")
    print(f"비전 데이터: {'성공' if vision_success else '실패'}")


async def main():
    """메인 함수"""
    # 로그인
    print("=== 로그인 ===")
    user_id = "corp03"
    user_pw = "*corp12#"

    token = await DataFetcher.login(user_id, user_pw)
    if not token:
        print("로그인 실패")
        return

    print(f"토큰: {token[:50]}...\n")

    # 테스트 설정
    build_id = 308
    layer = 1
    company = "corp03"

    await test_api(token, build_id, layer, company)


if __name__ == "__main__":
    asyncio.run(main())
