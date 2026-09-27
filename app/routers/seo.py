from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database

router = APIRouter(tags=["SEO & Sitemaps"])

BASE_URL = "https://cfsi.co.in"

@router.get("/robots.txt", response_class=Response)
async def get_robots_txt(request: Request):
    """Generates standard crawler directives allowing indexing of public education pages."""
    host = request.base_url._url.rstrip("/") if request else BASE_URL
    robots_content = f"""User-agent: *
Allow: /
Allow: /about
Allow: /courses
Allow: /courses/*
Allow: /news
Allow: /gallery/images
Allow: /gallery/videos
Allow: /contact

# Disallow private dashboards and internal tools
Disallow: /dashboard
Disallow: /dashboard/*
Disallow: /student-data
Disallow: /attendance
Disallow: /attendance/*
Disallow: /profile
Disallow: /teacher/*
Disallow: /leader/*
Disallow: /student/dashboard
Disallow: /api/*

Crawl-delay: 1

Sitemap: {host}/sitemap.xml
"""
    return Response(content=robots_content.strip(), media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response)
async def get_sitemap_xml(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generates dynamic Google-compliant XML sitemap.
    Automatically fetches active courses and news articles from MongoDB.
    """
    host = BASE_URL
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{host}/", "priority": "1.0", "changefreq": "daily", "lastmod": today_iso},
        {"loc": f"{host}/courses", "priority": "0.9", "changefreq": "weekly", "lastmod": today_iso},
        {"loc": f"{host}/about", "priority": "0.8", "changefreq": "monthly", "lastmod": today_iso},
        {"loc": f"{host}/news", "priority": "0.9", "changefreq": "daily", "lastmod": today_iso},
        {"loc": f"{host}/gallery/images", "priority": "0.7", "changefreq": "weekly", "lastmod": today_iso},
        {"loc": f"{host}/gallery/videos", "priority": "0.7", "changefreq": "weekly", "lastmod": today_iso},
        {"loc": f"{host}/contact", "priority": "0.8", "changefreq": "monthly", "lastmod": today_iso},
    ]

    # Fetch dynamic courses
    try:
        courses_cursor = db.courses.find()
        async for c in courses_cursor:
            slug = c.get("slug") or c.get("id") or str(c.get("_id"))
            if slug:
                urls.append({
                    "loc": f"{host}/courses/{slug}",
                    "priority": "0.85",
                    "changefreq": "weekly",
                    "lastmod": today_iso
                })
    except Exception:
        pass

    # Fetch dynamic news articles
    try:
        news_cursor = db.news_posts.find().sort("date", -1).limit(50)
        async for post in news_cursor:
            post_id = post.get("id") or str(post.get("_id"))
            if post_id:
                urls.append({
                    "loc": f"{host}/news?id={post_id}",
                    "priority": "0.75",
                    "changefreq": "weekly",
                    "lastmod": today_iso
                })
    except Exception:
        pass

    # Build XML
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{u["loc"]}</loc>')
        xml_lines.append(f'    <lastmod>{u["lastmod"]}</lastmod>')
        xml_lines.append(f'    <changefreq>{u["changefreq"]}</changefreq>')
        xml_lines.append(f'    <priority>{u["priority"]}</priority>')
        xml_lines.append('  </url>')
    xml_lines.append('</urlset>')

    return Response(content="\n".join(xml_lines), media_type="application/xml")
