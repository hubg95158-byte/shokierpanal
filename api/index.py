# -*- coding: utf-8 -*-
import html
import re
from urllib.parse import urlencode

import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

API_BASE = "https://api.golden-wave.me/api/website/blogs"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2FwaS5nb2xkZW4td2F2ZS5tZS9hcGkvd2Vic2l0ZS9sb2dpbiIsImlhdCI6MTc3NTc4NDA0MiwiZXhwIjoxODA3MzIwMDQyLCJuYmYiOjE3NzU3ODQwNDIsImp0aSI6ImZ5M1YwSHhKU1drYnZENTgiLCJzdWIiOiIxNDUzIiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyIsImxhc3RfbG9naW5fYXQiOiIyMDI2LTA0LTEwVDAxOjIwOjQyLjYwODAxOFoiLCJ0aW1lem9uZSI6IlVUQyJ9.iRhUyVKIEatvon0c5zvfaSXAxi8Tmcdz1djF6tPkJvw"


def get_page(page, api_base, token):
    url = f"{api_base}?page={int(page)}"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "ar",
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
        )
    except requests.RequestException as e:
        return {"ok": False, "error": str(e), "code": 0}

    try:
        data = response.json()
    except Exception:
        return {
            "ok": False,
            "error": "Invalid JSON",
            "code": response.status_code,
            "raw": response.text,
        }

    return {"ok": True, "data": data, "code": response.status_code}


def extract_youtube_id(url):
    if not url:
        return None

    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{6,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    m = re.search(r"[?&]v=([a-zA-Z0-9_-]{6,})", url)
    if m:
        return m.group(1)

    return None


def h(text):
    return html.escape(str(text if text is not None else ""), quote=True)


def nl2br(text):
    return h(text).replace("\n", "<br>")


def fetch_all_items():
    items = []
    page = 1

    while True:
        res = get_page(page, API_BASE, TOKEN)

        if not res["ok"]:
            raise Exception(
                f"Page {page} failed\nCode: {res.get('code')}\nError: {res.get('error')}"
            )

        json_data = res["data"]

        if not json_data.get("data") or not isinstance(json_data.get("data"), list):
            break

        for item in json_data["data"]:
            item["youtube_id"] = extract_youtube_id(item.get("link", ""))
            item["has_video"] = bool(item.get("youtube_id"))
            item["has_files"] = bool(item.get("files")) and isinstance(item.get("files"), list)
            item["search_text"] = (
                f"{item.get('title', '')} {item.get('desc', '')} {item.get('created_at', '')}"
            ).lower()
            items.append(item)

        meta = json_data.get("meta", {})
        links = json_data.get("links", {})

        if "last_page" in meta:
            last_page = int(meta["last_page"])
            if page >= last_page:
                break
        elif not links.get("next"):
            break

        page += 1

    return items


TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ page_title }}</title>
</head>
<body style="font-family:Tahoma,Arial,sans-serif;direction:rtl;padding:20px;background:#0f172a;color:#fff">
  {% if error_message %}
    <pre style="background:#111;color:#0f0;padding:20px;border-radius:12px;white-space:pre-wrap">{{ error_message }}</pre>
  {% elif selected_item %}
    <h1>{{ selected_item.title }}</h1>
    {% if embed_url %}
      <iframe
        width="100%"
        height="500"
        src="{{ embed_url }}"
        allowfullscreen
        style="border:0;border-radius:14px">
      </iframe>
    {% else %}
      <div>لا يوجد فيديو لهذا المحتوى</div>
    {% endif %}

    <div style="margin-top:20px">{{ selected_item_desc|safe }}</div>
    <p><a href="/" style="color:#7dd3fc">رجوع للرئيسية</a></p>
  {% else %}
    <h1>منصة شقير المجانية</h1>
    {% for item in items %}
      <div style="padding:14px;margin:12px 0;background:#1e293b;border-radius:14px">
        <a href="/?id={{ item.id }}" style="color:#fff;text-decoration:none">
          <h3>{{ item.title or "بدون عنوان" }}</h3>
          <div>{{ item.desc_html|safe }}</div>
        </a>
      </div>
    {% endfor %}
  {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    selected_id = request.args.get("id", default=0, type=int)

    try:
        items = fetch_all_items()
    except Exception as e:
        return render_template_string(
            TEMPLATE,
            page_title="خطأ | منصة شقير المجانية",
            error_message=str(e),
            selected_item=None,
            items=[],
            embed_url="",
            selected_item_desc="",
        ), 500

    for item in items:
        item["desc_html"] = nl2br(item.get("desc", ""))

    selected_item = None
    if selected_id > 0:
        for it in items:
            if int(it.get("id", 0)) == selected_id:
                selected_item = it
                break

    embed_url = ""
    selected_item_desc = ""

    if selected_item:
        if selected_item.get("youtube_id"):
            params = {"rel": 0, "modestbranding": 1, "controls": 1}
            embed_url = f"https://www.youtube.com/embed/{selected_item['youtube_id']}?{urlencode(params)}"

        selected_item_desc = nl2br(selected_item.get("desc", ""))

    page_title = (
        f"{selected_item.get('title')} | منصة شقير المجانية"
        if selected_item else
        "منصة شقير المجانية"
    )

    return render_template_string(
        TEMPLATE,
        page_title=page_title,
        error_message="",
        selected_item=selected_item,
        items=items,
        embed_url=embed_url,
        selected_item_desc=selected_item_desc,
    )
