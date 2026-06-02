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
    {"name":"바이오스펙테이터","url":"https://www.biospectator.com/section/section_list?MID=10000","article_selector":"div.article_list li","title_selector":"a.tit
