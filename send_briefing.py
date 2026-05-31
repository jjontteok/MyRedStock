import csv
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import requests


DEFAULT_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1yC36MDsTswSkwLbZe5OwwGdjw2ViVcN0vpC1AzBXNY0/export?format=csv&gid=0"
)
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
SHEET_LINK = "https://docs.google.com/spreadsheets/d/1yC36MDsTswSkwLbZe5OwwGdjw2ViVcN0vpC1AzBXNY0/edit?hl=ko&gid=0#gid=0"


def env(name: str, default: Optional[str] = None) -> str:
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


def load_remote_settings() -> dict:
    url = os.getenv("WATCHLIST_API_URL", "").strip()
    if not url:
        return {}
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not data.get("ok"):
        return {}
    return data


def kst_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def selected_time(settings: dict) -> str:
    value = str(settings.get("briefingTime") or "07:30").strip()
    if re.match(r"^\d{2}:\d{2}$", value):
        hour, minute = [int(part) for part in value.split(":")]
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return value
    return "07:30"


def sent_marker_path(settings: dict, now: Optional[datetime] = None) -> Path:
    current = now or kst_now()
    send_time = selected_time(settings).replace(":", "")
    return Path("docs") / ".sent" / f"{current.strftime('%Y-%m-%d')}-{send_time}.txt"


def should_send_now(settings: dict) -> bool:
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return True
    now = kst_now()
    hour, minute = [int(part) for part in selected_time(settings).split(":")]
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delta_minutes = (now - target).total_seconds() / 60
    if not 0 <= delta_minutes < 30:
        print(f"Not send time yet. now={now.strftime('%H:%M')} target={hour:02d}:{minute:02d}")
        return False
    sent_marker = sent_marker_path(settings, now)
    if sent_marker.exists():
        print(f"Today's briefing was already sent: {sent_marker}")
        return False
    return True


def fetch_news(stocks: list[str]) -> list[dict]:
    import feedparser

    fetched_at = kst_now().strftime("%H:%M")
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
                    "published_display": format_published_time(entry),
                    "fetched_at": fetched_at,
                    "source": getattr(getattr(entry, "source", None), "title", ""),
                }
            )
    return articles


def format_published_time(entry: object) -> str:
    published_parsed = getattr(entry, "published_parsed", None)
    if published_parsed:
        published_utc = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        published_kst = published_utc.astimezone(timezone(timedelta(hours=9)))
        return published_kst.strftime("%m/%d %H:%M")
    published = str(getattr(entry, "published", "") or "").strip()
    return published


def summarize(stocks: list[str], articles: list[dict]) -> str:
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY", "").strip():
        grouped: dict[str, list[dict]] = {stock: [] for stock in stocks}
        for article in articles:
            grouped.setdefault(article["stock"], []).append(article)
        lines = ["RedStock 오늘 브리핑"]
        for stock in stocks:
            stock_articles = grouped.get(stock, [])[:2]
            if not stock_articles:
                lines.append(f"{stock}: 확인된 주요 뉴스가 적습니다.")
                continue
            titles = " / ".join(article["title"] for article in stock_articles)
            lines.append(f"{stock}: {titles}")
        lines.append("체크: AI/HBM, 실적, 환율, 수급 변화를 함께 확인하세요.")
        return "\n".join(lines)

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    client = OpenAI(api_key=env("OPENAI_API_KEY"))
    today = kst_now().strftime("%Y-%m-%d")

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


def dated_briefing_url() -> str:
    base_url = public_briefing_url()
    if not base_url.startswith("http"):
        return base_url
    now = kst_now()
    today = now.strftime("%Y-%m-%d")
    version = now.strftime("%Y%m%d%H%M")
    return f"{base_url.rstrip('/')}/briefings/{today}.html?v={version}"


def render_briefing_page(stocks: list[str], articles: list[dict], briefing: str) -> str:
    now = kst_now()
    today = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M")
    asset_version = now.strftime("%Y%m%d%H%M%S")
    article_rows = "\n".join(
        f"""
        <li>
          <span class="ticker">{html.escape(article["stock"])}</span>
          <span class="news-main">
            <a href="{html.escape(article["link"])}" target="_blank" rel="noreferrer">{html.escape(article["title"])}</a>
            <span class="news-time">{html.escape(article.get("published_display") or article.get("published", ""))} 발췌 · {html.escape(article.get("fetched_at", ""))} 확인</span>
          </span>
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
    .news-main {{
      display: inline;
    }}
    .news-time {{
      display: inline-block;
      margin-left: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
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
      .news-main {{ display: block; }}
      .news-time {{ display: block; margin: 5px 0 0; }}
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


def write_briefing_page(stocks: list[str], articles: list[dict], briefing: str, settings: Optional[dict] = None) -> None:
    docs = Path("docs")
    briefings = docs / "briefings"
    briefings.mkdir(parents=True, exist_ok=True)
    today = kst_now().strftime("%Y-%m-%d")
    page = render_briefing_page(stocks, articles, briefing)
    (docs / "index.html").write_text(page, encoding="utf-8")
    (briefings / f"{today}.html").write_text(page, encoding="utf-8")
    if os.getenv("GITHUB_EVENT_NAME") == "schedule":
        sent_dir = docs / ".sent"
        sent_dir.mkdir(parents=True, exist_ok=True)
        marker = sent_marker_path(settings or {}, kst_now())
        marker.write_text(kst_now().isoformat(), encoding="utf-8")


def render_briefing_page(stocks: list[str], articles: list[dict], briefing: str) -> str:
    now = kst_now()
    today = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M")
    asset_version = now.strftime("%Y%m%d%H%M%S")
    article_rows = "\n".join(
        f"""
        <li>
          <span class="ticker">{html.escape(article["stock"])}</span>
          <span class="news-main">
            <a href="{html.escape(article["link"])}" target="_blank" rel="noreferrer">{html.escape(article["title"])}</a>
            <span class="news-time">{html.escape(article.get("published_display") or article.get("published", ""))} 발췌 · {html.escape(article.get("fetched_at", ""))} 확인</span>
          </span>
        </li>
        """
        for article in articles[:18]
    )
    stock_tags = "".join(f"<span data-stock-tag>{html.escape(stock)}</span>" for stock in stocks)
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
      --muted: #667085;
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
    body.modal-open {{ overflow: hidden; }}
    header {{
      background: var(--paper);
      border-bottom: 1px solid var(--line);
    }}
    .wrap {{
      width: min(920px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .top {{ padding: 34px 0 24px; }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--red);
      font-weight: 800;
    }}
    .mark {{
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      color: #fff;
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
    main {{ padding: 22px 0 44px; }}
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
    .actions {{
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .settings-summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }}
    .settings-summary strong {{
      color: var(--ink);
    }}
    button, .button-link {{
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      min-height: 40px;
      padding: 0 14px;
      font: inherit;
      font-weight: 750;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }}
    button.primary {{
      background: var(--red);
      border-color: var(--red);
      color: #fff;
    }}
    .icon-button {{
      width: 40px;
      padding: 0;
      font-size: 22px;
      line-height: 1;
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
    a:hover {{ text-decoration: underline; }}
    .ticker {{
      display: inline-block;
      min-width: 86px;
      margin-right: 8px;
      color: var(--green);
      font-weight: 800;
    }}
    .news-main {{
      display: inline;
    }}
    .news-time {{
      display: inline-block;
      margin-left: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
    }}
    small {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
    }}
    .modal {{
      position: fixed;
      inset: 0;
      display: grid;
      place-items: center;
      padding: 18px;
      background: rgba(17, 24, 39, 0.42);
      z-index: 10;
    }}
    .modal[hidden] {{ display: none; }}
    .dialog {{
      width: min(560px, 100%);
      max-height: min(760px, calc(100vh - 36px));
      overflow: auto;
      background: #fff;
      border-radius: 8px;
      border: 1px solid var(--line);
      box-shadow: 0 24px 70px rgba(17, 24, 39, 0.22);
    }}
    .dialog-head, .dialog-foot {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 18px;
      border-bottom: 1px solid var(--line);
    }}
    .dialog-foot {{
      border-top: 1px solid var(--line);
      border-bottom: 0;
      justify-content: flex-end;
      flex-wrap: wrap;
    }}
    .dialog h2 {{ margin: 0; }}
    .dialog-body {{ padding: 18px; }}
    .field-label {{
      display: block;
      margin: 0 0 8px;
      font-size: 13px;
      font-weight: 750;
      color: var(--muted);
    }}
    .time-field {{
      margin-bottom: 18px;
    }}
    .watch-row {{
      display: grid;
      grid-template-columns: 1fr 40px;
      gap: 8px;
      margin-bottom: 8px;
    }}
    input {{
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 12px;
      font: inherit;
    }}
    .status {{
      min-height: 20px;
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .status[data-tone="ok"] {{ color: var(--green); }}
    .status[data-tone="warn"] {{ color: #9a6700; }}
    .status[data-tone="error"] {{ color: var(--red); }}
    footer {{
      padding: 18px 0 34px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 640px) {{
      .wrap {{ width: min(100% - 24px, 920px); }}
      section {{ padding: 18px; }}
      .ticker {{ display: block; margin-bottom: 4px; }}
      .news-main {{ display: block; }}
      .news-time {{ display: block; margin: 5px 0 0; }}
      .dialog-foot {{ justify-content: stretch; }}
      .dialog-foot > * {{ flex: 1; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <div class="brand"><span class="mark">RS</span>RedStock</div>
      <h1>오늘의 주식 뉴스 브리핑</h1>
      <div class="meta">{generated_at} 생성 · Google Sheets 관심종목 기준</div>
      <div class="settings-summary">
        <span>발송 시간 <strong data-briefing-time-display>07:30</strong></span>
      </div>
      <div class="tags" data-stock-tags>{stock_tags}</div>
      <div class="actions">
        <button type="button" class="primary" data-watchlist-open>주식 종목 설정하기</button>
      </div>
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
  <div class="modal" data-watchlist-modal hidden>
    <form class="dialog" data-watchlist-form>
      <div class="dialog-head">
        <h2>관심 종목 설정</h2>
        <button type="button" class="icon-button" data-watchlist-close aria-label="닫기">×</button>
      </div>
      <div class="dialog-body">
        <label class="field-label" for="briefing-time">발송 시간</label>
        <div class="time-field">
          <input id="briefing-time" type="time" data-briefing-time value="07:30">
        </div>
        <div data-watchlist-list></div>
        <button type="button" data-watchlist-add>+ 종목 추가</button>
        <p class="status" data-watchlist-status></p>
      </div>
      <div class="dialog-foot">
        <a class="button-link" data-watchlist-sheet href="{SHEET_LINK}" target="_blank" rel="noreferrer">시트 열기</a>
        <button type="button" data-watchlist-close>취소</button>
        <button type="submit" class="primary">제출하기</button>
      </div>
    </form>
  </div>
  <footer class="wrap">투자 판단은 본인의 책임이며, 이 페이지는 뉴스 요약 참고용입니다.</footer>
  <script src="/MyRedStock/config.js?v={asset_version}"></script>
  <script src="/MyRedStock/watchlist.js?v={asset_version}"></script>
</body>
</html>
"""


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
    settings = load_remote_settings()
    if not should_send_now(settings):
        return 0

    remote_stocks = settings.get("stocks") if isinstance(settings.get("stocks"), list) else []
    stocks = [str(stock).strip() for stock in remote_stocks if str(stock).strip()] or load_watchlist()
    if not stocks:
        send_kakao_message("RedStock: Google Sheets A열에 브리핑 받을 종목을 추가해주세요.")
        return 0

    articles = fetch_news(stocks)
    if not articles:
        send_kakao_message("RedStock: 오늘 종목 관련 뉴스를 찾지 못했습니다. 시트의 종목명을 확인해주세요.")
        return 0

    briefing = summarize(stocks, articles)
    write_briefing_page(stocks, articles, briefing, settings)
    url = dated_briefing_url()
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
