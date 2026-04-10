# -*- coding: utf-8 -*-
import sys
import subprocess
import html
import re
from urllib.parse import urlencode

# تثبيت requests تلقائيًا لو مش موجودة
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

from flask import Flask, request, render_template_string

app = Flask(__name__)

API_BASE = "https://api.golden-wave.me/api/website/blogs"
TOKEN = "YOUR_BEARER_TOKEN_HERE"


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


TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title|safe }}</title>
    <meta name="description" content="منصة شقير المجانية - مكتبة تعليمية بتصميم حديث وصفحات فيديو مستقلة داخل الموقع.">
    <style>
        :root{
            --bg:#07111f;
            --bg2:#0f172a;
            --card:rgba(255,255,255,.08);
            --card-solid:#ffffff;
            --text:#f8fafc;
            --muted:#cbd5e1;
            --line:rgba(255,255,255,.12);
            --blue:#2563eb;
            --cyan:#06b6d4;
            --green:#16a34a;
            --red:#dc2626;
            --shadow:0 20px 50px rgba(0,0,0,.25);
            --radius:26px;
        }

        *{box-sizing:border-box}
        html{scroll-behavior:smooth}
        body{
            margin:0;
            font-family:Tahoma,Arial,sans-serif;
            color:var(--text);
            background:
                radial-gradient(circle at top right, rgba(37,99,235,.22), transparent 26%),
                radial-gradient(circle at top left, rgba(6,182,212,.14), transparent 25%),
                linear-gradient(180deg, #020617, #07111f 35%, #0f172a 100%);
            min-height:100vh;
        }

        a{text-decoration:none;color:inherit}

        .container{
            width:min(1400px, 94%);
            margin:auto;
            padding:24px 0 50px;
        }

        .hero{
            background:linear-gradient(135deg, rgba(37,99,235,.92), rgba(6,182,212,.88), rgba(14,165,233,.78));
            border-radius:34px;
            padding:28px 22px;
            box-shadow:var(--shadow);
            position:relative;
            overflow:hidden;
            border:1px solid rgba(255,255,255,.14);
        }

        .hero:before,.hero:after{
            content:"";
            position:absolute;
            border-radius:50%;
            background:rgba(255,255,255,.09);
        }

        .hero:before{
            width:220px;height:220px;right:-40px;top:-70px;
        }

        .hero:after{
            width:170px;height:170px;left:-30px;bottom:-50px;
        }

        .hero-inner{position:relative;z-index:2}

        .topbar{
            display:flex;
            justify-content:space-between;
            gap:12px;
            align-items:center;
            flex-wrap:wrap;
            margin-bottom:14px;
        }

        .brand{
            display:inline-flex;
            align-items:center;
            gap:10px;
            background:rgba(255,255,255,.13);
            border:1px solid rgba(255,255,255,.18);
            padding:10px 16px;
            border-radius:999px;
            font-weight:700;
        }

        .top-actions{
            display:flex;
            gap:10px;
            flex-wrap:wrap;
        }

        .top-btn{
            border:0;
            cursor:pointer;
            background:rgba(255,255,255,.14);
            color:#fff;
            border:1px solid rgba(255,255,255,.18);
            border-radius:14px;
            padding:11px 15px;
            font-weight:700;
        }

        .site-title{
            margin:10px 0 8px;
            font-size:clamp(28px, 5vw, 48px);
            line-height:1.2;
            font-weight:800;
        }

        .site-subtitle{
            margin:0;
            max-width:900px;
            line-height:1.95;
            color:rgba(255,255,255,.95);
            font-size:16px;
        }

        .controls{
            margin-top:22px;
            background:var(--card);
            border:1px solid var(--line);
            border-radius:28px;
            box-shadow:var(--shadow);
            padding:18px;
            backdrop-filter:blur(10px);
        }

        .controls-row{
            display:grid;
            grid-template-columns:1.6fr 1fr 1fr auto;
            gap:12px;
        }

        .search-box,.select-box{
            width:100%;
            border-radius:16px;
            border:1px solid var(--line);
            background:rgba(255,255,255,.06);
            color:var(--text);
            padding:14px 16px;
            font-size:15px;
            outline:none;
        }

        .action-main{
            border:0;
            cursor:pointer;
            border-radius:16px;
            background:linear-gradient(135deg, var(--blue), var(--cyan));
            color:#fff;
            padding:14px 16px;
            font-weight:700;
        }

        .section-head{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:12px;
            flex-wrap:wrap;
            margin:24px 0 18px;
        }

        .section-head h2{
            margin:0;
            font-size:28px;
        }

        .counter{
            background:var(--card);
            border:1px solid var(--line);
            border-radius:999px;
            padding:10px 14px;
            color:var(--muted);
            font-size:14px;
        }

        .grid{
            display:grid;
            grid-template-columns:repeat(auto-fill,minmax(330px,1fr));
            gap:18px;
        }

        .card{
            background:var(--card);
            border:1px solid var(--line);
            border-radius:28px;
            overflow:hidden;
            box-shadow:var(--shadow);
            transition:.22s ease;
            backdrop-filter:blur(10px);
        }

        .card:hover{
            transform:translateY(-4px);
        }

        .thumb{
            position:relative;
            aspect-ratio:16/9;
            overflow:hidden;
            background:#000;
        }

        .thumb img{
            width:100%;
            height:100%;
            object-fit:cover;
            display:block;
        }

        .thumb .fallback{
            width:100%;
            height:100%;
            display:grid;
            place-items:center;
            background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.2));
            font-size:18px;
            font-weight:700;
        }

        .thumb-badge{
            position:absolute;
            top:14px;
            left:14px;
            background:rgba(220,38,38,.92);
            color:#fff;
            padding:8px 12px;
            border-radius:999px;
            font-size:12px;
            font-weight:700;
        }

        .card-body{
            padding:18px;
        }

        .card-title{
            margin:0 0 10px;
            font-size:22px;
            line-height:1.8;
            color:#fff;
        }

        .meta{
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            margin-bottom:12px;
        }

        .pill{
            display:inline-block;
            padding:8px 12px;
            border-radius:999px;
            font-size:12px;
            font-weight:700;
        }

        .pill.date{background:rgba(37,99,235,.16);color:#93c5fd}
        .pill.video{background:rgba(249,115,22,.16);color:#fdba74}
        .pill.file{background:rgba(14,165,233,.16);color:#7dd3fc}
        .pill.ok{background:rgba(22,163,74,.16);color:#86efac}
        .pill.no{background:rgba(220,38,38,.16);color:#fca5a5}

        .desc{
            color:var(--muted);
            line-height:1.95;
            font-size:15px;
            min-height:60px;
            margin-bottom:16px;
        }

        .btn-row{
            display:flex;
            gap:10px;
            flex-wrap:wrap;
        }

        .btn{
            display:inline-flex;
            align-items:center;
            justify-content:center;
            gap:8px;
            border-radius:16px;
            padding:12px 14px;
            font-size:14px;
            font-weight:700;
            transition:.2s ease;
        }

        .btn.primary{
            background:linear-gradient(135deg, var(--blue), var(--cyan));
            color:#fff;
        }

        .btn.secondary{
            background:rgba(255,255,255,.06);
            color:#fff;
            border:1px solid var(--line);
        }

        .btn:hover{transform:translateY(-2px)}

        .video-page{
            display:grid;
            grid-template-columns:2fr 1fr;
            gap:18px;
            margin-top:22px;
        }

        .player-card,.side-card{
            background:var(--card);
            border:1px solid var(--line);
            border-radius:30px;
            box-shadow:var(--shadow);
            backdrop-filter:blur(10px);
            overflow:hidden;
        }

        .player-wrap{
            position:relative;
            aspect-ratio:16/9;
            background:#000;
            overflow:hidden;
        }

        .player-wrap iframe{
            width:100%;
            height:100%;
            border:0;
            display:block;
        }

        .player-glow{
            position:absolute;
            inset:auto 0 0 0;
            height:100px;
            background:linear-gradient(to top, rgba(0,0,0,.45), transparent);
            pointer-events:none;
        }

        .player-content{
            padding:20px;
        }

        .video-title{
            margin:0 0 12px;
            font-size:30px;
            line-height:1.7;
        }

        .video-desc{
            color:var(--muted);
            line-height:2;
            font-size:16px;
            margin-bottom:18px;
        }

        .video-meta{
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            margin-bottom:18px;
        }

        .side-card{
            padding:18px;
        }

        .side-title{
            margin:0 0 14px;
            font-size:20px;
        }

        .file-box{
            display:block;
            background:rgba(255,255,255,.05);
            border:1px solid var(--line);
            border-radius:16px;
            padding:14px;
            margin-bottom:10px;
            color:#fff;
        }

        .note{
            color:var(--muted);
            font-size:14px;
            line-height:1.9;
        }

        .related-list{
            display:grid;
            gap:12px;
        }

        .related-item{
            display:grid;
            grid-template-columns:100px 1fr;
            gap:10px;
            background:rgba(255,255,255,.04);
            border:1px solid var(--line);
            border-radius:18px;
            padding:10px;
            align-items:center;
            transition:.2s ease;
        }

        .related-item:hover{
            transform:translateY(-2px);
        }

        .related-item img,.related-fallback{
            width:100px;
            height:64px;
            border-radius:12px;
            object-fit:cover;
            background:#000;
            display:block;
        }

        .related-fallback{
            display:grid;
            place-items:center;
            background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.2));
            color:#fff;
            font-size:12px;
            font-weight:700;
        }

        .related-title{
            font-size:14px;
            line-height:1.7;
            color:#fff;
            margin-bottom:6px;
        }

        .related-date{
            font-size:12px;
            color:var(--muted);
        }

        .empty-state{
            margin-top:18px;
            padding:28px 18px;
            text-align:center;
            border-radius:24px;
            background:var(--card);
            border:1px solid var(--line);
            color:var(--muted);
            display:none;
        }

        .footer{
            text-align:center;
            color:var(--muted);
            font-size:14px;
            margin-top:30px;
        }

        pre.error-box{
            background:#111;
            color:#0f0;
            padding:20px;
            border-radius:12px;
            direction:ltr;
            white-space:pre-wrap;
        }

        @media (max-width: 1100px){
            .video-page{
                grid-template-columns:1fr;
            }

            .controls-row{
                grid-template-columns:1fr 1fr;
            }
        }

        @media (max-width: 700px){
            .controls-row{
                grid-template-columns:1fr;
            }

            .grid{
                grid-template-columns:1fr;
            }

            .video-title{
                font-size:24px;
            }

            .card-title{
                font-size:20px;
            }
        }
    </style>
</head>
<body>
<div class="container">

    <section class="hero">
        <div class="hero-inner">
            <div class="topbar">
                <div class="brand">🎓 منصة شقير المجانية</div>
                <div class="top-actions">
                    <a class="top-btn" href="/">الرئيسية</a>
                    <button class="top-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})">أعلى الصفحة</button>
                </div>
            </div>

            <h1 class="site-title">
                {% if selected_item %}
                    {{ selected_item.title or "منصة شقير المجانية" }}
                {% else %}
                    منصة شقير المجانية
                {% endif %}
            </h1>

            <p class="site-subtitle">
                {% if selected_item %}
                    صفحة عرض مستقلة للمحتوى داخل الموقع، بتصميم مخصص للطالب بعيد عن شكل يوتيوب التقليدي، مع ملفات ومحتوى مشابه وتنظيم أفضل للمشاهدة.
                {% else %}
                    اختر أي بطاقة لفتح صفحة خاصة بها تحتوي على الفيديو داخل الموقع، والملفات المرفقة، ومحتويات مشابهة، بتصميم أقوى وأسهل للطالب.
                {% endif %}
            </p>
        </div>
    </section>

    {% if error_message %}
        <pre class="error-box">{{ error_message }}</pre>
    {% elif selected_item %}

        <section class="video-page">
            <div class="player-card">
                <div class="player-wrap">
                    {% if embed_url %}
                        <iframe
                            src="{{ embed_url }}"
                            title="{{ selected_item.title }}"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                            allowfullscreen
                            referrerpolicy="strict-origin-when-cross-origin">
                        </iframe>
                    {% else %}
                        <div style="width:100%;height:100%;display:grid;place-items:center;background:linear-gradient(135deg, rgba(37,99,235,.35), rgba(6,182,212,.2));font-weight:700">
                            لا يوجد فيديو لهذا المحتوى
                        </div>
                    {% endif %}
                    <div class="player-glow"></div>
                </div>

                <div class="player-content">
                    <h2 class="video-title">{{ selected_item.title }}</h2>

                    <div class="video-meta">
                        <span class="pill date">{{ selected_item.created_at or "" }}</span>

                        {% if selected_item.has_video %}
                            <span class="pill video">فيديو داخل الموقع</span>
                        {% endif %}

                        {% if selected_item.has_files %}
                            <span class="pill file">يحتوي ملفات</span>
                        {% endif %}

                        {% if selected_item.can_download %}
                            <span class="pill ok">قابل للتحميل</span>
                        {% else %}
                            <span class="pill no">غير قابل للتحميل</span>
                        {% endif %}
                    </div>

                    <div class="video-desc">{{ selected_item_desc|safe }}</div>

                    <div class="btn-row">
                        <a class="btn primary" href="/">رجوع للرئيسية</a>

                        {% if selected_item.link %}
                            <a class="btn secondary" target="_blank" rel="noopener noreferrer" href="{{ selected_item.link }}">
                                فتح المصدر
                            </a>
                        {% endif %}

                        <button class="btn secondary" onclick="copyCurrentPage()">نسخ رابط الصفحة</button>
                    </div>
                </div>
            </div>

            <div style="display:grid;gap:18px;">
                <div class="side-card">
                    <h3 class="side-title">الملفات المرفقة</h3>

                    {% if selected_item.files and selected_item.files is iterable %}
                        {% for file in selected_item.files %}
                            <a class="file-box" target="_blank" rel="noopener noreferrer" href="{{ file.get('media', '#') }}">
                                📄 ملف {{ loop.index }}
                            </a>
                        {% endfor %}
                    {% else %}
                        <div class="note">لا توجد ملفات مرفقة لهذا المحتوى.</div>
                    {% endif %}
                </div>

                <div class="side-card">
                    <h3 class="side-title">محتويات مشابهة</h3>

                    <div class="related-list">
                        {% for r in related %}
                            <a class="related-item" href="/?id={{ r.id }}">
                                {% if r.thumb %}
                                    <img src="{{ r.thumb }}" alt="{{ r.title or '' }}">
                                {% else %}
                                    <div class="related-fallback">منصة شقير</div>
                                {% endif %}

                                <div>
                                    <div class="related-title">{{ r.title or "" }}</div>
                                    <div class="related-date">{{ r.created_at or "" }}</div>
                                </div>
                            </a>
                        {% endfor %}
                    </div>
                </div>

                <div class="side-card">
                    <h3 class="side-title">ملاحظات</h3>
                    <div class="note">
                        تم تصميم هذه الصفحة لتكون واجهة تعليمية داخل الموقع بدل إرسال الطالب مباشرة إلى يوتيوب، مع الحفاظ على تشغيل الفيديو داخل المنصة نفسها.
                    </div>
                </div>
            </div>
        </section>

    {% else %}
        <section class="controls">
            <div class="controls-row">
                <input type="text" id="searchInput" class="search-box" placeholder="ابحث بالعنوان أو الوصف أو التاريخ...">

                <select id="filterType" class="select-box">
                    <option value="all">كل المحتوى</option>
                    <option value="video">فيديوهات فقط</option>
                    <option value="files">ملفات فقط</option>
                    <option value="downloadable">قابل للتحميل فقط</option>
                </select>

                <select id="sortType" class="select-box">
                    <option value="newest">الأحدث أولًا</option>
                    <option value="oldest">الأقدم أولًا</option>
                    <option value="title-asc">العنوان أ → ي</option>
                    <option value="title-desc">العنوان ي → أ</option>
                </select>

                <button class="action-main" id="resetBtn">إعادة الضبط</button>
            </div>
        </section>

        <div class="section-head">
            <h2>المحتويات</h2>
            <div class="counter">العناصر الظاهرة: <span id="visibleCount">{{ items|length }}</span></div>
        </div>

        <section class="grid" id="cardsGrid">
            {% for item in items %}
                <article
                    class="card content-card"
                    data-index="{{ loop.index0 }}"
                    data-search="{{ item.search_text }}"
                    data-title="{{ (item.title or '')|lower }}"
                    data-has-video="{{ '1' if item.has_video else '0' }}"
                    data-has-files="{{ '1' if item.has_files else '0' }}"
                    data-downloadable="{{ '1' if item.can_download else '0' }}"
                >
                    <a href="/?id={{ item.id }}">
                        <div class="thumb">
                            {% if item.thumb %}
                                <img src="{{ item.thumb }}" alt="{{ item.title or '' }}">
                                <div class="thumb-badge">▶ افتح صفحة الفيديو</div>
                            {% else %}
                                <div class="fallback">منصة شقير المجانية</div>
                            {% endif %}
                        </div>

                        <div class="card-body">
                            <h3 class="card-title">{{ item.title or "بدون عنوان" }}</h3>

                            <div class="meta">
                                <span class="pill date">{{ item.created_at or "" }}</span>

                                {% if item.has_video %}
                                    <span class="pill video">فيديو</span>
                                {% endif %}

                                {% if item.has_files %}
                                    <span class="pill file">ملفات</span>
                                {% endif %}

                                {% if item.can_download %}
                                    <span class="pill ok">تحميل</span>
                                {% else %}
                                    <span class="pill no">غير قابل</span>
                                {% endif %}
                            </div>

                            <div class="desc">{{ item.desc_html|safe }}</div>

                            <div class="btn-row">
                                <span class="btn primary">عرض المحتوى</span>
                                <span class="btn secondary">صفحة مستقلة</span>
                            </div>
                        </div>
                    </a>
                </article>
            {% endfor %}
        </section>

        <div class="empty-state" id="emptyState">لا توجد نتائج مطابقة للبحث الحالي.</div>
    {% endif %}

    <div class="footer">
        جميع الحقوق محفوظة © منصة شقير المجانية
    </div>
</div>

{% if not selected_item and not error_message %}
<script>
    const searchInput = document.getElementById('searchInput');
    const filterType = document.getElementById('filterType');
    const sortType = document.getElementById('sortType');
    const resetBtn = document.getElementById('resetBtn');
    const cardsGrid = document.getElementById('cardsGrid');
    const cards = Array.from(document.querySelectorAll('.content-card'));
    const visibleCount = document.getElementById('visibleCount');
    const emptyState = document.getElementById('emptyState');

    function applyFilters() {
        const q = (searchInput.value || '').trim().toLowerCase();
        const filter = filterType.value;
        const sort = sortType.value;

        let visible = [];

        cards.forEach(card => {
            const text = card.dataset.search || '';
            const hasVideo = card.dataset.hasVideo === '1';
            const hasFiles = card.dataset.hasFiles === '1';
            const downloadable = card.dataset.downloadable === '1';

            let ok = true;

            if (q && !text.includes(q)) ok = false;
            if (filter === 'video' && !hasVideo) ok = false;
            if (filter === 'files' && !hasFiles) ok = false;
            if (filter === 'downloadable' && !downloadable) ok = false;

            card.style.display = ok ? '' : 'none';
            if (ok) visible.push(card);
        });

        visible.sort((a, b) => {
            const ai = parseInt(a.dataset.index || '0', 10);
            const bi = parseInt(b.dataset.index || '0', 10);
            const at = a.dataset.title || '';
            const bt = b.dataset.title || '';

            if (sort === 'newest') return ai - bi;
            if (sort === 'oldest') return bi - ai;
            if (sort === 'title-asc') return at.localeCompare(bt, 'ar');
            if (sort === 'title-desc') return bt.localeCompare(at, 'ar');
            return 0;
        });

        visible.forEach(card => cardsGrid.appendChild(card));

        visibleCount.textContent = visible.length;
        emptyState.style.display = visible.length ? 'none' : 'block';
    }

    searchInput.addEventListener('input', applyFilters);
    filterType.addEventListener('change', applyFilters);
    sortType.addEventListener('change', applyFilters);

    resetBtn.addEventListener('click', () => {
        searchInput.value = '';
        filterType.value = 'all';
        sortType.value = 'newest';
        applyFilters();
    });

    applyFilters();
</script>
{% elif selected_item and not error_message %}
<script>
    function copyCurrentPage() {
        navigator.clipboard.writeText(window.location.href).then(() => {
            alert('تم نسخ رابط الصفحة');
        }).catch(() => {
            alert('تعذر نسخ الرابط');
        });
    }
</script>
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
            related=[],
            embed_url="",
            selected_item_desc="",
        )

    for item in items:
        item["thumb"] = (
            f"https://img.youtube.com/vi/{item['youtube_id']}/hqdefault.jpg"
            if item.get("youtube_id")
            else ""
        )
        item["desc_html"] = nl2br(item.get("desc", ""))

    selected_item = None
    if selected_id > 0:
        for it in items:
            if int(it.get("id", 0)) == selected_id:
                selected_item = it
                break

    embed_url = ""
    related = []
    selected_item_desc = ""

    if selected_item:
        if selected_item.get("youtube_id"):
            params = {"rel": 0, "modestbranding": 1, "controls": 1}
            embed_url = (
                f"https://www.youtube.com/embed/{selected_item['youtube_id']}?{urlencode(params)}"
            )

        selected_item_desc = nl2br(selected_item.get("desc", ""))

        for item in items:
            if int(item.get("id", 0)) != int(selected_item.get("id", 0)):
                related.append({
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "created_at": item.get("created_at", ""),
                    "thumb": (
                        f"https://img.youtube.com/vi/{item['youtube_id']}/mqdefault.jpg"
                        if item.get("youtube_id")
                        else ""
                    ),
                })
            if len(related) >= 6:
                break

    page_title = (
        f"{h(selected_item.get('title'))} | منصة شقير المجانية"
        if selected_item else
        "منصة شقير المجانية"
    )

    return render_template_string(
        TEMPLATE,
        page_title=page_title,
        error_message="",
        selected_item=selected_item,
        items=items,
        related=related,
        embed_url=embed_url,
        selected_item_desc=selected_item_desc,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
