import csv
import html
import json
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests
from openai import OpenAI


DEFAULT_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1yC36MDsTswSkwLbZe5OwwGdjw2ViVcN0vpC1AzBXNY0/export?format=csv&gid=0"
)
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
SHEET_LINK = "https://docs.google.com/spreadsheets/d/1yC36MDsTswSkwLbZe5OwwGdjw2ViVcN0vpC1AzBXNY0/edit?hl=ko&gid=0#gid=0"


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def load_watchlist() -> list[str]:
    url = os.getenv("GOOGLE_SHEET_CSV_URL", DEFAULT_SHEET_CSV_URL).strip()
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    stocks: list[str] = []
    reader = csv.reader(StringIO(response.text))
    for row in reader:
        if not row:
            continue
        value = row[0].strip()
        if not value or value.startswith("#"):
            continue
        if value.lower() in {"stock", "stocks", "ticker", "symbol", "종목", "종목명"}:
            continue
        stocks.append(value)
    return stocks


def fetch_news(stocks: list[str]) -> list[dict]:
    articles: list[dict] = []
    seen: set[str] = set()
    for stock in stocks:
        query = quote_plus(f"{stock} stock news OR earnings OR market")
        url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            link = getattr(entry, "link", "")
            title = getattr(entry, "title", "").strip()
            if not title or link in seen:
                continue
            seen.add(link)
            articles.append(
                {
                    "stock": stock,
                    "title": title,
                    "link": link,
                    "published": getattr(entry, "published", ""),
                    "source": getattr(getattr(entry, "source", None), "title", ""),
                }
            )
    return articles


