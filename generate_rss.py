from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin
import re
import requests

BASE_URL = "https://rikos.rik.ee/"
CASE_RE = re.compile(r"\b[1-5]-\d{2,4}-\d+(?:/\d+)?\b")
DATE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")


def fetch_html():
    today = datetime.now().date()
    params = {
        "otsuseKpalgus": (today - timedelta(days=120)).strftime("%d.%m.%Y"),
        "otsuseKpLopp": today.strftime("%d.%m.%Y"),
        "pageSize": "100",
        "sortVaartus": "LahendiKuulutamiseAeg",
        "sortAsc": "false",
    }
    response = requests.get(
        BASE_URL,
        params=params,
        headers={"User-Agent": "riigikohus-rss/1.0 (+GitHub Actions)"},
        timeout=60,
    )
    response.raise_for_status()
    return response.text, response.url


def parse_items(html):
    soup = BeautifulSoup(html, "html.parser")
    items = {}

    for row in soup.select("tr"):
        row_text = " ".join(row.stripped_strings)
        case_match = CASE_RE.search(row_text)
        date_match = DATE_RE.search(row_text)
        if not case_match or not date_match:
            continue

        case = case_match.group(0)
        date = date_match.group(0)
        anchor = row.find("a", href=True)
        href = urljoin(BASE_URL, anchor["href"]) if anchor else f"{BASE_URL}LahendiOtsingEriVaade?asjaNr={case.split('/')[0]}"

        cells = [" ".join(cell.stripped_strings) for cell in row.find_all(["td", "th"])]
        description = max(cells, key=len) if cells else row_text
        items[case] = {"case": case, "date": date, "link": href, "description": description}

    if not items:
        text = " ".join(soup.stripped_strings)
        for match in re.finditer(r"(\d{2}\.\d{2}\.\d{4}).{0,120}?([1-5]-\d{2,4}-\d+(?:/\d+)?)", text):
            date, case = match.groups()
            items[case] = {
                "case": case,
                "date": date,
                "link": f"{BASE_URL}LahendiOtsingEriVaade?asjaNr={case.split('/')[0]}",
                "description": f"Riigikohtu lahend {case}",
            }

    return sorted(
        items.values(),
        key=lambda item: datetime.strptime(item["date"], "%d.%m.%Y"),
        reverse=True,
    )


def write_feed(items, source_url):
    if not items:
        raise RuntimeError("RIK-i otsingust ei leitud ühtegi lahendit; rss.xml jäeti muutmata.")

    fg = FeedGenerator()
    fg.id(BASE_URL)
    fg.title("Riigikohtu uued lahendid")
    fg.link(href=source_url, rel="alternate")
    fg.description("Riigikohtu viimased avaldatud lahendid")
    fg.language("et")

    for item in items:
        entry = fg.add_entry()
        entry.id(item["link"])
        entry.title(f'{item["case"]} | {item["date"]}')
        entry.link(href=item["link"])
        entry.description(item["description"])
        dt = datetime.strptime(item["date"], "%d.%m.%Y").replace(tzinfo=timezone.utc)
        entry.published(dt)

    fg.rss_file("rss.xml", pretty=True)


if __name__ == "__main__":
    html, source_url = fetch_html()
    items = parse_items(html)
    write_feed(items, source_url)
    print(f"Leitud {len(items)} lahendit. Uusim: {items[0]['date']} {items[0]['case']}")
