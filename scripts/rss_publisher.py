
import os
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

FEEDS = [
    {
        "url": "https://rss.dw.com/xml/rss-ar-all",
        "language": "ar",
        "category": "أخبار",
        "icon": "📰",
    },
    {
        "url": "https://rss.dw.com/xml/rss-fr-all",
        "language": "fr",
        "category": "Actualités",
        "icon": "📰",
    },
    {
        "url": "https://rss.dw.com/xml/rss-en-all",
        "language": "en",
        "category": "News",
        "icon": "📰",
    },
]

def clean_text(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def get_value(element, name):
    for child in element.iter():
        if child.tag.split("}")[-1] == name:
            return child
    return None

def fetch_feed(feed):
    request = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "ChatMix RSS Publisher/1.0"}
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())

    entries = []

    for item in root.iter():
        if item.tag.split("}")[-1] not in ("item", "entry"):
            continue

        title_node = get_value(item, "title")
        description_node = (
            get_value(item, "description")
            or get_value(item, "summary")
            or get_value(item, "encoded")
        )

        link_node = get_value(item, "link")

        title = clean_text(
            title_node.text if title_node is not None else ""
        )

        summary = clean_text(
            "".join(description_node.itertext())
            if description_node is not None else ""
        )

        link = ""

        if link_node is not None:
            link = (
                link_node.attrib.get("href", "")
                or link_node.text
                or ""
            ).strip()

        if title and link.startswith("https://") and summary:
            entries.append({
                "title": title[:250],
                "summary": summary[:700],
                "link": link,
            })

    return entries

def publish_article(article, feed):
    payload = {
        "title": article["title"],
        "category": feed["category"],
        "content": article["summary"],
        "description": article["summary"][:220],
        "icon": feed["icon"],
        "language": feed["language"],
        "source_url": article["link"],
        "source_name": "Deutsche Welle",
        "published": True,
    }

    url = (
        SUPABASE_URL
        + "/rest/v1/articles?"
        + urllib.parse.urlencode({
            "on_conflict": "source_url,language"
        })
    )

    data = __import__("json").dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status

def main():
    total = 0

    for feed in FEEDS:
        print("Reading:", feed["language"])

        try:
            articles = fetch_feed(feed)

            for article in articles[:10]:
                try:
                    publish_article(article, feed)
                    total += 1
                    print("Processed:", article["title"])
                except Exception as error:
                    print("Article error:", error)

        except Exception as error:
            print("Feed error:", feed["language"], error)

    print("Finished. Processed:", total)

if __name__ == "__main__":
    main()
