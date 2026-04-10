# -*- coding: utf-8 -*-
import html
import re
import time
from functools import lru_cache
from urllib.parse import urlencode

import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

API_BASE = "https://api.golden-wave.me/api/website/blogs"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2FwaS5nb2xkZW4td2F2ZS5tZS9hcGkvd2Vic2l0ZS9sb2dpbiIsImlhdCI6MTc3NTc4NDA0MiwiZXhwIjoxODA3MzIwMDQyLCJuYmYiOjE3NzU3ODQwNDIsImp0aSI6ImZ5M1YwSHhKU1drYnZENTgiLCJzdWIiOiIxNDUzIiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyIsImxhc3RfbG9naW5fYXQiOiIyMDI2LTA0LTEwVDAxOjIwOjQyLjYwODAxOFoiLCJ0aW1lem9uZSI6IlVUQyJ9.iRhUyVKIEatvon0c5zvfaSXAxi8Tmcdz1djF6tPkJvw"
SITE_NAME = "منصة شقير المجانية"
SITE_DESC = "منصة تعليمية سريعة وحديثة بعرض فيديوهات داخل الموقع"
TIMEOUT = 20


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


def api_headers():
    return {
        "Accept": "application/json",
        "Accept-Language": "ar",
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {TOKEN}",
    }


