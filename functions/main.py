import datetime
from base64 import b64encode

import requests
from firebase_admin import firestore, initialize_app
from firebase_functions import https_fn
from readability import Document

initialize_app()

FEED_HEADER = f"""
<?xml version="1.1" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <id>https://github.com/Gudsfile/Pochurl</id>
    <title>Pochurl - what do I have to read?</title>
    <updated>{datetime.datetime.now().isoformat()}</updated>
    <generator>https://github.com/Gudsfile/Pochurl</generator>
    <icon>https://en.wikipedia.org/static/favicon/wikipedia.ico</icon>
"""

FEED_FOOTER = """
</feed>
"""


@https_fn.on_request()
def add_entry(req: https_fn.Request) -> https_fn.Response:
    """Take the body passed to this HTTP endpoint and insert it into
    a new document in the entries collection."""
    link = req.json.get("link")

    if link is None:
        return https_fn.Response("No link parameter provided", status=400)

    client = firestore.client()
    db = client.collection("entries")

    updated = datetime.datetime.now().isoformat()
    entry_id = b64encode(bytes(link, encoding="utf-8")).decode("utf-8")
    title, content = extract_content(link)
    entry = {"link": link, "title": title, "updated": updated, "xml_content": entry_to_xml(entry_id, link, title, updated, content)}

    db.document(entry_id).set(entry)

    return https_fn.Response(f"Entry with ID {entry_id} added.")


@https_fn.on_request()
def get_entries(req: https_fn.Request) -> https_fn.Response:
    """Return the feed XML from the entries collection."""
    client = firestore.client()
    db = client.collection("entries")

    entries = db.stream()
    feed_content = "\n".join([entry.get("xml_content") for entry in entries])
    feed = f"{FEED_HEADER}\n{feed_content}\n{FEED_FOOTER}"

    return https_fn.Response(feed, mimetype="text/xml")


def extract_content(link: str):
    response = requests.get(link, timeout=10)
    doc = Document(response.content)
    return doc.title(), doc.summary()


def entry_to_xml(entry_id, link, title, updated, content):
    header = "<entry>"
    entry_id = f"""<id>{entry_id}</id>"""
    title = f"""<title type="html"><![CDATA[{title}]]></title>"""
    updated = f"""<updated>{updated}</updated>"""
    content = f"""<content type="html"><![CDATA[{content}]]></content>"""
    link = f"""<link href="{link}"></link>"""
    footer = "</entry>"
    return "\n".join([header, title, entry_id, link, updated, content, footer])
