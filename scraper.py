import os, json, hashlib, time, re, requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from datetime import datetime
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_news.json"
SIMILARITY_THRESHOLD = 0.75
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 우선순위 회사 & 키워드
PRIORITY_COMPANIES = [
    "삼성바이오로직스", "셀트리온", "SK바이오팜", "유한양행",
    "한미약품", "대웅제약", "녹십자", "에스티팜", "HK이노엔"
]
PRIORITY_KEYWORDS = [
    "기술이전", "적응증", "임상", "FDA", "IND", "NDA", "BLA",
    "허가", "승인", "파이프라인", "Phase", "3상", "2상", "1상", "인수"
]

def is_priority(title):
    for company in PRIORITY_COMPANIES:
        if company in title:
            for keyword in PRIORITY_KEYWORDS:
                if keyword.lower() in title.lower():
                    return True
    return False

# RSS 피드 소스
RSS_SOURCES = [
    {"name": "바이오뉴스", "url": "https://www.thebionews.net/rss/allArticle.xml"},
    {"name": "히트뉴스", "url": "https://www.hitnews.co.kr/rss/allArticle.xml"},
    {"name": "메디소비자뉴스", "url": "https://www.medisobizanews.com/rss/allArticle.xml"},
    {"name": "뉴스MP", "url": "https://www.newsmp.com/rss/allArticle.xml"},
    {"name": "FiercePharma", "url": "https://www.fiercepharma.com/rss/xml"},
    {"name": "BiopharmaDive", "url": "https://www.biopharmadive.com/feeds/news/"},
    {"name": "BioSpace", "url": "https://www.biospace.com/rss/news"},
]

# HTML 크롤링 소스 (RSS 없는 곳)
HTML_SOURCES = [
    {"name":"약업닷컴","url":"https://www.yakup.com/news/index.html?cat=12&cat2=121","article_selector":"div.news_list li","title_selector":"a.news_title","link_selector":"a.news_title","base_url":"https://www.yakup.com"},
    {"name":"바이오스펙테이터","url":"https://www.biospectator.com/section/section_list?MID=10000","article_selector":"ul.article_list li","title_selector":"a.tit","link_selector":"a.tit","base_url":"https://www.biospectator.com"},
    {"name":"한경바이오인사이트","url":"https://www.hankyung.com/bioinsight","article_selector":"div.article-list li","title_selector":"a","link_selector":"a","base_url":"https://www.hankyung.com"},
]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"urls": [], "titles": []}

def save_seen(seen):
    seen["urls"] = seen["urls"][-2000:]
    seen["titles"] = seen["titles"][-2000:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def url_hash(url):
    return hashlib.md5(url.strip().encode()).hexdigest()

def is_duplicate(url, title, seen):
    if url_hash(url) in seen["urls"]:
        return True
    clean = lambda s: re.sub(r"\s+", " ", s.strip().lower())
    for old in seen["titles"][-500:]:
        if SequenceMatcher(None, clean(title), clean(old)).ratio() >= SIMILARITY_THRESHOLD:
            return True
    return False

def fetch_rss(source):
    articles = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        for item in items[:20]:
            title_el = item.find("title")
            link_el = item.find("link")
            if title_el is None or link_el is None:
                continue
            title = title_el.text or ""
            url = link_el.text or ""
            title = re.sub(r"<[^>]+>", "", title).strip()
            if title and url:
                articles.append({"title": title, "url": url, "source": source["name"]})
    except Exception as e:
        print(f"[RSS ERROR] {source['name']}: {e}")
    return articles

def fetch_html(source):
    articles = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(source["article_selector"])[:20]:
            t = item.select_one(source["title_selector"])
            l = item.select_one(source["link_selector"])
            if not t or not l: continue
            title = t.get_text(strip=True)
            href = l.get("href", "")
            if not title or not href: continue
            url = href if href.startswith("http") else source["base_url"] + (href if href.startswith("/") else "/" + href)
            articles.append({"title": title, "url": url, "source": source["name"]})
    except Exception as e:
        print(f"[HTML ERROR] {source['name']}: {e}")
    return articles

def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 시작")
    seen = load_seen()
    priority_articles = []
    normal_articles = []

    for source in RSS_SOURCES:
        arts = fetch_rss(source)
        print(f"  {source['name']}: {len(arts)}개")
        for art in arts:
            if not is_duplicate(art["url"], art["title"], seen):
                if is_priority(art["title"]):
                    priority_articles.append(art)
                else:
                    normal_articles.append(art)
                seen["urls"].append(url_hash(art["url"]))
                seen["titles"].append(art["title"].strip())
        time.sleep(0.5)

    for source in HTML_SOURCES:
        arts = fetch_html(source)
        print(f"  {source['name']}: {len(arts)}개")
        for art in arts:
            if not is_duplicate(art["url"], art["title"], seen):
                if is_priority(art["title"]):
                    priority_articles.append(art)
                else:
                    normal_articles.append(art)
                seen["urls"].append(url_hash(art["url"]))
                seen["titles"].append(art["title"].strip())
        time.sleep(0.5)

    print(f"우선순위 기사: {len(priority_articles)}개, 일반 기사: {len(normal_articles)}개")

    sent = 0
    for art in priority_articles[:10]:
        send_telegram(f"🔥 <b>[우선] [{art['source']}]</b>\n{art['title']}\n🔗 {art['url']}")
        sent += 1
        time.sleep(0.5)

    for art in normal_articles[:20]:
        send_telegram(f"💊 <b>[{art['source']}]</b>\n{art['title']}\n🔗 {art['url']}")
        sent += 1
        time.sleep(0.5)

    print(f"완료: {sent}개 전송")
    save_seen(seen)

if __name__ == "__main__":
    main()