def get_page(page: int):
    response = requests.get(
        f"{API_BASE}?page={page}",
        headers=api_headers(),
        timeout=TIMEOUT,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.json()


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
    params = urlencode({"rel": 0, "modestbranding": 1, "controls": 1})
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
            --bg:#07111f;--bg2:#0f172a;--card:rgba(255,255,255,.08);--card2:rgba(255,255,255,.05);
            --line:rgba(255,255,255,.12);--txt:#f8fafc;--muted:#cbd5e1;--blue:#2563eb;--cyan:#06b6d4;
            --violet:#7c3aed;--green:#16a34a;--red:#dc2626;--orange:#f97316;--shadow:0 22px 60px rgba(0,0,0,.30);
        }
        *{box-sizing:border-box} html{scroll-behavior:smooth}
        body{
            margin:0;font-family:Tahoma,Arial,sans-serif;color:var(--txt);
            background:radial-gradient(circle at top right, rgba(37,99,235,.22), transparent 24%),
            radial-gradient(circle at top left, rgba(124,58,237,.14), transparent 26%),
            linear-gradient(180deg, #020617, #07111f 40%, #0f172a 100%);
            min-height:100vh;
        }
        a{text-decoration:none;color:inherit}
        .container{width:min(1400px,94%);margin:auto;padding:24px 0 42px}
        .glass{background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow);backdrop-filter:blur(14px)}
        .hero{
            position:relative;overflow:hidden;border-radius:36px;padding:24px;
            background:linear-gradient(135deg, rgba(37,99,235,.96), rgba(6,182,212,.86), rgba(124,58,237,.80));
            border:1px solid rgba(255,255,255,.16);
        }
        .hero:before,.hero:after{content:"";position:absolute;border-radius:50%;background:rgba(255,255,255,.08)}
        .hero:before{width:240px;height:240px;top:-80px;right:-60px}
        .hero:after{width:190px;height:190px;left:-40px;bottom:-60px}
        .hero-inner{position:relative;z-index:2}
        .topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
        .brand{display:inline-flex;align-items:center;gap:10px;padding:12px 18px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.17);font-weight:800}
        .dot{width:12px;height:12px;border-radius:50%;background:#fff;box-shadow:0 0 16px rgba(255,255,255,.9)}
        .top-actions,.hero-badges,.hero-actions,.meta,.btn-row,.quick-pills{display:flex;gap:10px;flex-wrap:wrap}
        .top-btn,.btn,.action-main,.action-alt{border:0;cursor:pointer;border-radius:16px;padding:12px 16px;font-weight:800;transition:.22s ease}
        .top-btn{color:#fff;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.16)}
        .top-btn:hover,.btn:hover,.action-main:hover,.action-alt:hover{transform:translateY(-2px)}
        .hero-grid{display:grid;grid-template-columns:1.25fr .95fr;gap:18px;margin-top:18px}
        .site-title{margin:0;font-size:clamp(32px,5vw,58px);line-height:1.18;font-weight:900}
        .site-subtitle{margin:12px 0 0;line-height:2;font-size:16px;color:rgba(255,255,255,.96)}
        .hero-badge,.pill,.quick-pill{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;font-size:12px;font-weight:800}
        .hero-badge,.quick-pill{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.15)}
        .panel{padding:18px;border-radius:28px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.14)}
        .stats-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
        .stat{padding:18px;border-radius:22px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12)}
        .stat-label{font-size:13px;color:#e2e8f0}.stat-value{margin-top:8px;font-size:30px;font-weight:900}.stat-note{margin-top:6px;color:#dbeafe;font-size:12px}
        .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px}.btn.main{background:#fff;color:#0f172a}.btn.ghost{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.16)}
        .section{margin-top:22px}.strip{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
        .strip-card{padding:18px;border-radius:24px}.strip-title{font-size:14px;color:var(--muted)}.strip-number{margin-top:10px;font-size:32px;font-weight:900}.strip-desc{margin-top:8px;font-size:13px;line-height:1.8;color:var(--muted)}
        .section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:22px 0 16px}
        .section-head h2{margin:0;font-size:28px}.counter{padding:10px 14px;border-radius:999px;background:var(--card2);border:1px solid var(--line);font-size:14px;color:var(--muted)}
        .featured-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
        .featured-card{position:relative;overflow:hidden;min-height:260px;border-radius:28px;display:flex;align-items:flex-end}
        .featured-bg{position:absolute;inset:0;background-size:cover;background-position:center}.featured-overlay{position:absolute;inset:0;background:linear-gradient(180deg, rgba(0,0,0,.10), rgba(0,0,0,.82))}
        .featured-body{position:relative;z-index:2;padding:18px;width:100%}.featured-title{margin:0 0 10px;font-size:22px;line-height:1.7}
        .controls{padding:18px;border-radius:28px}.controls-grid{display:grid;grid-template-columns:1.5fr 1fr 1fr auto auto;gap:12px}
        .input,.select{width:100%;border-radius:16px;border:1px solid var(--line);background:rgba(255,255,255,.06);color:var(--txt);padding:14px 16px;outline:none}
        .input::placeholder{color:#94a3b8}.action-main{background:linear-gradient(135deg,var(--blue),var(--cyan));color:#fff}.action-alt{background:rgba(255,255,255,.06);color:#fff;border:1px solid var(--line)}
        .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px}.card{overflow:hidden;border-radius:28px;transition:.22s ease}.card:hover{transform:translateY(-5px)}
        .thumb{position:relative;aspect-ratio:16/9;overflow:hidden;background:#000}.thumb img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .3s ease}.card:hover .thumb img{transform:scale(1.04)}
        .fallback{width:100%;height:100%;display:grid;place-items:center;background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.22), rgba(124,58,237,.18));font-size:18px;font-weight:800}
        .thumb-top{position:absolute;top:14px;left:14px;right:14px;display:flex;justify-content:space-between;gap:10px}
        .thumb-badge,.thumb-index{padding:8px 12px;border-radius:999px;font-size:12px;font-weight:800}
        .thumb-badge{background:rgba(220,38,38,.92);color:#fff}.thumb-index{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.16)}
        .card-body{padding:18px}.card-title{margin:0 0 10px;font-size:22px;line-height:1.7}.card-desc{min-height:68px;margin-bottom:14px;color:var(--muted);line-height:1.95;font-size:15px}
        .pill.date{background:rgba(37,99,235,.16);color:#93c5fd}.pill.video{background:rgba(249,115,22,.16);color:#fdba74}.pill.file{background:rgba(14,165,233,.16);color:#7dd3fc}.pill.ok{background:rgba(22,163,74,.16);color:#86efac}.pill.no{background:rgba(220,38,38,.16);color:#fca5a5}
        .btn.soft{background:linear-gradient(135deg,var(--blue),var(--cyan));color:#fff}.btn.outline{background:rgba(255,255,255,.05);color:#fff;border:1px solid var(--line)}
        .video-layout{display:grid;grid-template-columns:2fr .95fr;gap:18px}.player-card,.side-card{border-radius:28px;overflow:hidden}
        .player-wrap{position:relative;aspect-ratio:16/9;background:#000}.player-wrap iframe{width:100%;height:100%;border:0;display:block}
        .player-placeholder{width:100%;height:100%;display:grid;place-items:center;background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.2));font-size:24px;font-weight:900}
        .player-glow{position:absolute;inset:auto 0 0 0;height:120px;background:linear-gradient(to top, rgba(0,0,0,.48), transparent)}
        .player-content{padding:22px}.video-title{margin:0 0 12px;font-size:34px;line-height:1.6}.video-desc{margin-bottom:18px;color:var(--muted);line-height:2;font-size:16px}
        .side-stack{display:grid;gap:18px}.side-card{padding:18px}.side-title{margin:0 0 14px;font-size:22px}
        .file-box{display:block;background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:16px;padding:14px;margin-bottom:10px;transition:.2s ease}
        .file-box:hover{transform:translateY(-2px);background:rgba(255,255,255,.08)}
        .related-list{display:grid;gap:12px}.related-item{display:grid;grid-template-columns:108px 1fr;gap:10px;padding:10px;border-radius:18px;background:rgba(255,255,255,.04);border:1px solid var(--line)}
        .related-thumb,.related-fallback{width:108px;height:68px;border-radius:14px;object-fit:cover;background:#000}
        .related-fallback{display:grid;place-items:center;background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.2));font-size:12px;font-weight:800}
        .related-title{font-size:14px;line-height:1.7;margin-bottom:6px}.related-date,.note,.footer{color:var(--muted)}
        .empty-state{display:none;margin-top:18px;padding:26px 18px;border-radius:24px;text-align:center}.error-box{white-space:pre-wrap;direction:ltr;background:#111827;color:#86efac;padding:18px;border-radius:18px;border:1px solid rgba(34,197,94,.18)}
        .footer{text-align:center;font-size:14px;margin-top:30px}
        @media (max-width:1100px){.hero-grid,.video-layout{grid-template-columns:1fr}.featured-grid{grid-template-columns:repeat(2,1fr)}.controls-grid{grid-template-columns:1fr 1fr 1fr}.strip{grid-template-columns:repeat(2,1fr)}}
        @media (max-width:800px){.controls-grid,.featured-grid,.grid,.strip{grid-template-columns:1fr}.site-title{font-size:clamp(28px,8vw,42px)}.video-title{font-size:28px}}
    </style>
</head>
<body>
<div class="container">
    <section class="hero">
        <div class="hero-inner">
            <div class="topbar">
                <div class="brand"><span class="dot"></span>{{ site_name }}</div>
                <div class="top-actions">
                    <a class="top-btn" href="/">الرئيسية</a>
                    <button class="top-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})">أعلى الصفحة</button>
                </div>
            </div>

            <div class="hero-grid">
                <div>
                    <div class="hero-badges">
                        <div class="hero-badge">⚡ سريع</div>
                        <div class="hero-badge">🎬 فيديو داخل الموقع</div>
                        <div class="hero-badge">📱 متجاوب</div>
                        <div class="hero-badge">🔎 بحث فوري</div>
                    </div>

                    <h1 class="site-title">{% if selected_item %}{{ selected_item.title or site_name }}{% else %}{{ site_name }}{% endif %}</h1>
                    <p class="site-subtitle">
                        {% if selected_item %}
                            صفحة مستقلة لعرض الفيديو والمحتوى والملفات داخل المنصة بشكل قوي وسريع.
                        {% else %}
                            {{ site_desc }} مع بطاقات حديثة وإحصائيات وبحث مباشر وفلترة وفرز بدون إعادة تحميل.
                        {% endif %}
                    </p>

                    <div class="hero-actions" style="margin-top:16px">
                        <a href="#content-area" class="btn main">ابدأ التصفح</a>
                        <button type="button" class="btn ghost" onclick="copyHomeLink()">نسخ الرابط</button>
                    </div>
                </div>

                <div class="panel">
                    <div class="stats-grid">
                        <div class="stat"><div class="stat-label">إجمالي المحتويات</div><div class="stat-value">{{ stats.total }}</div><div class="stat-note">كل العناصر المتاحة الآن</div></div>
                        <div class="stat"><div class="stat-label">الفيديوهات</div><div class="stat-value">{{ stats.videos }}</div><div class="stat-note">تشغيل مدمج داخل الموقع</div></div>
                        <div class="stat"><div class="stat-label">الملفات</div><div class="stat-value">{{ stats.files }}</div><div class="stat-note">عناصر بها مرفقات</div></div>
                        <div class="stat"><div class="stat-label">القابل للتحميل</div><div class="stat-value">{{ stats.downloads }}</div><div class="stat-note">تنزيل مباشر عندما يتوفر</div></div>
                    </div>
                    <div class="quick-pills" style="margin-top:12px">
                        <div class="quick-pill">🕒 {{ generated_at }}</div>
                        <div class="quick-pill">🚀 كاش 3 دقائق</div>
                        <div class="quick-pill">✨ واجهة حديثة</div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    {% if error_message %}
        <section class="section"><div class="error-box">{{ error_message }}</div></section>
    {% elif selected_item %}
        <section class="section">
            <div class="strip">
                <div class="strip-card glass"><div class="strip-title">رقم العنصر</div><div class="strip-number">{{ selected_item.id }}</div><div class="strip-desc">المعرف الداخلي للمحتوى</div></div>
                <div class="strip-card glass"><div class="strip-title">فيديو</div><div class="strip-number">{{ "نعم" if selected_item.has_video else "لا" }}</div><div class="strip-desc">تشغيل داخل المنصة</div></div>
                <div class="strip-card glass"><div class="strip-title">الملفات</div><div class="strip-number">{{ selected_item.files|length if selected_item.files else 0 }}</div><div class="strip-desc">عدد المرفقات</div></div>
                <div class="strip-card glass"><div class="strip-title">التحميل</div><div class="strip-number">{{ "نعم" if selected_item.can_download else "لا" }}</div><div class="strip-desc">حالة التحميل</div></div>
            </div>
        </section>

        <section class="section video-layout" id="content-area">
            <div class="player-card glass">
                <div class="player-wrap">
                    {% if embed_url %}
                        <iframe src="{{ embed_url }}" title="{{ selected_item.title }}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
                    {% else %}
                        <div class="player-placeholder">لا يوجد فيديو لهذا المحتوى</div>
                    {% endif %}
                    <div class="player-glow"></div>
                </div>

                <div class="player-content">
                    <h2 class="video-title">{{ selected_item.title }}</h2>
                    <div class="meta">
                        <span class="pill date">📅 {{ selected_item.created_at or "" }}</span>
                        {% if selected_item.has_video %}<span class="pill video">🎬 فيديو داخل الموقع</span>{% endif %}
                        {% if selected_item.has_files %}<span class="pill file">📄 يحتوي ملفات</span>{% endif %}
                        {% if selected_item.can_download %}<span class="pill ok">⬇ قابل للتحميل</span>{% else %}<span class="pill no">⛔ غير قابل للتحميل</span>{% endif %}
                    </div>
                    <div class="video-desc">{{ selected_item_desc|safe }}</div>
                    <div class="btn-row">
                        <a class="btn soft" href="/">رجوع للرئيسية</a>
                        {% if selected_item.link %}<a class="btn outline" href="{{ selected_item.link }}" target="_blank" rel="noopener noreferrer">فتح المصدر</a>{% endif %}
                        <button class="btn outline" type="button" onclick="copyCurrentPage()">نسخ رابط الصفحة</button>
                    </div>
                </div>
            </div>

            <div class="side-stack">
                <div class="side-card glass">
                    <h3 class="side-title">الملفات المرفقة</h3>
                    {% if selected_item.files and selected_item.files is iterable %}
                        {% for file in selected_item.files %}
                            <a class="file-box" href="{{ file.get('media', '#') }}" target="_blank" rel="noopener noreferrer">📄 ملف {{ loop.index }}</a>
                        {% endfor %}
                    {% else %}
                        <div class="note">لا توجد ملفات مرفقة لهذا المحتوى.</div>
                    {% endif %}
                </div>

                <div class="side-card glass">
                    <h3 class="side-title">محتويات مشابهة</h3>
                    <div class="related-list">
                        {% for r in related %}
                            <a class="related-item" href="/?id={{ r.id }}">
                                {% if r.thumb %}<img class="related-thumb" src="{{ r.thumb }}" alt="{{ r.title }}">{% else %}<div class="related-fallback">منصة شقير</div>{% endif %}
                                <div><div class="related-title">{{ r.title }}</div><div class="related-date">{{ r.created_at }}</div></div>
                            </a>
                        {% endfor %}
                    </div>
                </div>

                <div class="side-card glass">
                    <h3 class="side-title">ملاحظات</h3>
                    <div class="note">هذه النسخة معاد كتابتها لتكون أخف وأسرع في Vercel مع كاش وتقليل الزوائد.</div>
                </div>
            </div>
        </section>
    {% else %}
        <section class="section">
            <div class="strip">
                <div class="strip-card glass"><div class="strip-title">إجمالي العناصر</div><div class="strip-number">{{ stats.total }}</div><div class="strip-desc">كل ما تم جلبه من المصدر</div></div>
                <div class="strip-card glass"><div class="strip-title">الفيديوهات</div><div class="strip-number">{{ stats.videos }}</div><div class="strip-desc">عناصر فيها تشغيل مباشر</div></div>
                <div class="strip-card glass"><div class="strip-title">الملفات</div><div class="strip-number">{{ stats.files }}</div><div class="strip-desc">عناصر تحتوي مرفقات</div></div>
                <div class="strip-card glass"><div class="strip-title">التحميلات</div><div class="strip-number">{{ stats.downloads }}</div><div class="strip-desc">عناصر قابلة للتنزيل</div></div>
            </div>
        </section>

        <section class="section">
            <div class="section-head"><h2>العناصر المميزة</h2><div class="counter">أفضل 6 عناصر في الواجهة</div></div>
            <div class="featured-grid">
                {% for item in featured %}
                    <a class="featured-card glass" href="/?id={{ item.id }}">
                        {% if item.thumb %}<div class="featured-bg" style="background-image:url('{{ item.thumb }}')"></div>{% else %}<div class="featured-bg" style="background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.22), rgba(124,58,237,.18))"></div>{% endif %}
                        <div class="featured-overlay"></div>
                        <div class="featured-body">
                            <div class="meta">
                                <span class="pill date">📅 {{ item.created_at or "" }}</span>
                                {% if item.has_video %}<span class="pill video">🎬 فيديو</span>{% endif %}
                                {% if item.has_files %}<span class="pill file">📄 ملفات</span>{% endif %}
                            </div>
                            <h3 class="featured-title">{{ item.title or "بدون عنوان" }}</h3>
                            <span class="btn main">فتح المحتوى</span>
                        </div>
                    </a>
                {% endfor %}
            </div>
        </section>

        <section class="section">
            <div class="controls glass">
                <div class="section-head" style="margin:0 0 14px">
                    <h2>البحث والفلترة</h2>
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

        <section class="section" id="content-area">
            <div class="section-head"><h2>كل المحتويات</h2><div class="counter">بطاقات حديثة سريعة</div></div>
            <div class="grid" id="cardsGrid">
                {% for item in items %}
                    <article class="card glass content-card" data-index="{{ loop.index0 }}" data-search="{{ item.search_text }}" data-title="{{ item.title_lower }}" data-has-video="{{ '1' if item.has_video else '0' }}" data-has-files="{{ '1' if item.has_files else '0' }}" data-downloadable="{{ '1' if item.can_download else '0' }}">
                        <a href="/?id={{ item.id }}">
                            <div class="thumb">
                                {% if item.thumb %}<img src="{{ item.thumb }}" alt="{{ item.title or '' }}" loading="lazy">{% else %}<div class="fallback">منصة شقير المجانية</div>{% endif %}
                                <div class="thumb-top"><div class="thumb-badge">▶ عرض المحتوى</div><div class="thumb-index">#{{ loop.index }}</div></div>
                            </div>
                            <div class="card-body">
                                <h3 class="card-title">{{ item.title or "بدون عنوان" }}</h3>
                                <div class="meta">
                                    <span class="pill date">📅 {{ item.created_at or "" }}</span>
                                    {% if item.has_video %}<span class="pill video">🎬 فيديو</span>{% endif %}
                                    {% if item.has_files %}<span class="pill file">📄 ملفات</span>{% endif %}
                                    {% if item.can_download %}<span class="pill ok">⬇ تحميل</span>{% else %}<span class="pill no">⛔ غير قابل</span>{% endif %}
                                </div>
                                <div class="card-desc">{{ item.desc_html|safe }}</div>
                                <div class="btn-row"><span class="btn soft">عرض المحتوى</span><span class="btn outline">صفحة مستقلة</span></div>
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
    navigator.clipboard.writeText(window.location.href).then(() => alert("تم نسخ رابط الصفحة")).catch(() => alert("تعذر نسخ الرابط"));
}
function copyHomeLink(){
    navigator.clipboard.writeText(window.location.origin + "/").then(() => alert("تم نسخ رابط الموقع")).catch(() => alert("تعذر نسخ الرابط"));
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
    scrollTopBtn.addEventListener("click", () => window.scrollTo({top:0, behavior:"smooth"}));
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
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
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
        generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        error_message="",
    )

# local only
# if __name__ == "__main__":
#     app.run(debug=True)

