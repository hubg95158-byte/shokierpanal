# -*- coding: utf-8 -*-
import html
import json
import re
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

API_BASE = "https://api.golden-wave.me/api/website/blogs"
LOGIN_URL = "https://api.golden-wave.me/api/website/login"

STUDENT_CODE = "26687"
PASSWORD = "123456789"

SITE_NAME = "منصة شقير المجانية"
SITE_DESC = "منصة تعليمية سريعة وحديثة بعرض فيديوهات داخل الموقع"
TIMEOUT = 20
TOKEN_CACHE_FILE = Path("token_cache.json")


def esc(text):
    return html.escape(str(text or ""), quote=True)


def nl2br(text):
    return esc(text).replace("\n", "<br>")


def extract_youtube_id(url: str):
    if not url:
        return None

    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{6,})",
        r"[?&]v=([a-zA-Z0-9_-]{6,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def read_cached_token():
    try:
        if TOKEN_CACHE_FILE.exists():
            data = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
            token = data.get("token")
            if token:
                return token
    except Exception:
        pass
    return None


def write_cached_token(token: str):
    TOKEN_CACHE_FILE.write_text(
        json.dumps(
            {
                "token": token,
                "saved_at": int(time.time()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def clear_cached_token():
    try:
        if TOKEN_CACHE_FILE.exists():
            TOKEN_CACHE_FILE.unlink()
    except Exception:
        pass


def extract_token_from_login_response(data):
    if not isinstance(data, dict):
        return None

    direct_keys = ["token", "access_token", "accessToken"]
    for key in direct_keys:
        if data.get(key):
            return data[key]

    nested = data.get("data")
    if isinstance(nested, dict):
        for key in direct_keys:
            if nested.get(key):
                return nested[key]

    return None


def login_and_cache_token():
    headers = {
        "User-Agent": "Dart/3.7 (dart:io)",
        "Accept": "application/json",
        "Accept-Language": "ar",
        "Content-Type": "application/json",
    }

    payload = {
        "student_code": STUDENT_CODE,
        "password": PASSWORD,
    }

    response = requests.post(
        LOGIN_URL,
        headers=headers,
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()
    token = extract_token_from_login_response(data)

    if not token:
        raise ValueError(f"لم يتم العثور على token في رد تسجيل الدخول: {data}")

    write_cached_token(token)
    return token


def get_valid_token(force_refresh=False):
    if not force_refresh:
        cached = read_cached_token()
        if cached:
            return cached
    return login_and_cache_token()


def build_api_headers(token: str):
    return {
        "Accept": "application/json",
        "Accept-Language": "ar",
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {token}",
    }


def authorized_get(url: str):
    token = get_valid_token(force_refresh=False)

    response = requests.get(
        url,
        headers=build_api_headers(token),
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    if response.status_code == 401:
        clear_cached_token()
        token = get_valid_token(force_refresh=True)
        response = requests.get(
            url,
            headers=build_api_headers(token),
            timeout=TIMEOUT,
            allow_redirects=True,
        )

    response.raise_for_status()
    return response.json()


def get_page(page: int):
    return authorized_get(f"{API_BASE}?page={page}")


@lru_cache(maxsize=4)
def fetch_items(cache_key: int):
    items = []
    page = 1

    while True:
        data = get_page(page)
        rows = data.get("data", [])

        if not isinstance(rows, list) or not rows:
            break

        for item in rows:
            title = item.get("title", "") or ""
            desc = item.get("desc", "") or ""
            created = item.get("created_at", "") or ""
            yt = extract_youtube_id(item.get("link", "") or "")

            item["youtube_id"] = yt
            item["has_video"] = bool(yt)
            item["has_files"] = isinstance(item.get("files"), list) and bool(item.get("files"))
            item["thumb"] = f"https://img.youtube.com/vi/{yt}/hqdefault.jpg" if yt else ""
            item["thumb_small"] = f"https://img.youtube.com/vi/{yt}/mqdefault.jpg" if yt else ""
            item["desc_html"] = nl2br(desc)
            item["title_lower"] = title.lower()
            item["search_text"] = f"{title} {desc} {created}".lower()
            items.append(item)

        meta = data.get("meta", {})
        links = data.get("links", {})

        if meta.get("last_page"):
            if page >= int(meta["last_page"]):
                break
        elif not links.get("next"):
            break

        page += 1

    return items


def all_items():
    return fetch_items(int(time.time() // 180))


def get_stats(items):
    return {
        "total": len(items),
        "videos": sum(1 for i in items if i.get("has_video")),
        "files": sum(1 for i in items if i.get("has_files")),
        "downloads": sum(1 for i in items if i.get("can_download")),
    }


def get_embed_url(item):
    if not item or not item.get("youtube_id"):
        return ""

    params = urlencode(
        {
            "rel": 0,
            "modestbranding": 1,
            "controls": 1,
        }
    )
    return f"https://www.youtube.com/embed/{item['youtube_id']}?{params}"


TEMPLATE = r'''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }}</title>
    <meta name="description" content="{{ site_desc }}">
    <meta name="theme-color" content="#0b1220">
    <style>
        :root{
            --bg:#07111f;
            --card:rgba(255,255,255,.08);
            --card2:rgba(255,255,255,.05);
            --line:rgba(255,255,255,.12);
            --txt:#f8fafc;
            --muted:#cbd5e1;
            --blue:#2563eb;
            --cyan:#06b6d4;
            --shadow:0 22px 60px rgba(0,0,0,.30);
        }
        *{box-sizing:border-box}
        html{scroll-behavior:smooth}
        body{
            margin:0;
            font-family:Tahoma,Arial,sans-serif;
            color:var(--txt);
            background:
                radial-gradient(circle at top right, rgba(37,99,235,.22), transparent 24%),
                linear-gradient(180deg, #020617, #07111f 40%, #0f172a 100%);
            min-height:100vh;
        }
        a{text-decoration:none;color:inherit}
        .container{width:min(1400px,94%);margin:auto;padding:24px 0 42px}
        .glass{
            background:var(--card);
            border:1px solid var(--line);
            box-shadow:var(--shadow);
            backdrop-filter:blur(14px);
        }
        .hero{
            border-radius:36px;
            padding:24px;
            background:linear-gradient(135deg, rgba(37,99,235,.96), rgba(6,182,212,.86));
        }
        .topbar,.hero-badges,.hero-actions,.meta,.btn-row{
            display:flex;
            gap:10px;
            flex-wrap:wrap;
            align-items:center;
            justify-content:space-between;
        }
        .brand,.hero-badge,.pill,.counter{
            padding:10px 14px;
            border-radius:999px;
            background:rgba(255,255,255,.12);
            border:1px solid rgba(255,255,255,.16);
            font-weight:800;
        }
        .hero-grid,.video-layout{
            display:grid;
            grid-template-columns:1.25fr .95fr;
            gap:18px;
            margin-top:18px;
        }
        .site-title{
            margin:0;
            font-size:clamp(32px,5vw,58px);
            line-height:1.18;
            font-weight:900;
        }
        .site-subtitle{
            margin:12px 0 0;
            line-height:2;
            font-size:16px;
            color:rgba(255,255,255,.96);
        }
        .panel,.controls,.card-body,.player-content,.side-card,.strip-card{
            padding:18px;
        }
        .panel,.controls,.card,.player-card,.side-card,.strip-card,.featured-card{
            border-radius:28px;
        }
        .btn,.action-main,.action-alt,.top-btn{
            border:0;
            cursor:pointer;
            border-radius:16px;
            padding:12px 16px;
            font-weight:800;
        }
        .btn.main,.action-main{
            background:linear-gradient(135deg,var(--blue),var(--cyan));
            color:#fff;
        }
        .btn.outline,.action-alt,.top-btn{
            background:rgba(255,255,255,.06);
            color:#fff;
            border:1px solid var(--line);
        }
        .stats-grid,.strip,.featured-grid,.controls-grid,.grid,.side-stack,.related-list{
            display:grid;
            gap:14px;
        }
        .stats-grid{grid-template-columns:repeat(2,1fr)}
        .strip{grid-template-columns:repeat(4,1fr)}
        .featured-grid{grid-template-columns:repeat(3,1fr)}
        .controls-grid{grid-template-columns:1.5fr 1fr 1fr auto auto}
        .grid{grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}
        .featured-card,.card{overflow:hidden}
        .featured-card{
            position:relative;
            min-height:260px;
            display:flex;
            align-items:flex-end;
        }
        .featured-bg{
            position:absolute;
            inset:0;
            background-size:cover;
            background-position:center;
        }
        .featured-overlay{
            position:absolute;
            inset:0;
            background:linear-gradient(180deg, rgba(0,0,0,.10), rgba(0,0,0,.82));
        }
        .featured-body{
            position:relative;
            z-index:2;
            padding:18px;
            width:100%;
        }
        .featured-title,.card-title,.video-title{margin:0 0 10px}
        .featured-title,.card-title{font-size:22px;line-height:1.7}
        .video-title{font-size:34px;line-height:1.6}
        .input,.select{
            width:100%;
            border-radius:16px;
            border:1px solid var(--line);
            background:rgba(255,255,255,.06);
            color:var(--txt);
            padding:14px 16px;
            outline:none;
        }
        .thumb,.player-wrap{
            position:relative;
            aspect-ratio:16/9;
            overflow:hidden;
            background:#000;
        }
        .thumb img,.player-wrap iframe,.related-thumb{
            width:100%;
            height:100%;
            object-fit:cover;
            display:block;
        }
        .fallback,.player-placeholder,.related-fallback{
            display:grid;
            place-items:center;
            background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.2));
            font-weight:800;
        }
        .thumb-top{
            position:absolute;
            top:14px;
            left:14px;
            right:14px;
            display:flex;
            justify-content:space-between;
            gap:10px;
        }
        .thumb-badge,.thumb-index{
            padding:8px 12px;
            border-radius:999px;
            font-size:12px;
            font-weight:800;
        }
        .thumb-badge{background:rgba(220,38,38,.92);color:#fff}
        .thumb-index{
            background:rgba(255,255,255,.12);
            color:#fff;
            border:1px solid rgba(255,255,255,.16);
        }
        .card-desc,.video-desc,.note,.strip-desc,.stat-note{
            color:var(--muted);
            line-height:1.9;
        }
        .player-glow{
            position:absolute;
            inset:auto 0 0 0;
            height:120px;
            background:linear-gradient(to top, rgba(0,0,0,.48), transparent);
        }
        .related-item{
            display:grid;
            grid-template-columns:108px 1fr;
            gap:10px;
            padding:10px;
            border-radius:18px;
            background:rgba(255,255,255,.04);
            border:1px solid var(--line);
        }
        .related-thumb,.related-fallback{
            width:108px;
            height:68px;
            border-radius:14px;
            background:#000;
        }
        .empty-state{
            display:none;
            margin-top:18px;
            padding:26px 18px;
            border-radius:24px;
            text-align:center;
        }
        .error-box{
            white-space:pre-wrap;
            direction:ltr;
            background:#111827;
            color:#86efac;
            padding:18px;
            border-radius:18px;
            border:1px solid rgba(34,197,94,.18);
        }
        .footer{
            text-align:center;
            font-size:14px;
            margin-top:30px;
            color:var(--muted);
        }
        @media (max-width:1100px){
            .hero-grid,.video-layout,.featured-grid,.controls-grid,.strip{
                grid-template-columns:1fr 1fr;
            }
            .grid{grid-template-columns:1fr}
        }
        @media (max-width:800px){
            .hero-grid,.video-layout,.featured-grid,.controls-grid,.strip,.stats-grid{
                grid-template-columns:1fr;
            }
            .video-title{font-size:28px}
        }
    </style>
</head>
<body>
<div class="container">
    <section class="hero glass">
        <div class="topbar">
            <div class="brand">{{ site_name }}</div>
            <div style="display:flex;gap:10px;flex-wrap:wrap">
                <a class="top-btn" href="/">الرئيسية</a>
                <button class="top-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})">أعلى الصفحة</button>
            </div>
        </div>

        <div class="hero-grid">
            <div>
                <div class="hero-badges">
                    <div class="hero-badge">⚡ سريع</div>
                    <div class="hero-badge">🎬 فيديو داخل الموقع</div>
                    <div class="hero-badge">🔐 توكن محفوظ</div>
                    <div class="hero-badge">♻ يعيد الدخول فقط عند 401</div>
                </div>

                <h1 class="site-title">
                    {% if selected_item %}
                        {{ selected_item.title or site_name }}
                    {% else %}
                        {{ site_name }}
                    {% endif %}
                </h1>

                <p class="site-subtitle">{{ site_desc }}</p>

                <div class="hero-actions" style="justify-content:flex-start;margin-top:16px">
                    <a href="#content-area" class="btn main">ابدأ التصفح</a>
                    <button type="button" class="btn outline" onclick="copyHomeLink()">نسخ الرابط</button>
                </div>
            </div>

            <div class="panel glass">
                <div class="stats-grid">
                    <div class="glass strip-card">
                        <div>إجمالي المحتويات</div>
                        <div style="font-size:30px;font-weight:900">{{ stats.total }}</div>
                    </div>
                    <div class="glass strip-card">
                        <div>الفيديوهات</div>
                        <div style="font-size:30px;font-weight:900">{{ stats.videos }}</div>
                    </div>
                    <div class="glass strip-card">
                        <div>الملفات</div>
                        <div style="font-size:30px;font-weight:900">{{ stats.files }}</div>
                    </div>
                    <div class="glass strip-card">
                        <div>التحميلات</div>
                        <div style="font-size:30px;font-weight:900">{{ stats.downloads }}</div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    {% if error_message %}
        <section style="margin-top:22px">
            <div class="error-box">{{ error_message }}</div>
        </section>

    {% elif selected_item %}
        <section style="margin-top:22px" class="video-layout" id="content-area">
            <div class="player-card glass">
                <div class="player-wrap">
                    {% if embed_url %}
                        <iframe
                            src="{{ embed_url }}"
                            title="{{ selected_item.title }}"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                            allowfullscreen
                            referrerpolicy="strict-origin-when-cross-origin"></iframe>
                    {% else %}
                        <div class="player-placeholder">لا يوجد فيديو لهذا المحتوى</div>
                    {% endif %}
                    <div class="player-glow"></div>
                </div>

                <div class="player-content">
                    <h2 class="video-title">{{ selected_item.title }}</h2>

                    <div class="meta" style="justify-content:flex-start">
                        <span class="pill">📅 {{ selected_item.created_at or "" }}</span>
                        {% if selected_item.has_video %}<span class="pill">🎬 فيديو</span>{% endif %}
                        {% if selected_item.has_files %}<span class="pill">📄 ملفات</span>{% endif %}
                        {% if selected_item.can_download %}<span class="pill">⬇ تحميل</span>{% else %}<span class="pill">⛔ غير قابل</span>{% endif %}
                    </div>

                    <div class="video-desc">{{ selected_item_desc|safe }}</div>

                    <div class="btn-row">
                        <a class="btn main" href="/">رجوع للرئيسية</a>
                        {% if selected_item.link %}
                            <a class="btn outline" href="{{ selected_item.link }}" target="_blank" rel="noopener noreferrer">فتح المصدر</a>
                        {% endif %}
                        <button class="btn outline" type="button" onclick="copyCurrentPage()">نسخ رابط الصفحة</button>
                    </div>
                </div>
            </div>

            <div class="side-stack">
                <div class="side-card glass">
                    <h3>الملفات المرفقة</h3>
                    {% if selected_item.files and selected_item.files is iterable %}
                        {% for file in selected_item.files %}
                            <a class="btn outline" style="display:flex;margin-bottom:10px;justify-content:center" href="{{ file.get('media', '#') }}" target="_blank" rel="noopener noreferrer">📄 ملف {{ loop.index }}</a>
                        {% endfor %}
                    {% else %}
                        <div class="note">لا توجد ملفات مرفقة لهذا المحتوى.</div>
                    {% endif %}
                </div>

                <div class="side-card glass">
                    <h3>محتويات مشابهة</h3>
                    <div class="related-list">
                        {% for r in related %}
                            <a class="related-item" href="/?id={{ r.id }}">
                                {% if r.thumb %}
                                    <img class="related-thumb" src="{{ r.thumb }}" alt="{{ r.title }}">
                                {% else %}
                                    <div class="related-fallback">منصة شقير</div>
                                {% endif %}
                                <div>
                                    <div>{{ r.title }}</div>
                                    <div class="note">{{ r.created_at }}</div>
                                </div>
                            </a>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </section>

    {% else %}
        <section style="margin-top:22px">
            <div class="topbar" style="justify-content:space-between;margin-bottom:16px">
                <h2 style="margin:0">العناصر المميزة</h2>
                <div class="counter">أفضل 6 عناصر</div>
            </div>

            <div class="featured-grid">
                {% for item in featured %}
                    <a class="featured-card glass" href="/?id={{ item.id }}">
                        {% if item.thumb %}
                            <div class="featured-bg" style="background-image:url('{{ item.thumb }}')"></div>
                        {% else %}
                            <div class="featured-bg"></div>
                        {% endif %}
                        <div class="featured-overlay"></div>
                        <div class="featured-body">
                            <div class="meta" style="justify-content:flex-start">
                                <span class="pill">📅 {{ item.created_at or "" }}</span>
                                {% if item.has_video %}<span class="pill">🎬 فيديو</span>{% endif %}
                            </div>
                            <h3 class="featured-title">{{ item.title or "بدون عنوان" }}</h3>
                            <span class="btn main">فتح المحتوى</span>
                        </div>
                    </a>
                {% endfor %}
            </div>
        </section>

        <section style="margin-top:22px">
            <div class="controls glass">
                <div class="topbar" style="justify-content:space-between;margin-bottom:14px">
                    <h2 style="margin:0">البحث والفلترة</h2>
                    <div class="counter">العناصر الظاهرة: <span id="visibleCount">{{ items|length }}</span></div>
                </div>

                <div class="controls-grid">
                    <input type="text" id="searchInput" class="input" placeholder="ابحث بالعنوان أو الوصف أو التاريخ...">

                    <select id="filterType" class="select">
                        <option value="all">كل المحتوى</option>
                        <option value="video">فيديوهات فقط</option>
                        <option value="files">ملفات فقط</option>
                        <option value="downloadable">قابل للتحميل فقط</option>
                        <option value="no-video">بدون فيديو</option>
                    </select>

                    <select id="sortType" class="select">
                        <option value="newest">الأحدث أولًا</option>
                        <option value="oldest">الأقدم أولًا</option>
                        <option value="title-asc">العنوان أ → ي</option>
                        <option value="title-desc">العنوان ي → أ</option>
                    </select>

                    <button id="resetBtn" class="action-main" type="button">إعادة الضبط</button>
                    <button id="scrollTopBtn" class="action-alt" type="button">أعلى الصفحة</button>
                </div>
            </div>
        </section>

        <section style="margin-top:22px" id="content-area">
            <div class="topbar" style="justify-content:space-between;margin-bottom:16px">
                <h2 style="margin:0">كل المحتويات</h2>
                <div class="counter">بطاقات حديثة سريعة</div>
            </div>

            <div class="grid" id="cardsGrid">
                {% for item in items %}
                    <article
                        class="card glass content-card"
                        data-index="{{ loop.index0 }}"
                        data-search="{{ item.search_text }}"
                        data-title="{{ item.title_lower }}"
                        data-has-video="{{ '1' if item.has_video else '0' }}"
                        data-has-files="{{ '1' if item.has_files else '0' }}"
                        data-downloadable="{{ '1' if item.can_download else '0' }}"
                    >
                        <a href="/?id={{ item.id }}">
                            <div class="thumb">
                                {% if item.thumb %}
                                    <img src="{{ item.thumb }}" alt="{{ item.title or '' }}" loading="lazy">
                                {% else %}
                                    <div class="fallback">منصة شقير المجانية</div>
                                {% endif %}
                                <div class="thumb-top">
                                    <div class="thumb-badge">▶ عرض المحتوى</div>
                                    <div class="thumb-index">#{{ loop.index }}</div>
                                </div>
                            </div>

                            <div class="card-body">
                                <h3 class="card-title">{{ item.title or "بدون عنوان" }}</h3>

                                <div class="meta" style="justify-content:flex-start">
                                    <span class="pill">📅 {{ item.created_at or "" }}</span>
                                    {% if item.has_video %}<span class="pill">🎬 فيديو</span>{% endif %}
                                    {% if item.has_files %}<span class="pill">📄 ملفات</span>{% endif %}
                                    {% if item.can_download %}<span class="pill">⬇ تحميل</span>{% else %}<span class="pill">⛔ غير قابل</span>{% endif %}
                                </div>

                                <div class="card-desc">{{ item.desc_html|safe }}</div>

                                <div class="btn-row">
                                    <span class="btn main">عرض المحتوى</span>
                                    <span class="btn outline">صفحة مستقلة</span>
                                </div>
                            </div>
                        </a>
                    </article>
                {% endfor %}
            </div>

            <div class="empty-state glass" id="emptyState">لا توجد نتائج مطابقة للبحث الحالي.</div>
        </section>
    {% endif %}

    <div class="footer">جميع الحقوق محفوظة © {{ site_name }}</div>
</div>

<script>
function copyCurrentPage(){
    navigator.clipboard.writeText(window.location.href).then(() => {
        alert("تم نسخ رابط الصفحة");
    }).catch(() => {
        alert("تعذر نسخ الرابط");
    });
}

function copyHomeLink(){
    navigator.clipboard.writeText(window.location.origin + "/").then(() => {
        alert("تم نسخ رابط الموقع");
    }).catch(() => {
        alert("تعذر نسخ الرابط");
    });
}

const searchInput = document.getElementById("searchInput");
const filterType = document.getElementById("filterType");
const sortType = document.getElementById("sortType");
const resetBtn = document.getElementById("resetBtn");
const scrollTopBtn = document.getElementById("scrollTopBtn");
const cardsGrid = document.getElementById("cardsGrid");
const cards = Array.from(document.querySelectorAll(".content-card"));
const visibleCount = document.getElementById("visibleCount");
const emptyState = document.getElementById("emptyState");

function applyFilters(){
    if(!cards.length || !cardsGrid) return;

    const q = (searchInput?.value || "").trim().toLowerCase();
    const filter = filterType?.value || "all";
    const sort = sortType?.value || "newest";
    let visible = [];

    cards.forEach(card => {
        const text = card.dataset.search || "";
        const hasVideo = card.dataset.hasVideo === "1";
        const hasFiles = card.dataset.hasFiles === "1";
        const downloadable = card.dataset.downloadable === "1";
        let ok = true;

        if(q && !text.includes(q)) ok = false;
        if(filter === "video" && !hasVideo) ok = false;
        if(filter === "files" && !hasFiles) ok = false;
        if(filter === "downloadable" && !downloadable) ok = false;
        if(filter === "no-video" && hasVideo) ok = false;

        card.style.display = ok ? "" : "none";
        if(ok) visible.push(card);
    });

    visible.sort((a, b) => {
        const ai = parseInt(a.dataset.index || "0", 10);
        const bi = parseInt(b.dataset.index || "0", 10);
        const at = a.dataset.title || "";
        const bt = b.dataset.title || "";

        if(sort === "newest") return ai - bi;
        if(sort === "oldest") return bi - ai;
        if(sort === "title-asc") return at.localeCompare(bt, "ar");
        if(sort === "title-desc") return bt.localeCompare(at, "ar");
        return 0;
    });

    visible.forEach(card => cardsGrid.appendChild(card));

    if(visibleCount) visibleCount.textContent = visible.length;
    if(emptyState) emptyState.style.display = visible.length ? "none" : "block";
}

if(searchInput) searchInput.addEventListener("input", applyFilters);
if(filterType) filterType.addEventListener("change", applyFilters);
if(sortType) sortType.addEventListener("change", applyFilters);

if(resetBtn){
    resetBtn.addEventListener("click", () => {
        if(searchInput) searchInput.value = "";
        if(filterType) filterType.value = "all";
        if(sortType) sortType.value = "newest";
        applyFilters();
    });
}

if(scrollTopBtn){
    scrollTopBtn.addEventListener("click", () => {
        window.scrollTo({top:0, behavior:"smooth"});
    });
}

applyFilters();
</script>
</body>
</html>
'''


@app.route("/", methods=["GET"])
def index():
    selected_id = request.args.get("id", default=0, type=int)

    try:
        items = all_items()
    except Exception as e:
        return render_template_string(
            TEMPLATE,
            page_title=f"خطأ | {SITE_NAME}",
            site_name=SITE_NAME,
            site_desc=SITE_DESC,
            selected_item=None,
            items=[],
            stats={"total": 0, "videos": 0, "files": 0, "downloads": 0},
            related=[],
            embed_url="",
            selected_item_desc="",
            featured=[],
            error_message=str(e),
        ), 500

    selected_item = next((x for x in items if int(x.get("id", 0)) == selected_id), None)
    related = []

    if selected_item:
        sid = int(selected_item.get("id", 0))
        for item in items:
            if int(item.get("id", 0)) != sid:
                related.append({
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "created_at": item.get("created_at", ""),
                    "thumb": item.get("thumb_small", ""),
                })
            if len(related) >= 8:
                break

    return render_template_string(
        TEMPLATE,
        page_title=f"{selected_item.get('title')} | {SITE_NAME}" if selected_item else SITE_NAME,
        site_name=SITE_NAME,
        site_desc=SITE_DESC,
        selected_item=selected_item,
        items=items,
        stats=get_stats(items),
        related=related,
        embed_url=get_embed_url(selected_item),
        selected_item_desc=nl2br(selected_item.get("desc", "")) if selected_item else "",
        featured=items[:6],
        error_message="",
    )

# local only
# if __name__ == "__main__":
#     app.run(debug=Tr
