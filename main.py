import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = "5170675475"
STATE_FILE = "prices.json"

HOTELS = {
    "탑 클라우드호텔": "https://nol.yanolja.com/stay/domestic/28012",
    "맥모텔": "https://nol.yanolja.com/stay/domestic/24135",
    "호텔세르보": "https://nol.yanolja.com/stay/domestic/3010407",
    "도안 자우리": "https://nol.yanolja.com/stay/domestic/3000349",
    "스파타워": "https://nol.yanolja.com/stay/domestic/23960",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; SM-S918N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(prices):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)


def send_telegram(message):
    if not TELEGRAM_TOKEN:
        print("텔레그램 전송 실패: TELEGRAM_TOKEN이 없습니다.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
            },
            timeout=20,
        )

        print("텔레그램 응답:", response.status_code)

        if response.status_code != 200:
            print("텔레그램 오류:", response.text[:500])
            return False

        return True

    except requests.RequestException as e:
        print("텔레그램 요청 오류:", e)
        return False


def extract_stay_prices(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = " ".join(soup.stripped_strings)
    text = re.sub(r"\s+", " ", text)

    prices = []

    # 숙박 항목 뒤에 표시되는 가격 검색
    stay_pattern = re.compile(
        r"숙박(?:(?!대실|숙박).){0,700}?"
        r"([0-9]{1,3}(?:,[0-9]{3})+)\s*원",
        re.DOTALL,
    )

    for value in stay_pattern.findall(text):
        price = int(value.replace(",", ""))

        if 10000 <= price <= 1000000:
            prices.append(price)

    # 회원가 형식 보완
    member_pattern = re.compile(
        r"회원가\s*"
        r"([0-9]{1,3}(?:,[0-9]{3})+)\s*원"
    )

    for value in member_pattern.findall(text):
        price = int(value.replace(",", ""))

        if 10000 <= price <= 1000000:
            prices.append(price)

    return sorted(set(prices))


def get_price(name, url):
    print(f"\n{name} 확인 중...")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=25,
        )

        print("야놀자 응답:", response.status_code)

        response.raise_for_status()

    except requests.RequestException as e:
        print(f"{name} : 접속 오류 - {e}")
        return None

    prices = extract_stay_prices(response.text)

    if not prices:
        print(f"{name} : 숙박 가격 확인 실패")
        return None

    lowest = min(prices)

    print("숙박 가격 후보:", prices)
    print(f"{name} 최저 숙박가: {lowest:,}원")

    return lowest


def format_price(price):
    if price is None:
        return "확인 실패"

    return f"{price:,}원"


def main():
    now = datetime.now(ZoneInfo("Asia/Seoul"))

    print(
        f"[{now:%Y-%m-%d %H:%M:%S}] "
        "야놀자 가격 확인 시작"
    )

    old_prices = load_state()
    current_prices = {}

    for name, url in HOTELS.items():
        price = get_price(name, url)

        if price is not None:
            current_prices[name] = price

    # 가격 확인 실패 시 기존 정상 가격은 유지
    new_state = dict(old_prices)
    new_state.update(current_prices)

    save_state(new_state)

    manual_run = (
        os.environ.get("GITHUB_EVENT_NAME")
        == "workflow_dispatch"
    )

    changes = []

    for name, price in current_prices.items():
        old = old_prices.get(name)

        if old is None:
            changes.append(
                f"• {name}: {price:,}원 (첫 확인)"
            )

        elif old != price:
            diff = price - old

            if diff > 0:
                direction = "▲"
            else:
                direction = "▼"

            changes.append(
                f"• {name}: "
                f"{old:,}원 → {price:,}원 "
                f"({direction}{abs(diff):,}원)"
            )

    failed = [
        name
        for name in HOTELS
        if name not in current_prices
    ]

    # 수동 실행하면 무조건 현재 가격을 텔레그램으로 전송
    if manual_run:
        lines = [
            "🏨 야놀자 숙박 가격 확인",
            f"{now:%m/%d %H:%M}",
            "",
        ]

        for name in HOTELS:
            lines.append(
                f"• {name}: "
                f"{format_price(current_prices.get(name))}"
            )

        if failed:
            lines += [
                "",
                "⚠️ 확인 실패: "
                + ", ".join(failed),
            ]

        message = "\n".join(lines)

        send_telegram(message)

    # 자동 실행은 가격 변동이 있을 때만 알림
    elif changes:
        lines = [
            "🔔 야놀자 숙박 가격 변동",
            f"{now:%m/%d %H:%M}",
            "",
            *changes,
        ]

        if failed:
            lines += [
                "",
                "⚠️ 확인 실패: "
                + ", ".join(failed),
            ]

        send_telegram("\n".join(lines))

    else:
        print(
            "가격 변동 없음 - "
            "텔레그램 전송 안 함"
        )

    print("\n가격 확인 완료")
if __name__ == "__main__":
    main()

