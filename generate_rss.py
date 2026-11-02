from playwright.sync_api import sync_playwright
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import quote
import re

URL = "https://rikos.rik.ee/Lahendid"
CASE_RE = re.compile(r"\b[1-5]-\d{2,4}-\d+(?:/\d+)?\b")
DATE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    text = page.locator("body").inner_text()
    print("===== RIK PAGE CONTENT =====")
    print(text)
    print("===== END CONTENT =====")
    browser.close()

lines = [x.strip() for x in text.splitlines() if x.strip()]
items = []
current_date = None

for line in lines:
    if DATE_RE.fullmatch(line):
        current_date = line
        continue
    if CASE_RE.fullmatch(line) and current_date:
        items.append({"date": current_date, "case": line})

unique = {}
for item in items:
    unique[item["case"]] = item
items = list(unique.values())

fg = FeedGenerator()
fg.id(URL)
fg.title("Riigikohtu uued lahendid")
fg.link(href=URL, rel="alternate")
fg.description("Riigikohtu viimased avaldatud lahendid")
fg.language("et")

for item in items:
    case = item["case"]
    date = item["date"]
    link = f"https://rikos.rik.ee/Lahendid?asjaNr={quote(case)}"
    entry = fg.add_entry()
    entry.id(link)
    entry.title(f"{case} | {date}")
    entry.link(href=link)
    entry.description(f'Riigikohtu lahend {case}<br>Kuupäev: {date}<br><a href="{link}">Ava lahend RIK-is</a>')
    try:
        dt = datetime.strptime(date, "%d.%m.%Y")
        entry.published(dt.replace(tzinfo=timezone.utc))
    except ValueError:
        pass

fg.rss_file("rss.xml", pretty=True)
print(f"Leitud {len(items)} lahendit.")