def summarize(stocks: list[str], articles: list[dict]) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    client = OpenAI(api_key=env("OPENAI_API_KEY"))
    today = datetime.now().strftime("%Y-%m-%d")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You write concise Korean morning briefings for an individual investor. "
                    "Use only the provided news list. Do not invent facts. "
                    "Mention when news coverage is thin."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "date": today,
                        "watchlist": stocks,
                        "news": articles,
                        "required_format": [
                            "headline",
                            "market_summary",
                            "stock_sections",
                            "positive_points",
                            "risk_points",
                            "watch_today",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return response.output_text.strip()


def public_briefing_url() -> str:
    configured = os.getenv("PUBLIC_BRIEFING_URL", "").strip()
    if configured:
        return configured
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if "/" not in repository:
        return SHEET_LINK
    owner, repo = repository.split("/", 1)
    return f"https://{owner}.github.io/{repo}/"


def render_briefing_page(stocks: list[str], articles: list[dict], briefing: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    article_rows = "\n".join(
        f"""
        <li>
          <span class="ticker">{html.escape(article["stock"])}</span>
          <a href="{html.escape(article["link"])}" target="_blank" rel="noreferrer">{html.escape(article["title"])}</a>
          <small>{html.escape(article.get("published", ""))}</small>
        </li>
        """
        for article in articles[:18]
    )
    stock_tags = "".join(f"<span>{html.escape(stock)}</span>" for stock in stocks)
    briefing_html = "<br>".join(html.escape(briefing).splitlines())
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RedStock Briefing - {today}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #171717;
      --muted: #666f7a;
      --line: #e4e7ec;
      --paper: #ffffff;
      --bg: #f5f7fb;
      --red: #d92035;
      --green: #0f8b5f;
      --blue: #1d5fd1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.58;
    }}
    header {{
      background: var(--paper);
      border-bottom: 1px solid var(--line);
    }}
    .wrap {{
      width: min(920px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .top {{
      padding: 34px 0 24px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--red);
      font-weight: 800;
      letter-spacing: 0;
    }}
    .mark {{
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      color: white;
      background: var(--red);
      font-size: 13px;
    }}
    h1 {{
      margin: 18px 0 8px;
      font-size: clamp(30px, 5vw, 48px);
      line-height: 1.08;
      letter-spacing: 0;
    }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
    }}
    main {{
      padding: 22px 0 44px;
    }}
    section {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      margin-top: 16px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }}
    .tags span {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
      color: var(--muted);
      background: #fbfcff;
    }}
    .briefing {{
      font-size: 16px;
      white-space: normal;
    }}
    ul {{
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    li {{
      padding: 13px 0;
      border-top: 1px solid var(--line);
    }}
    li:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    a {{
      color: var(--blue);
      text-decoration: none;
      font-weight: 650;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .ticker {{
      display: inline-block;
      min-width: 86px;
      margin-right: 8px;
      color: var(--green);
      font-weight: 800;
    }}
    small {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
    }}
    footer {{
      padding: 18px 0 34px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 640px) {{
      .wrap {{ width: min(100% - 24px, 920px); }}
      section {{ padding: 18px; }}
      .ticker {{ display: block; margin-bottom: 4px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <div class="brand"><span class="mark">RS</span>RedStock</div>
      <h1>오늘의 주식 뉴스 브리핑</h1>
      <div class="meta">{generated_at} 생성 · Google Sheets 관심종목 기준</div>
      <div class="tags">{stock_tags}</div>
    </div>
  </header>
  <main class="wrap">
    <section>
      <h2>요약</h2>
      <div class="briefing">{briefing_html}</div>
    </section>
    <section>
      <h2>확인한 뉴스</h2>
      <ul>{article_rows}</ul>
    </section>
  </main>
  <footer class="wrap">투자 판단은 본인의 책임이며, 이 페이지는 뉴스 요약 참고용입니다.</footer>
</body>
</html>
"""


def write_briefing_page(stocks: list[str], articles: list[dict], briefing: str) -> None:
    docs = Path("docs")
    briefings = docs / "briefings"
    briefings.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    page = render_briefing_page(stocks, articles, briefing)
    (docs / "index.html").write_text(page, encoding="utf-8")
    (briefings / f"{today}.html").write_text(page, encoding="utf-8")


def refresh_access_token() -> str:
    body = {
        "grant_type": "refresh_token",
        "client_id": env("KAKAO_REST_API_KEY"),
        "refresh_token": env("KAKAO_REFRESH_TOKEN"),
    }
    response = requests.post(KAKAO_TOKEN_URL, data=body, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data["access_token"]


def split_for_kakao(text: str, limit: int = 190) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = f"{current}\n{line}".strip() if current else line.strip()
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current = line.strip()
    if current:
        chunks.append(current)
    return chunks or ["RedStock: 보낼 브리핑 내용이 없습니다."]


def send_kakao_message(text: str, link_url: str = SHEET_LINK, button_title: str = "종목 시트") -> None:
    access_token = refresh_access_token()
    send_mode = os.getenv("KAKAO_SEND_MODE", "split").strip().lower()
    chunks = [text[:200]] if send_mode == "single" else split_for_kakao(text)
    for index, chunk in enumerate(chunks):
        prefix = f"({index + 1}) " if index > 0 else ""
        template_object = {
            "object_type": "text",
            "text": f"{prefix}{chunk}"[:200],
            "link": {
                "web_url": link_url,
                "mobile_web_url": link_url,
            },
            "buttons": [
                {
                    "title": button_title,
                    "link": {
                        "web_url": link_url,
                        "mobile_web_url": link_url,
                    },
                }
            ],
        }
        response = requests.post(
            KAKAO_MEMO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            data={"template_object": json.dumps(template_object, ensure_ascii=False)},
            timeout=20,
        )
        response.raise_for_status()


def main() -> int:
    stocks = load_watchlist()
    if not stocks:
        send_kakao_message("RedStock: Google Sheets A열에 브리핑 받을 종목을 추가해주세요.")
        return 0

    articles = fetch_news(stocks)
    if not articles:
        send_kakao_message("RedStock: 오늘 종목 관련 뉴스를 찾지 못했습니다. 시트의 종목명을 확인해주세요.")
        return 0

    briefing = summarize(stocks, articles)
    write_briefing_page(stocks, articles, briefing)
    url = public_briefing_url()
    stock_text = ", ".join(stocks[:4])
    send_kakao_message(
        f"RedStock 오늘 브리핑 도착. 관심종목: {stock_text}. 전체 내용: {url}",
        link_url=url,
        button_title="브리핑 보기",
    )
    print("Briefing sent.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise
