import os
import re
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# ==========================================
# 설정
# ==========================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = "5170675475"
STATE_FILE = "prices.json"

HOTELS = {
    "탑 클라우드호텔": "https://nol.yanolja.com/stay/domestic/28012",
    "맥모텔": "https://nol.yanolja.com/stay/domestic/24135",
    "호텔세르보": "https://nol.yanolja.com/stay/domestic/3010407",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://nol.yanolja.com/",
}


# ==========================================
# 텔레그램
# ==========================================

def send_telegram(message):
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN 없음")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=20
        )

        print("텔레그램 전송:", response.status_code)

        return response.status_code == 200

    except Exception as e:
        print("텔레그램 오류:", e)
        return False


# ==========================================
# 이전 가격 불러오기 / 저장
# ==========================================

def load_prices():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print("기존 가격 읽기 오류:", e)
        return {}


def save_prices(prices):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            prices,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True
        )


# ==========================================
# 야놀자 가격 가져오기
# ==========================================

def get_price(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=25
        )

        print("야놀자 응답:", response.status_code)

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        text = soup.get_text("\n")

        # 객실 선택 영역만 사용
        if "객실 선택" in text:
            text = text.split("객실 선택", 1)[1]

        # 위치/교통 뒤의 후기, 주소 등은 제외
        if "위치/교통" in text:
            text = text.split("위치/교통", 1)[0]

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        prices = []

        for i, line in enumerate(lines):

            # 50,000 원 / 50000원 형태
            matches = re.findall(
                r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{5,7})\s*원(?:~)?",
                line
            )

            if not matches:
                continue

            # 바로 앞 객실이 예약마감이면 제외
            context = " ".join(lines[max(0, i - 8):i + 1])

            if "예약마감" in context:
                continue

            for raw in matches:
                try:
                    price = int(raw.replace(",", ""))

                    if 10000 <= price <= 1000000:
                        prices.append(price)

                except ValueError:
                    pass

        if not prices:
            print("가격 후보 없음")
            return None

        price = min(prices)

        print("가격 후보:", sorted(set(prices)))
        print("최저 숙박가격:", price)

        return price

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
        + "] 야놀자 가격 확인 시작"
    )

    old_prices = load_prices()
    new_prices = dict(old_prices)

    successful = {}
    failed = []

    for hotel, url in HOTELS.items():
        print()
        print(hotel, "확인 중...")

        price = get_price(url)

        if price is None:
            print(hotel, ": 가격 확인 실패")
            failed.append(hotel)
            continue

        successful[hotel] = price
        new_prices[hotel] = price

        print(hotel, ":", f"{price:,}원")

    # --------------------------------------
    # 첫 실행 = 기준가격 저장
    # --------------------------------------

    if not old_prices and successful:
        lines = [
            "🏨 야놀자 기준가격 저장",
            ""
        ]

        for hotel, price in successful.items():
            lines.append(
                f"{hotel}: {price:,}원"
            )

        lines.append("")
        lines.append(
            "확인시간: "
            + now.strftime("%Y-%m-%d %H:%M")
        )

        send_telegram("\n".join(lines))

    # --------------------------------------
    # 이후 실행 = 가격 변경 시에만 알림
    # --------------------------------------

    elif old_prices:
        changes = []

        for hotel, price in successful.items():
            old_price = old_prices.get(hotel)

            if old_price is None:
                changes.append(
                    f"🆕 {hotel}\n"
                    f"현재 가격: {price:,}원"
                )

            elif price != old_price:

                if price < old_price:
                    symbol = "🔻 가격 하락"
                else:
                    symbol = "🔺 가격 상승"

                changes.append(
                    f"{symbol}\n"
                    f"숙소: {hotel}\n"
                    f"이전 가격: {old_price:,}원\n"
                    f"현재 가격: {price:,}원\n"
                    f"차이: {price - old_price:+,}원"
                )

        if changes:
            message = (
                "🚨 야놀자 숙박가격 변경\n\n"
                + "\n\n".join(changes)
                + "\n\n확인시간: "
                + now.strftime("%Y-%m-%d %H:%M")
            )

            send_telegram(message)

        else:
            print("가격 변동 없음 - 텔레그램 알림 없음")

    save_prices(new_prices)

    if failed:
        print("가격 확인 실패 숙소:", ", ".join(failed))

    print("가격 확인 완료")


if __name__ == "__main__":
    main()
