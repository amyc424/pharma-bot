import os, json, hashlib, time, re, requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_news.json"
SIMILARITY_THRESHOLD = 0.75
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SOURCES = [
    {"name":"바이오뉴스","url":"https://www.thebionews.net/news/articleList.html?page=1&total=19488&box_idxno=&view_type=sm","article_selector":"ul.type2 li","title_selector":"dt a","link_selector":"dt a","base_url":"https://www.thebionews.net"},
    {"name":"뉴스MP","url":"https://www.newsmp.com/news/articleList.html?sc_section_code=S1N6&view_type=sm","article_selector":"ul.type2 li","title_selector":"dt a","link_selector":"dt a","base_url":"https://www.newsmp.com"},
    {"name":"약업닷컴","url":"https://www.yakup.com/news/index.html?cat=12&cat2=121","article_selector":"div.news_list li","title_selector":"a.news_title","link_selector":"a.news_title","base_url":"https://www.yakup.com"},
    {"name":"바이오스펙테이터","url":"https://www.biospectator.com/section/section_list?MID=10000","article_selector":"div.article_list li","title_selector":"a.tit","link_selector":"a.tit","base_url":"https://www.biospectator.com"},
    {"name":"한경바이오인사이트","url":"https://www.hankyung.com/bioinsight","article_selector":"li.news-item","title_selector":"h3 a","link_selector":"h3 a","base_url":"https://www.hankyung.com"},
    {"name":"메디소비자뉴스","url":"https://www.medisobizanews.com/news/articleList.html?view_type=sm","article_selector":"ul.type2 li","title_selector":"dt a","link_selector":"dt a","base_url":"https://www.medisobizanews.com"},
    {"name":"히트뉴스","url":"https://www.hitnews.co.kr/news/articleList.html?sc_sub_section_code=S2N17&view_type=sm","article_selector":"ul.type2 li","title_selector":"dt a","link_selector":"dt a","base_url":"https://www.hitnews.co.kr"},
    {"name":"FiercePharma","url":"https://www.fiercepharma.com/","article_selector":"article","title_selector":"h3 a, h2 a","link_selector":"h3 a, h2 a","base_url":"https://www.fiercepharma.com"},
    {"name":"BioSpace","url":"https://www.biospace.com/latest-news-press-releases","article_selector":"article","title_selector":"h3 a, h2 a","link_selector":"h3 a, h2 a","base_url":"https://www.biospace.com"},
    {"name":"BiopharmaDive","url":"https://www.biopharmadive.com/topic/biotech/","article_selector":"article","title_selector":"h3 a, h2 a","link_selector":"h3 a, h2 a","base_url":"https://www.biopharmadive.com"},
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

def fetch_articles(source):
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
        print(f"[ERROR] {source['name']}: {e}")
    return articles

def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10
    )

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 시작")
    seen = load_seen()
    new_articles = []
    for source in SOURCES:
        arts = fetch_articles(source)
        print(f"  {source['name']}: {len(arts)}개")
        for art in arts:
            if not is_duplicate(art["url"], art["title"], seen):
                new_articles.append(art)
                seen["urls"].append(url_hash(art["url"]))
                seen["titles"].append(art["title"].strip())
        time.sleep(1)
    print(f"새 기사: {len(new_articles)}개")
    for art in new_articles[:30]:
        send_telegram(f"💊 <b>[{art['source']}]</b>\n{art['title']}\n🔗 {art['url']}")
        time.sleep(0.5)
    if len(new_articles) > 30:
        send_telegram(f"ℹ️ 총 {len(new_articles)}개 중 30개만 전송했습니다.")
    save_seen(seen)
    print("완료")

if __name__ == "__main__":
    main()
