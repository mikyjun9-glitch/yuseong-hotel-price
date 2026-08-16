import os
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# 텔레그램 설정
# ==========================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = "5170675475"

# ==========================================
# 야놀자 숙소 3개
# ==========================================

HOTELS = {
    "탑 클라우드호텔": "https://nol.yanolja.com/stay/domestic/28012",
    "맥모텔": "https://nol.yanolja.com/stay/domestic/24135",
    "호텔세르보": "https://nol.yanolja.com/stay/domestic/3010407",
}


# ==========================================
# 텔레그램 보내기
# ==========================================

def send_telegram(message):
    if not TELEGRAM_TOKEN:
        print("텔레그램 토큰이 없습니다.")
        return

    try:
        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_TOKEN}/sendMessage"
        )

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=15
        )

        print("텔레그램 전송:", response.status_code)

    except Exception as e:
        print("텔레그램 전송 오류:", e)


# ==========================================
# 야놀자 가격 가져오기
# ==========================================

def get_price(url):

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent":
                "Mozilla/5.0 (Linux; Android 10) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Mobile Safari/537.36"
            },
            timeout=20
        )

        response.raise_for_status()

        text = response.text

        # 페이지 안의 가격 후보 검색
        patterns = [
            r'"price"\s*:\s*(\d{4,7})',
            r'"salePrice"\s*:\s*(\d{4,7})',
            r'"discountPrice"\s*:\s*(\d{4,7})',
            r'"amount"\s*:\s*(\d{4,7})',
        ]

        prices = []

        for pattern in patterns:
            found = re.findall(pattern, text)

            for value in found:
                try:
                    price = int(value)

                    if 10000 <= price <= 1000000:
                        prices.append(price)

                except:
                    pass

        if not prices:
            return None

        return min(prices)

    except Exception as e:
        print("가격 확인 오류:", e)
        return None


# ==========================================
# 메인
# ==========================================

def main():

    now = datetime.now(ZoneInfo("Asia/Seoul"))

    print(
        "[" + now.strftime("%Y-%m-%d %H:%M:%S")
        + "] 가격 확인 시작"
    )

    results = []

    for hotel, url in HOTELS.items():

        print(hotel + " 확인 중...")

        price = get_price(url)

        if price is None:

            print(hotel + ": 가격 확인 실패")

            results.append(
                hotel + ": 가격 확인 실패"
            )

        else:

            print(
                hotel + ": "
                + f"{price:,}원"
            )

            results.append(
                hotel + ": "
                + f"{price:,}원"
            )

    # 수동 테스트할 때 결과 확인용
    message = (
        "🏨 야놀자 가격 확인\n\n"
        + "\n".join(results)
        + "\n\n확인시간: "
        + now.strftime("%Y-%m-%d %H:%M")
    )

    send_telegram(message)

    print("가격 확인 완료")


if __name__ == "__main__":
    main()
