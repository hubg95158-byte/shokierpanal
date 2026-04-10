# -*- coding: utf-8 -*-
import html
import re
from urllib.parse import urlencode
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# --- تغيير التوكن هنا (تم تعبئة الخاصة بك) ---
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2FwaS5nb2xkZW4td2F2ZS5tZS9hcGkvd2Vic2l0ZS9sb2dpbiIsImlhdCI6MTc3NTc4NDA0MiwiZXhwIjoxODA3MzIwMDQyLCJuYmYiOjE3NzU3ODQwNDIsImp0aSI6ImZ5M1YwSHhKU1drYnZENTgiLCJzdWIiOiIxNDUzIiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyIsImxhc3RfbG9naW5fYXQiOiIyMDI2LTA0LTEwVDAxOjIwOjQyLjYwODAxOFoiLCJ0aW1lem9uZSI6IlVUQyJ9.iRhUyVKIEatvon0c5zvfaSXAxi8Tmcdz1djF6tPkJvw"  # تأكد من عدم تغييره أو حذفه

API_BASE = "https://api.golden-wave.me/api/website/blogs"


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
        r"youtu.be/([a-zA-Z0-9_-]{11})",
        r"youtube.com/watch?v=([a-zA-Z0-9_-]{11})",
        r"youtube.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube.com/shorts/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    m = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url)
    if m:
        return m.group(1)

    return None


def h(text):
    return html.escape(str(text if text is not None else ""), quote=True)


def nl2br(text):
    return h(text).replace("
", "<br>")


def fetch_all_items():
    items = []
    page = 1

    while True:
        res = get_epage(page, API_BASE, TOKEN)

        if not res["ok"]:
            raise Exception(
                f"Page {page} failed
Code: {res.get('code')}
Error: {res.get('error')}"
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


# --- HTML + CSS TEMPLATE كاملة ومطورة ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ page_title }}</title>
  <style>
    :root {
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-card: #1e293b;
      --border-radius: 12px;
      --shadow: 0 10px 25px rgba(0,0,0,0.3);
      --text: #e2e8f0;
      --text-muted: #94a3b8;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
    }
    body {
      font-family: Tahoma, Arial, sans-serif;
      direction: rtl;
      margin: 0;
      padding: 20px 16px 40px 16px;
      background: var(--bg-primary);
      color: var(--text);
      line-height: 1.6;
    }
    .container {
      max-width: 1024px;
      margin: 0 auto;
    }
    .error {
      background: #111111;
      color: #00ff00;
      padding: 20px;
      border-radius: var(--border-radius);
      white-space: pre-wrap;
      font-size: 13px;
      overflow-x: auto;
    }
    .header {
      text-align: right;
      margin-bottom: 24px;
    }
    .header h1 {
      margin: 0 0 8px 0;
      font-size: 1.6rem;
      font-weight: bold;
    }
    .header small {
      color: var(--text-muted);
      font-size: 0.9rem;
    }
    .back-link {
      color: #7dd3fc;
      text-decoration: none;
      font-size: 0.95rem;
      margin-top: 16px;
      display: inline-block;
    }
    .back-link:hover {
      text-decoration: underline;
    }
    .item-list {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }
    .card {
      padding: 16px;
      background: var(--bg-card);
      border-radius: var(--border-radius);
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: var(--shadow);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 35px rgba(0,0,0,0.4);
    }
    .card a {
      color: #fff;
      text-decoration: none;
    }
    .card a:hover {
      color: #7dd3fc;
    }
    .card h3 {
      margin: 0 0 8px 0;
      font-size: 1.1rem;
      font-weight: 600;
    }
    .card p {
      margin: 0;
      font-size: 0.9rem;
      color: var(--text-muted);
    }
    .iframe-wrapper {
      margin-top: 16px;
      border-radius: var(--border-radius);
      overflow: hidden;
      box-shadow: var(--shadow);
    }
    iframe {
      width: 100%;
      height: 500px;
      border: 0;
    }
    .content {
      margin-top: 16px;
      font-size: 0.95rem;
      color: var(--text-muted);
    }
    .content br {
      margin: 4px 0;
    }
  </style>
</head>
<body>
  <div class="container">
    {% if error_message %}
      <div class="error">{{ error_message }}</div>
    {% elif selected_item %}
      <header class="header">
        <h1>{{ selected_item.title }}</h1>
        <small>{{ selected_item.created_at }}</small>
      </header>

      {% if embed_url %}
        <div class="iframe-wrapper">
          <iframe
            src="{{ embed_url }}"
            allowfullscreen>
          </iframe>
        </div>
      {% else %}
        <div style="margin-top:16px;color:var(--text-muted)">
          لا يوجد فيديو لهذا المحتوى
        </div>
      {% endif %}

      <div class="content">{{ selected_item_desc|safe }}</div>
      <a href="/" class="back-link">رجوع للرئيسية</a>
    {% else %}
      <header class="header">
        <h1>منصة شقير المجانية</h1>
        <small>منصة تعليمية تقدم محتوى عربي مجاني</small>
      </header>

      <div class="item-list">
        {% for item in items %}
          <article class="card">
            <a href="/?id={{ item.id }}">
              <h3>{{ item.title or "بدون عنوان" }}</h3>
              <p>{{ item.desc_html|safe }}</p>
            </a>
          </article>
        {% endfor %}
      </div>
    {% endif %}
  </div>
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
