import os
import time
import requests
from datetime import datetime
import re


# ==========================================
# 텔레그램 설정
# ==========================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = "5170675475"


# ==========================================
# 야놀자 숙소
# ==========================================

HOTELS = {
    "탑 클라우드호텔": "https://nol.yanolja.com/stay/domestic/28012",
    "맥모텔": "https://nol.yanolja.com/stay/domestic/24135",
    "호텔세르보": "https://nol.yanolja.com/stay/domestic/3010407"
}


# ==========================================
# 텔레그램 알림
# ==========================================

def send_telegram(message):

    if not TELEGRAM_TOKEN:
        print("텔레그램 봇 토큰이 설정되지 않았습니다.")
        return

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_TOKEN}/sendMessage"
    )

    try:
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
# 야놀자 가격 확인
# ==========================================

def get_price(url):

    if not url:
        return None

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                "Mozilla/5.0 (Linux; Android 10) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0.0.0 "
                "Mobile Safari/537.36",
                "Accept-Language":
                "ko-KR,ko;q=0.9"
            },
            timeout=20
        )

        if response.status_code != 200:
            print(
                "페이지 접속 실패:",
                response.status_code
            )
            return None

        text = response.text

        # ==================================
        # 원화 가격 찾기
        # ==================================

        prices = re.findall(
            r'([0-9][0-9,]*)\s*원',
            text
        )

        numbers = []

        for value in prices:

            value = value.replace(",", "")

            try:

                number = int(value)

                # 1만원 ~ 100만원
                if 10000 <= number <= 1000000:
                    numbers.append(number)

            except ValueError:
                pass

        if numbers:
            return min(numbers)

        print("가격을 찾지 못했습니다.")

    except Exception as e:

        print("가격 확인 오류:", e)

    return None


# ==========================================
# 메인 감시
# ==========================================

last_prices = {}


while True:

    try:

        now = datetime.now()

        current_time = (
            now.hour * 60
            + now.minute
        )

        # ==================================
        # 오전 10:00 ~ 오후 11:50 감시
        # ==================================

        start = 10 * 60
        end = 23 * 60 + 50

        if start <= current_time <= end:

            print(
                "\n["
                + now.strftime("%Y-%m-%d %H:%M:%S")
                + "] 가격 확인 시작"
            )

            # ==================================
            # 야놀자 3개 숙소 확인
            # ==================================

            for hotel, url in HOTELS.items():

                print(
                    hotel + " 확인 중..."
                )

                price = get_price(url)

                # 가격 확인 실패
                if price is None:

                    print(
                        hotel
                        + ": 가격 확인 실패"
                    )

                    continue

                print(
                    hotel
                    + ": "
                    + f"{price:,}원"
                )

                old_price = last_prices.get(hotel)

                # ==================================
                # 처음 확인한 가격은 저장만
                # ==================================

                if old_price is None:

                    last_prices[hotel] = price

                    print(
                        hotel
                        + ": "
                        + f"{price:,}원 저장"
                    )

                    continue

                # ==================================
                # 가격이 변경된 경우
                # ==================================

                if price != old_price:

                    if price < old_price:
                        change = "🔻 가격 하락"
                    else:
                        change = "🔺 가격 상승"

                    message = (
                        "🚨 호텔 가격 변경\n\n"
                        + change
                        + "\n"
                        + "숙소: "
                        + hotel
                        + "\n"
                        + "이전 가격: "
                        + f"{old_price:,}원"
                        + "\n"
                        + "현재 가격: "
                        + f"{price:,}원"
                        + "\n"
                        + "확인시간: "
                        + now.strftime("%H:%M")
                    )

                    # 텔레그램 전송
                    send_telegram(message)

                    # 새로운 가격 저장
                    last_prices[hotel] = price

                    print(message)

                else:

                    print(
                        hotel
                        + ": 가격 변동 없음"
                    )

        else:

            print(
                "["
                + now.strftime("%H:%M")
                + "] 감시시간 외"
            )

        # ==================================
        # 5분마다 확인
        # ==================================

        time.sleep(300)

    except Exception as e:

        print(
            "메인 감시 오류:",
            e
        )

        # 오류가 발생해도 프로그램 종료하지 않음
        time.sleep(60)
