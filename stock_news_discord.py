import os
import requests
from deep_translator import GoogleTranslator

# -------------------- 설정값 --------------------
# GitHub Actions에서 환경변수(Secrets)로 넣을 값
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TOP_N = 5

# -------------------- 뉴스 수집 --------------------

def fetch_korean_stock_news(top_n=5):
    if not NEWS_API_KEY:
        raise RuntimeError("환경변수 NEWS_API_KEY 가 설정되어 있지 않습니다.")

    url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": NEWS_API_KEY,
        "q": "주식 OR 증시 OR 코스피 OR 코스닥 OR 코스피지수 OR 코스닥지수",
        "language": "ko",
        "sortBy": "publishedAt",
        "pageSize": top_n,
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    print("NewsAPI 응답 요약:", data.get("status"), data.get("totalResults"))

    articles = data.get("articles", [])
    news_list = []

    for a in articles:
        title = (a.get("title") or "").strip()
        desc = a.get("description") or ""
        url = a.get("url") or ""

        if not title:
            continue

        news_list.append(
            {
                "title": title,
                "description": desc,
                "url": url,
            }
        )

    return news_list

# -------------------- 번역 --------------------

def translate_text(text: str, target_lang: str) -> str:
    if not text:
        return ""
    try:
        return GoogleTranslator(source="ko", target=target_lang).translate(text)
    except Exception as e:
        print(f"번역 오류: {e}")
        return text

def translate_news_list(news_list, dest_lang):
    translated = []
    for item in news_list:
        ko_title = item["title"]
        ko_desc = item["description"]

        t_title = translate_text(ko_title, dest_lang)
        t_desc = translate_text(ko_desc, dest_lang) if ko_desc else ""

        translated.append(
            {
                "title": t_title,
                "description": t_desc,
                "url": item["url"],
            }
        )
    return translated

# -------------------- 메시지 만들기 --------------------

def build_message(ko_news, en_news, zh_news) -> str:
    lines = []
    lines.append("**오늘의 한국 주식 TOP 5 뉴스**\n")

    # 한국어
    lines.append("=== 🇰🇷 한국어 ===")
    for i, n in enumerate(ko_news, start=1):
        lines.append(f"{i}. {n['title']}")
        if n["description"]:
            lines.append(f"   - 요약: {n['description'].replace('\n', ' ').strip()}")
        if n["url"]:
            lines.append(f"   링크: {n['url']}")
        lines.append("")

    # 영어
    lines.append("=== 🇺🇸 English ===")
    for i, n in enumerate(en_news, start=1):
        lines.append(f"{i}. {n['title']}")
        if n["description"]:
            lines.append(f"   - Summary: {n['description'].replace('\n', ' ').strip()}")
        lines.append("")

    # 중국어
    lines.append("=== 🇨🇳 中文(简体) ===")
    for i, n in enumerate(zh_news, start=1):
        lines.append(f"{i}. {n['title']}")
        if n["description"]:
            lines.append(f"   - 摘要: {n['description'].replace('\n', ' ').strip()}")
        lines.append("")

    return "\n".join(lines)

# -------------------- 디스코드 전송 --------------------

def send_to_discord(message: str):
    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError("환경변수 DISCORD_WEBHOOK_URL 이 설정되어 있지 않습니다.")

    max_len = 1900
    lines = message.split("\n")
    buffer = ""

    for line in lines:
        if len(buffer) + len(line) + 1 > max_len:
            _post_discord(buffer)
            buffer = line + "\n"
        else:
            buffer += line + "\n"

    if buffer.strip():
        _post_discord(buffer)

def _post_discord(content: str):
    resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
    if resp.status_code not in (200, 204):
        print("디스코드 전송 실패:", resp.status_code, resp.text)
    else:
        print("디스코드 전송 성공")

# -------------------- main --------------------

def main():
    print("한국 주식 관련 Top 뉴스 수집 및 디스코드 전송 시작...")

    ko_news = fetch_korean_stock_news(top_n=TOP_N)
    if not ko_news:
        print("뉴스가 없습니다.")
        return

    en_news = translate_news_list(ko_news, "en")
    zh_news = translate_news_list(ko_news, "chinese (simplified)")

    message = build_message(ko_news, en_news, zh_news)
    send_to_discord(message)

    print("작업 완료")

if __name__ == "__main__":
    main()
