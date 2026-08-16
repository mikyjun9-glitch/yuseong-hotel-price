import re
import requests

HOTELS = {
    "탑 클라우드호텔": "https://nol.yanolja.com/stay/domestic/28012",
    "맥모텔": "https://nol.yanolja.com/stay/domestic/24135",
    "호텔세르보": "https://nol.yanolja.com/stay/domestic/3010407",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; SM-S918N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


def get_prices(name, url):
    print(f"\n{name} 확인 중...")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        print("야놀자 응답:", response.status_code)

        if response.status_code != 200:
            print(f"{name} : 접속 실패")
            return

        html = response.text

        # 야놀자 페이지에 표시되는
        # "판매가 70,000원" 형식의 가격 검색
        patterns = [
            r'판매가\s*([0-9,]+)\s*원',
            r'판매가[^0-9]{0,30}([0-9,]+)',
            r'"price"\s*:\s*"?([0-9]+)"?',
            r'"salePrice"\s*:\s*"?([0-9]+)"?',
            r'"sellingPrice"\s*:\s*"?([0-9]+)"?',
        ]

        prices = []

        for pattern in patterns:
            matches = re.findall(pattern, html)

            for value in matches:
                try:
                    price = int(value.replace(",", ""))

                    # 숙박 가격으로 볼 수 있는 범위만 사용
                    if 10000 <= price <= 1000000:
                        prices.append(price)

                except ValueError:
                    pass

        prices = sorted(set(prices))

        if not prices:
            print("가격 후보 없음")
            print(f"{name} : 가격 확인 실패")
            return

        print("가격 후보:", prices)
        print(f"{name} 최저 판매가: {min(prices):,}원")
        except requests.RequestException as e:
        print(f"{name} : 요청 오류 - {e}")

def main():

    print("===== 야놀자 가격 추출 테스트 =====")

    for name, url in HOTELS.items():
        get_prices(name, url)

    print("\n===== 확인 완료 =====")


if __name__ == "__main__":
    main()
