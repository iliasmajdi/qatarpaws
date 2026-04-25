#!/usr/bin/env python3
"""
QatarPaws v2 master rebuild.

Reads existing HTML pages, extracts structured business data,
and emits new-design markup across:
  - /index.html + /ar/index.html
  - /<category>/index.html + /ar/<category>/index.html   (22 files)
  - /business/*.html + /ar/business/*.html               (406 files)
  - /about.html + /ar/about.html
  - /blog/index.html + /ar/blog/index.html
  - /list-your-business.html + /ar/list-your-business.html   (new)
  - /sitemap.xml                                         (regenerated)

Run from repo root: `python scripts/rebuild_site.py`

Zero-cost constraint: every asset referenced is either local or a free service.
"""

from __future__ import annotations
import html as htmllib
import json
import os
import re
import sys
import glob
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

GA_ID = "G-Y7EYH2SNTV"
GSC_VERIFICATION = "5W6O91g8x0DMRozumfcRBeyeddZUbQ9ZIKpLukY6bIg"
SITE = "https://qatarpaws.com"
BUILD_DATE = date.today().isoformat()

# ---------- CATEGORY METADATA ------------------------------------------------

CATS = [
    dict(slug="vets",                en="Veterinary Clinics",        ar="العيادات البيطرية",
         tone="vet",   en_unit="CLINICS",  ar_unit="عيادة",
         en_tags=["EMERGENCY","SURGERY","VACCINATION"],
         ar_tags=["طوارئ","جراحة","تطعيم"],
         en_tag="Find trusted vets and animal hospitals across Qatar.",
         ar_tag="ابحث عن عيادات بيطرية ومستشفيات حيوانات موثوقة في قطر."),
    dict(slug="pet-shops",           en="Pet Shops & Stores",        ar="متاجر الحيوانات الأليفة",
         tone="shop",  en_unit="STORES",   ar_unit="متجر",
         en_tags=["FOOD","TOYS","ACCESSORIES"],
         ar_tags=["طعام","ألعاب","إكسسوارات"],
         en_tag="Pet food, supplies, and specialty stores in Qatar.",
         ar_tag="طعام ومستلزمات وإكسسوارات الحيوانات الأليفة في قطر."),
    dict(slug="grooming",            en="Pet Grooming",              ar="العناية بالحيوانات",
         tone="groom", en_unit="SALONS",   ar_unit="صالون",
         en_tags=["BATH","TRIM","MOBILE"],
         ar_tags=["استحمام","قص","متنقل"],
         en_tag="Salons and mobile grooming services for cats and dogs.",
         ar_tag="صالونات وخدمات عناية متنقلة للقطط والكلاب."),
    dict(slug="boarding",            en="Pet Boarding & Daycare",    ar="إيواء الحيوانات",
         tone="stay",  en_unit="HOTELS",   ar_unit="مركز",
         en_tags=["OVERNIGHT","DAYCARE","WALKS"],
         ar_tags=["مبيت","رعاية نهارية","مشي"],
         en_tag="Pet hotels and daycare while you travel or work.",
         ar_tag="فنادق ورعاية نهارية للحيوانات الأليفة."),
    dict(slug="pet-sitting",         en="Pet Sitting",               ar="رعاية الحيوانات",
         tone="sit",   en_unit="SERVICES", ar_unit="خدمة",
         en_tags=["IN-HOME","WALKS","FEEDING"],
         ar_tags=["في المنزل","مشي","إطعام"],
         en_tag="In-home pet sitters across Qatar.",
         ar_tag="مربّيات وخدمات رعاية في المنزل في قطر."),
    dict(slug="rescue",              en="Rescue & Adoption",         ar="الإنقاذ والتبني",
         tone="rescue",en_unit="SHELTERS", ar_unit="مأوى",
         en_tags=["ADOPTION","FOSTER","TRAP-NEUTER"],
         ar_tags=["تبنّي","احتضان","تعقيم"],
         en_tag="Adoption shelters and animal welfare groups.",
         ar_tag="مآوٍ ومنظّمات تبنّي ورعاية الحيوانات."),
    dict(slug="relocation",          en="Pet Relocation",            ar="نقل الحيوانات",
         tone="move",  en_unit="AGENTS",   ar_unit="وكيل",
         en_tags=["IMPORT","EXPORT","PAPERWORK"],
         ar_tags=["استيراد","تصدير","أوراق"],
         en_tag="Moving to or from Qatar with a pet — import/export specialists.",
         ar_tag="متخصّصون في نقل الحيوانات من وإلى قطر."),
    dict(slug="pet-friendly-cafes",  en="Pet-Friendly Cafés",        ar="مقاهي صديقة للحيوانات",
         tone="cafe",  en_unit="SPOTS",    ar_unit="مقهى",
         en_tags=["PATIO","WATER BOWLS","OUTDOOR"],
         ar_tags=["تراس","مياه","خارجي"],
         en_tag="Cafés where dogs are welcome in Doha and beyond.",
         ar_tag="مقاهٍ ترحّب بالكلاب في الدوحة وحولها."),
    dict(slug="pet-friendly-hotels", en="Pet-Friendly Hotels",       ar="فنادق صديقة للحيوانات",
         tone="stay",  en_unit="STAYS",    ar_unit="فندق",
         en_tags=["PET-FRIENDLY","RESORT","LUXURY"],
         ar_tags=["صديق للحيوان","منتجع","فاخر"],
         en_tag="Hotels and resorts that welcome pets.",
         ar_tag="فنادق ومنتجعات ترحّب بالحيوانات الأليفة."),
    dict(slug="pet-friendly-parks",  en="Parks & Outdoor",           ar="حدائق ومتنزهات",
         tone="park",  en_unit="AREAS",    ar_unit="حديقة",
         en_tags=["OFF-LEASH","WALKS","OUTDOOR"],
         ar_tags=["بدون مقود","مشي","خارجي"],
         en_tag="Parks and outdoor areas for pet walks and play.",
         ar_tag="حدائق ومناطق مفتوحة للمشي واللعب."),
    dict(slug="training",            en="Training",                  ar="تدريب",
         tone="train", en_unit="TRAINERS", ar_unit="مدرّب",
         en_tags=["OBEDIENCE","PUPPIES","BEHAVIOR"],
         ar_tags=["طاعة","جراء","سلوك"],
         en_tag="Professional dog trainers and behavior specialists.",
         ar_tag="مدرّبو كلاب ومتخصّصون في السلوك."),
]
CAT_BY_SLUG = {c["slug"]: c for c in CATS}
CAT_BY_EN_LABEL = {c["en"]: c for c in CATS}
CAT_BY_AR_LABEL = {c["ar"]: c for c in CATS}

# ---------- UI STRINGS -------------------------------------------------------

UI = {
    "en": {
        "nav_guide":"Guide", "nav_cats":"Categories", "nav_journal":"Journal",
        "nav_map":"Map", "nav_lang":"العربية", "nav_list":"List your business",
        "nav_toggle":"Open menu",
        "hero_eyebrow":"Qatar's pet directory",  # suffix added dynamically "· 267 places"
        "hero_h1_a":"Where", "hero_h1_em":"good boys", "hero_h1_amp":"& girls",
        "hero_h1_b":"go in Qatar.",
        "hero_lead":"A curated guide to every vet, groomer, boarder, café and rescue in the country — verified, mapped, and bilingual.",
        "search_placeholder":"Search a vet, neighborhood, or service…",
        "search_go":"Find",
        "popular":"Popular",
        "stat_places":"Verified places", "stat_cats":"Categories",
        "stat_lang":"AR · EN", "stat_lang_l":"Fully bilingual",
        "stat_year":"2026", "stat_year_l":"Updated weekly",
        "rail_eyebrow":"Browse by service", "rail_h2":"Everywhere your pet needs to be.",
        "rail_more":"View all categories",
        "editorial_eyebrow":"The QatarPaws Journal",
        "editorial_h2":"Collections, curated by locals.",
        "editorial_more":"All collections",
        "near_eyebrow":"Top rated this month",
        "near_h2":"Verified places, near you.",
        "near_more":"See all",
        "filter_all":"All", "filter_open":"Open now", "filter_rated":"Rated 4.5+",
        "guide_eyebrow":"Not sure where to start?",
        "guide_h2_a":"Pick the right vet", "guide_h2_em":"in under a minute.",
        "guide_p":"Our directory ranks clinics by reviews and distance — not who paid. No sign-up, fully bilingual, free forever.",
        "guide_cta1":"Browse vets", "guide_cta2":"How we rank",
        "compare_h":"Clinic", "compare_h2":"Rating",
        "foot_dir":"Directory", "foot_journal":"Journal", "foot_business":"Business",
        "foot_blurb":"An independent, bilingual directory of every pet service in Qatar — made in Doha, updated weekly, free to use.",
        "foot_list":"List your place", "foot_about":"About", "foot_contact":"Contact",
        "foot_blog":"Blog", "foot_home":"Home",
        "foot_bottom_l":"© 2026 QATARPAWS · DOHA, QATAR",
        "foot_bottom_r":"EN · العربية",
        "bc_home":"Home",
        "biz_call":"Call now", "biz_dir":"Get directions", "biz_web":"Visit website",
        "biz_photos":"Photos", "biz_reviews":"What visitors say",
        "biz_similar":"Similar places nearby",
        "biz_more_google":"See more reviews on Google",
        "biz_address":"Address", "biz_phone":"Phone",
        "biz_rating":"Rating",
        "photo_credit":"Photo via Google Maps",
        "page_results":"results",
        "top_rated":"Top rated",
        "editors_pick":"Editor's pick",
        "verified":"Verified",
        "view_details":"View details",
        "call_dir":"Call & directions",
        "about_h1":"About QatarPaws",
        "about_lead":"Qatar's independent pet services directory.",
        "blog_h1":"Journal",
        "blog_lead":"Guides and stories from Qatar's pet community.",
        "blog_soon_h":"Coming soon",
        "blog_soon_p":"We're working on pet care guides, interviews, and newcomer tips tailored to Qatar.",
        "list_h1":"List your business on QatarPaws",
        "list_lead":"Free listing, bilingual, forever. Built for local businesses that care for Qatar's pets.",
        "list_cta":"Send us your details",
        "list_mail_subject":"QatarPaws listing request",
        "map_chip_a":"Showing top places", "map_chip_b":"Qatar-wide",
        "popular_tags": ["24-hour vets","Pet-friendly hotels","Mobile grooming","Relocation","Rescue & adoption"],
    },
    "ar": {
        "nav_guide":"الدليل", "nav_cats":"الفئات", "nav_journal":"المدونة",
        "nav_map":"الخريطة", "nav_lang":"English", "nav_list":"أضف نشاطك",
        "nav_toggle":"فتح القائمة",
        "hero_eyebrow":"دليل قطر للحيوانات الأليفة",
        "hero_h1_a":"دليل قطر", "hero_h1_em":"الكامل", "hero_h1_amp":"لكلّ",
        "hero_h1_b":"ما يخصّ حيوانك.",
        "hero_lead":"دليل مختار بعناية لكلّ طبيب بيطري، ومصفّف، وفندق حيوانات، ومقهى، ومأوى في قطر — موثّق، ومفهرس، وثنائي اللغة.",
        "search_placeholder":"ابحث عن طبيب بيطري، حي، أو خدمة…",
        "search_go":"بحث",
        "popular":"الأكثر بحثًا",
        "stat_places":"أماكن موثّقة", "stat_cats":"فئات",
        "stat_lang":"AR · EN", "stat_lang_l":"ثنائي اللغة",
        "stat_year":"2026", "stat_year_l":"يُحدَّث أسبوعيًا",
        "rail_eyebrow":"تصفّح حسب الخدمة", "rail_h2":"كلّ ما يحتاجه حيوانك في مكان واحد.",
        "rail_more":"كلّ الفئات",
        "editorial_eyebrow":"مجلّة قطر بوز",
        "editorial_h2":"مجموعات مختارة من سكّان المحلّ.",
        "editorial_more":"كلّ المجموعات",
        "near_eyebrow":"الأعلى تقييمًا هذا الشهر",
        "near_h2":"أماكن موثّقة، قريبة منك.",
        "near_more":"شاهد الكل",
        "filter_all":"الكل", "filter_open":"مفتوح الآن", "filter_rated":"+4.5",
        "guide_eyebrow":"لست متأكّدًا من أين تبدأ؟",
        "guide_h2_a":"اختر الطبيب البيطري المناسب", "guide_h2_em":"في أقل من دقيقة.",
        "guide_p":"دليلنا يرتّب العيادات حسب التقييمات والمسافة — لا حسب من دفع. بدون تسجيل، بلغتين، مجاني إلى الأبد.",
        "guide_cta1":"تصفّح العيادات", "guide_cta2":"آلية الترتيب",
        "compare_h":"العيادة", "compare_h2":"التقييم",
        "foot_dir":"الدليل", "foot_journal":"المدونة", "foot_business":"للأعمال",
        "foot_blurb":"دليل مستقل وثنائي اللغة لكلّ خدمة حيوانات في قطر — صُنع في الدوحة، ويُحدَّث أسبوعيًا، مجاني.",
        "foot_list":"أضف نشاطك", "foot_about":"من نحن", "foot_contact":"تواصل",
        "foot_blog":"المدونة", "foot_home":"الرئيسية",
        "foot_bottom_l":"© 2026 قطر بوز · الدوحة، قطر",
        "foot_bottom_r":"العربية · EN",
        "bc_home":"الرئيسية",
        "biz_call":"اتّصل الآن", "biz_dir":"الاتجاهات", "biz_web":"زيارة الموقع",
        "biz_photos":"الصور", "biz_reviews":"ماذا يقول الزوّار",
        "biz_similar":"أماكن مشابهة قريبة",
        "biz_more_google":"المزيد من التقييمات على جوجل",
        "biz_address":"العنوان", "biz_phone":"الهاتف",
        "biz_rating":"التقييم",
        "photo_credit":"الصورة من خرائط جوجل",
        "page_results":"نتيجة",
        "top_rated":"الأعلى تقييمًا",
        "editors_pick":"اختيار المحرّر",
        "verified":"موثّق",
        "view_details":"التفاصيل",
        "call_dir":"اتّصال واتجاهات",
        "about_h1":"عن قطر بوز",
        "about_lead":"دليل قطر المستقل لخدمات الحيوانات الأليفة.",
        "blog_h1":"المجلّة",
        "blog_lead":"أدلّة وقصص من مجتمع الحيوانات الأليفة في قطر.",
        "blog_soon_h":"قريبًا",
        "blog_soon_p":"نعمل على أدلّة عناية بالحيوانات، ومقابلات، ونصائح للقادمين الجدد، مصمّمة لقطر.",
        "list_h1":"أضف نشاطك إلى قطر بوز",
        "list_lead":"إدراج مجاني، ثنائي اللغة، إلى الأبد. مصمّم للأنشطة المحلّية التي تهتمّ بحيوانات قطر.",
        "list_cta":"أرسل لنا تفاصيلك",
        "list_mail_subject":"طلب إدراج على قطر بوز",
        "map_chip_a":"أفضل الأماكن", "map_chip_b":"جميع أنحاء قطر",
        "popular_tags": ["طوارئ بيطرية 24/7","فنادق ترحّب بالحيوانات","عناية متنقلة","نقل الحيوانات","مآوٍ وتبنّي"],
    },
}

# ---------- JOURNAL (static stub copy) --------------------------------------

JOURNAL = {
    "en": [
        dict(cls="fa", kicker="Issue №01 · Guide", count="12 PLACES",
             h="The most-trusted 24-hour vets in Doha, ranked by reviewers who've actually been there at 3 a.m.",
             p="After-hours clinics from West Bay to Al Wakrah, with response times and on-call specialists.",
             href="/vets/"),
        dict(cls="fb", kicker="Weekend · Food", count="8 CAFÉS",
             h="Where to brunch with your dog on a Friday in Doha.",
             p="Shaded patios, water bowls, and a cortado for you.",
             href="/pet-friendly-cafes/"),
        dict(cls="fc", kicker="Newcomer", count="14 PROS",
             h="Relocating to Qatar with a pet? Start here.",
             p="Import permits, approved airlines, and the vets who handle the paperwork.",
             href="/relocation/"),
    ],
    "ar": [
        dict(cls="fa", kicker="العدد ١ · دليل", count="١٢ مكانًا",
             h="أكثر العيادات البيطرية موثوقية لخدمة الطوارئ على مدار الساعة في الدوحة.",
             p="عيادات تفتح بعد منتصف الليل من الخليج الغربي إلى الوكرة، مع أوقات الاستجابة والأخصّائيين.",
             href="/ar/vets/"),
        dict(cls="fb", kicker="عطلة · طعام", count="٨ مقاهٍ",
             h="أين تفطر مع كلبك يوم الجمعة في الدوحة.",
             p="تراسات مظلّلة، ومياه جاهزة، وقهوة لذيذة لك.",
             href="/ar/pet-friendly-cafes/"),
        dict(cls="fc", kicker="للقادمين الجدد", count="١٤ خبيرًا",
             h="هل تنتقل إلى قطر مع حيوانك الأليف؟ ابدأ من هنا.",
             p="تصاريح الاستيراد، وشركات الطيران المعتمدة، والأطبّاء الذين يتولّون الأوراق.",
             href="/ar/relocation/"),
    ],
}

# ---------- SHARED SVG ICONS (inline, small) ---------------------------------

SVG = {
    "paw": """<svg width="30" height="30" viewBox="0 0 40 40" fill="none" aria-hidden="true">
<circle cx="20" cy="20" r="19" fill="#141210"/>
<g fill="#F6F1E8">
<ellipse cx="13" cy="15.5" rx="2.6" ry="3.4"/>
<ellipse cx="20" cy="12.5" rx="2.6" ry="3.4"/>
<ellipse cx="27" cy="15.5" rx="2.6" ry="3.4"/>
<ellipse cx="30.5" cy="22" rx="2.3" ry="3"/>
<path d="M20 18c-5 0-8.5 3.6-8.5 7.6 0 2.8 2.2 4.4 5 4.4 1.7 0 2.5-.7 3.5-.7s1.8.7 3.5.7c2.8 0 5-1.6 5-4.4 0-4-3.5-7.6-8.5-7.6z"/>
</g>
<circle cx="30" cy="11" r="1.4" fill="#7B1E1E"/>
</svg>""",
    "search": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
    "pin": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 1118 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "pin_lg": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 1118 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "phone": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>',
    "star": '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l3 7h7l-5.5 4.5L18 21l-6-4.5L6 21l1.5-7.5L2 9h7z"/></svg>',
    "globe": '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 010 20M12 2a15 15 0 000 20"/></svg>',
    "menu": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
    "vet":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 4v16M4 12h16"/></svg>',
    "shop":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 7h18l-2 12H5L3 7zM8 7V5a4 4 0 018 0v2"/></svg>',
    "groom":  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/></svg>',
    "stay":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 10V21h18V10M3 10l9-7 9 7M9 21v-6h6v6"/></svg>',
    "cafe":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 8h14v6a5 5 0 01-5 5H8a5 5 0 01-5-5V8zM17 9h2a3 3 0 010 6h-2"/></svg>',
    "park":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 2v20M5 9c0-4 3-7 7-7s7 3 7 7-3 7-7 7-7-3-7-7z"/></svg>',
    "rescue": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 00-7.8 0L12 5.6l-1-1a5.5 5.5 0 00-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 000-7.6z"/></svg>',
    "sit":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 20V4l18 8-18 8zM9 12h12"/></svg>',
    "move":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 12h18M13 5l8 7-8 7"/></svg>',
    "train":  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 10L12 4 2 10l10 6 10-6zM6 12v5c3 2 9 2 12 0v-5"/></svg>',
}

# ---------- EXTRACTORS -------------------------------------------------------

def _html_txt(s):
    """Strip HTML tags from a small string (used for address/title text)."""
    return re.sub(r"<[^>]+>", "", s or "").strip()

JSONLD_RE = re.compile(r'<script type="application/ld\+json">\s*(\{[^<]*?"@type":\s*"LocalBusiness"[^<]*?\})\s*</script>', re.DOTALL)
TITLE_RE = re.compile(r"<title>([^<]+)</title>")
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]+)"')
HERO_IMG_RE = re.compile(r'<div class="biz-hero">.*?<img src="([^"]+)"', re.DOTALL)
CAT_LABEL_RE = re.compile(r'<div class="(?:biz-hero-text\s*)?cat">([^<]+)</div>|<div class="cat">([^<]+)</div>')
PHONE_RE = re.compile(r'href="tel:(\+?\d+)"')
MAPS_DIR_RE = re.compile(r'href="(https://www\.google\.com/maps/dir/[^"]+)"')
WEBSITE_RE = re.compile(r'class="btn-outline"\s+href="(https?://[^"]+)"[^>]*>\s*(?:Visit Website|زيارة الموقع)')
PHOTOS_ROW_RE = re.compile(r'<div class="photos-row">(.*?)</div>', re.DOTALL)
PHOTO_IMG_RE = re.compile(r'<img src="([^"]+)"')
REVIEW_CARD_RE = re.compile(
    r'<(?:div|article) class="review-card">\s*<div class="review-header">\s*<span class="review-author">([^<]+)</span>\s*<span class="review-time">([^<]+)</span>\s*</div>\s*<div class="review-stars"[^>]*>([^<]+)</div>\s*<p class="review-text">(.*?)</p>\s*</(?:div|article)>',
    re.DOTALL,
)
ADDRESS_RE_EN = re.compile(r'<div class="biz-info-item"[^>]*>\s*<svg[^>]*>.*?</svg>\s*<div><div class="label">([^<]+)</div></div>', re.DOTALL)

def extract_business(filepath: Path) -> dict | None:
    """Extract a business detail page's full data. Returns None if not parseable."""
    try:
        raw = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    b: dict = {"file": str(filepath)}
    # language
    b["lang"] = "ar" if "/ar/" in str(filepath).replace("\\", "/") else "en"
    # slug from filesystem (source of truth; canonical in HTML may be stale after renames)
    b["slug"] = filepath.stem
    pre = "/ar" if b["lang"] == "ar" else ""
    b["canonical"] = f"{SITE}{pre}/business/{b['slug']}.html"

    # LocalBusiness JSON-LD (canonical source)
    m = JSONLD_RE.search(raw)
    if m:
        try:
            jd = json.loads(m.group(1))
        except json.JSONDecodeError:
            jd = {}
    else:
        jd = {}
    b["name"] = jd.get("name") or _html_txt((TITLE_RE.search(raw).group(1).split("|")[0] if TITLE_RE.search(raw) else filepath.stem))
    addr = jd.get("address") or {}
    b["address"] = addr.get("streetAddress", "") or ""
    b["locality"] = addr.get("addressLocality", "Doha")
    b["phone"] = jd.get("telephone", "") or ""
    geo = jd.get("geo") or {}
    b["lat"] = geo.get("latitude", "")
    b["lng"] = geo.get("longitude", "")
    rating = jd.get("aggregateRating") or {}
    try:
        b["rating"] = float(rating.get("ratingValue", 0) or 0)
    except (TypeError, ValueError):
        b["rating"] = 0.0
    rc = str(rating.get("reviewCount", "0") or "0").replace(",", "")
    try:
        b["review_count"] = int(rc)
    except ValueError:
        b["review_count"] = 0
    b["image"] = jd.get("image", "") or ""

    # Category (from hero .cat block on old pages OR .cat-kicker on rebuilt pages)
    cat_match = re.search(r'<div class="cat(?:-kicker)?">([^<]+)</div>', raw)
    raw_cat = cat_match.group(1).strip() if cat_match else ""
    # Iteratively unescape — previous buggy runs may have left multi-level escaped entities
    prev = None
    while prev != raw_cat:
        prev = raw_cat
        raw_cat = htmllib.unescape(raw_cat)
    b["cat_label"] = raw_cat

    # Map to category slug
    b["cat_slug"] = ""
    if b["cat_label"] in CAT_BY_EN_LABEL:
        b["cat_slug"] = CAT_BY_EN_LABEL[b["cat_label"]]["slug"]
    elif b["cat_label"] in CAT_BY_AR_LABEL:
        b["cat_slug"] = CAT_BY_AR_LABEL[b["cat_label"]]["slug"]

    # tel link -> unified phone href
    mph = PHONE_RE.search(raw)
    b["tel_href"] = "tel:" + mph.group(1) if mph else (("tel:+974" + b["phone"].replace(" ", "")) if b["phone"] else "")

    # Google Maps directions URL
    mdir = MAPS_DIR_RE.search(raw)
    b["maps_dir"] = mdir.group(1) if mdir else (f"https://www.google.com/maps/search/?api=1&query={b['lat']},{b['lng']}" if b["lat"] and b["lng"] else "")

    # External website
    mweb = WEBSITE_RE.search(raw)
    b["website"] = mweb.group(1) if mweb else ""

    # Image + photos source-of-truth: the local watermarked /images/<slug>.jpg.
    # The Google Maps lh3 URLs are dead (403 from CDN), so we ignore whatever
    # was in the old JSON-LD and check for a real file we host ourselves.
    local_jpg = ROOT / "images" / f"{b['slug']}.jpg"
    b["image"] = f"/images/{b['slug']}.jpg" if local_jpg.exists() else ""
    b["photos"] = []  # photos-row no longer rendered (no per-business gallery)

    # Reviews
    reviews = []
    for m2 in REVIEW_CARD_RE.finditer(raw):
        author = htmllib.unescape(m2.group(1).strip())
        time_ago = m2.group(2).strip()
        stars_txt = m2.group(3).strip()
        text_raw = m2.group(4).strip()
        text = htmllib.unescape(_html_txt(text_raw)).strip().strip('"\'"')
        stars = stars_txt.count("★")
        if author and text:
            reviews.append(dict(author=author, time=time_ago, stars=stars, text=text))
    b["reviews"] = reviews
    return b


def extract_businesses_from_list_page(filepath: Path) -> list[dict]:
    """Extract all <a class='card'> entries from a homepage/category page."""
    try:
        raw = filepath.read_text(encoding="utf-8")
    except Exception:
        return []
    out = []
    for block in re.findall(r'<a href="([^"]+)" class="card">(.*?)</a>', raw, re.DOTALL):
        url, body = block
        name_m = re.search(r'<div class="card-name">([^<]+)</div>', body)
        cat_m = re.search(r'<div class="card-cat">([^<]+)</div>', body)
        img_m = re.search(r'<img src="([^"]+)"', body)
        rating_m = re.search(r'<span class="star">★</span>\s*([0-9.]+)', body)
        reviews_m = re.search(r'<span [^>]*>\(([\d,]+)\)</span>', body)
        metas = re.findall(r'<div class="card-meta">(?:<svg[^>]*>.*?</svg>)?\s*(.*?)</div>', body, re.DOTALL)
        addr = _html_txt(metas[0]) if len(metas) >= 1 else ""
        phone = _html_txt(metas[1]) if len(metas) >= 2 else ""
        try:
            rating = float(rating_m.group(1)) if rating_m else 0.0
        except ValueError:
            rating = 0.0
        try:
            review_count = int(reviews_m.group(1).replace(",", "")) if reviews_m else 0
        except ValueError:
            review_count = 0
        out.append(dict(
            url=url.strip(),
            name=htmllib.unescape((name_m.group(1).strip() if name_m else "")),
            cat_label=htmllib.unescape((cat_m.group(1).strip() if cat_m else "")),
            image=(img_m.group(1).strip() if img_m else ""),
            rating=rating,
            review_count=review_count,
            address=htmllib.unescape(addr),
            phone=htmllib.unescape(phone),
        ))
    return out

# ---------- HELPERS ----------------------------------------------------------

def esc(s: str) -> str:
    return htmllib.escape(s or "", quote=True)

def fmt_reviews(n: int) -> str:
    if n >= 1000:
        v = n / 1000
        return f"{v:.1f}k".replace(".0k", "k")
    return f"{n:,}"

def star_row(rating: float) -> str:
    full = int(round(rating))
    return "★" * full + "☆" * max(0, 5 - full)

def tone_for_cat(slug: str) -> str:
    return CAT_BY_SLUG.get(slug, {}).get("tone", "vet")

def glyph_for_tone(tone: str) -> str:
    return SVG.get(tone, SVG["vet"])

def prefix(lang: str) -> str:
    return "/ar" if lang == "ar" else ""

def cat_label(slug: str, lang: str) -> str:
    c = CAT_BY_SLUG.get(slug)
    return (c["ar"] if lang == "ar" else c["en"]) if c else slug

def unit(slug: str, lang: str) -> str:
    c = CAT_BY_SLUG.get(slug)
    return (c["ar_unit"] if lang == "ar" else c["en_unit"]) if c else ""

# ---------- SHARED HEAD / HEADER / FOOTER ------------------------------------

def head_block(*, lang: str, title: str, description: str, path: str,
               og_type: str = "website", extra_ldjson: list[str] | None = None) -> str:
    """Return the full <head>...</head> block."""
    html_lang = lang
    dir_attr = "rtl" if lang == "ar" else "ltr"
    url_self = SITE + path
    # URL-encode the alt path for hreflang
    other = path
    if lang == "ar" and path.startswith("/ar"):
        other_path = path[len("/ar"):] or "/"
    else:
        other_path = "/ar" + path if not path.startswith("/ar") else path
    url_en = SITE + (other_path if lang == "ar" else path)
    url_ar = SITE + (path if lang == "ar" else other_path)
    og_locale = "ar_QA" if lang == "ar" else "en_US"
    og_locale_alt = "en_US" if lang == "ar" else "ar_QA"
    extras = "\n".join(extra_ldjson or [])
    return f"""<!DOCTYPE html>
<html lang="{html_lang}" dir="{dir_attr}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="referrer" content="no-referrer-when-downgrade">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{esc(url_self)}">
<meta property="og:site_name" content="QatarPaws">
<meta property="og:locale" content="{og_locale}">
<meta property="og:locale:alternate" content="{og_locale_alt}">
<meta property="og:image" content="{SITE}/images/og-default.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{SITE}/images/og-default.svg">
<link rel="canonical" href="{esc(url_self)}">
<link rel="alternate" hreflang="en" href="{esc(url_en)}">
<link rel="alternate" hreflang="ar" href="{esc(url_ar)}">
<link rel="alternate" hreflang="x-default" href="{SITE}/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="dns-prefetch" href="https://maps.google.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Amiri:ital,wght@0,400;0,700;1,400&family=Cairo:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="preload" href="/css/style.css" as="style">
<link rel="stylesheet" href="/css/style.css">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#F6F1E8">
{extras}
<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>
<!-- Google Search Console -->
<meta name="google-site-verification" content="{GSC_VERIFICATION}">
</head>"""


def header_block(lang: str) -> str:
    t = UI[lang]
    pre = prefix(lang)
    lang_href = "/" if lang == "ar" else "/ar/"
    return f"""<a href="#main" class="skip-link">{'تخطّ إلى المحتوى' if lang=='ar' else 'Skip to main content'}</a>
<header class="topbar" role="banner">
<div class="topbar-inner">
<a href="{pre}/" class="logo" aria-label="QatarPaws home">
{SVG['paw']}
<span class="wordmark">Qatar<em>Paws</em></span>
</a>
<button class="nav-toggle" type="button" aria-label="{esc(t['nav_toggle'])}" aria-expanded="false" aria-controls="primary-nav" onclick="this.setAttribute('aria-expanded',this.getAttribute('aria-expanded')==='true'?'false':'true');document.getElementById('primary-nav').classList.toggle('open')">{SVG['menu']}</button>
<nav class="nav" id="primary-nav" aria-label="Primary">
<a href="{pre}/#categories">{esc(t['nav_cats'])}</a>
<a href="{pre}/blog/">{esc(t['nav_journal'])}</a>
<a href="{pre}/about.html">{esc(t['nav_about'] if 'nav_about' in t else (t['foot_about']))}</a>
<span class="divider" aria-hidden="true"></span>
<a href="{lang_href}" class="lang">{SVG['globe']} {esc(t['nav_lang'])}</a>
<a href="{pre}/list-your-business.html" class="list-cta">{esc(t['nav_list'])}</a>
</nav>
</div>
</header>"""


def footer_block(lang: str) -> str:
    t = UI[lang]
    pre = prefix(lang)
    # category links for footer "Directory" column
    cats = []
    for c in CATS[:6]:
        cats.append(f'<li><a href="{pre}/{c["slug"]}/">{esc(c["ar"] if lang=="ar" else c["en"])}</a></li>')
    cat_lis = "\n".join(cats)
    return f"""<footer class="site-foot" role="contentinfo">
<div class="foot">
<div class="brand">
<h3>QatarPaws</h3>
<p>{esc(t['foot_blurb'])}</p>
</div>
<div>
<h4>{esc(t['foot_dir'])}</h4>
<ul>
{cat_lis}
</ul>
</div>
<div>
<h4>{esc(t['foot_journal'])}</h4>
<ul>
<li><a href="{pre}/blog/">{esc(t['foot_blog'])}</a></li>
<li><a href="{pre}/about.html">{esc(t['foot_about'])}</a></li>
</ul>
</div>
<div>
<h4>{esc(t['foot_business'])}</h4>
<ul>
<li><a href="{pre}/list-your-business.html">{esc(t['foot_list'])}</a></li>
<li><a href="mailto:hello@qatarpaws.com">{esc(t['foot_contact'])}</a></li>
</ul>
</div>
</div>
<div class="foot-bottom">
<span>{esc(t['foot_bottom_l'])}</span>
<span>{esc(t['foot_bottom_r'])}</span>
</div>
</footer>"""


# ---------- CARD TEMPLATES ---------------------------------------------------

def render_card(biz: dict, lang: str, wide: bool = False, badge: str | None = None) -> str:
    """Render a new-design biz card. `biz` can be the full detail dict or a homepage card dict."""
    t = UI[lang]
    url = biz.get("canonical", "").replace(SITE, "") or biz.get("url", "")
    if not url.startswith("/"):
        url = "/" + url.lstrip("/")
    # Image: use biz['image'] (detail) or biz['image']
    img = biz.get("image", "")
    name = biz.get("name", "")
    cat_label = biz.get("cat_label", "") or cat_label_from_any(biz, lang)
    # Determine category slug
    cat_slug = biz.get("cat_slug") or CAT_BY_EN_LABEL.get(cat_label, {}).get("slug") or CAT_BY_AR_LABEL.get(cat_label, {}).get("slug") or ""
    address = biz.get("address", "")
    locality = biz.get("locality", "") or ""
    # Location line: trim to neighborhood + city
    loc_line = address or (locality or ("Doha" if lang == "en" else "الدوحة"))
    rating = float(biz.get("rating") or 0)
    review_count = int(biz.get("review_count") or 0)
    aria_label = esc(f"{name}, {cat_label}")
    stars_label = f"{rating:.1f} out of 5" if lang == "en" else f"{rating:.1f} من 5"
    # Service tags line from category
    c_meta = CAT_BY_SLUG.get(cat_slug)
    tags = ""
    if c_meta:
        tags_src = c_meta["ar_tags"] if lang == "ar" else c_meta["en_tags"]
        tags = " · ".join(tags_src[:3])
    wide_cls = " wide" if wide else ""
    badge_html = ""
    if badge:
        badge_html = f'<span class="badge top">{esc(badge)}</span>'
    # image or placeholder
    if img:
        img_html = f'<img src="{esc(img)}" alt="{esc(name)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'"><div class="ph" style="display:none"><span>QATARPAWS</span></div>'
    else:
        img_html = '<div class="ph"><span>QATARPAWS</span></div>'
    rating_block = ""
    if rating > 0:
        rating_block = f'<span class="rating" aria-label="{esc(stars_label)}">{SVG["star"]} {rating:.1f} <em>({fmt_reviews(review_count)})</em></span>'
    return f"""<article class="biz{wide_cls}">
<a class="stretched" href="{esc(url)}" aria-label="{aria_label}"></a>
<div class="img">
{img_html}
<div class="badges">{badge_html}</div>
{rating_block}
</div>
<div class="body">
<div class="cat-label">{esc(cat_label)}</div>
<h3>{esc(name)}</h3>
<div class="neighborhood">{SVG['pin']} <span>{esc(loc_line)}</span></div>
<div class="divider"></div>
<div class="cta-row">
<span class="tags">{esc(tags)}</span>
<a href="{esc(url)}">{esc(t['view_details'])} →</a>
</div>
</div>
</article>"""


def cat_label_from_any(biz: dict, lang: str) -> str:
    label = biz.get("cat_label") or ""
    if not label:
        slug = biz.get("cat_slug", "")
        if slug:
            return CAT_BY_SLUG[slug]["ar" if lang == "ar" else "en"]
    return label


# ---------- CATEGORY RAIL ----------------------------------------------------

def render_cat_rail(lang: str, counts: dict[str, int]) -> str:
    t = UI[lang]
    pre = prefix(lang)
    items = []
    for c in CATS:
        if c["slug"] == "training" and counts.get("training", 0) == 0:
            continue  # hide empty training
        label = c["ar"] if lang == "ar" else c["en"]
        unit = c["ar_unit"] if lang == "ar" else c["en_unit"]
        count = counts.get(c["slug"], 0)
        count_str = f"{count} {unit}"
        items.append(f"""<a class="cat" data-tone="{c['tone']}" href="{pre}/{c['slug']}/">
<span class="glyph">{glyph_for_tone(c['tone'])}</span>
<div class="label">{esc(label)}</div>
<div class="count">{esc(count_str)}</div>
<span class="arrow" aria-hidden="true">↗</span>
</a>""")
    return f"""<section class="rail" id="categories">
<div class="wrap">
<div class="section-head">
<div>
<div class="eyebrow">{esc(t['rail_eyebrow'])}</div>
<h2>{esc(t['rail_h2'])}</h2>
</div>
</div>
<div class="rail-scroll" role="list">
{chr(10).join(items)}
</div>
</div>
</section>"""


# ---------- EDITORIAL / JOURNAL ---------------------------------------------

def render_journal(lang: str) -> str:
    t = UI[lang]
    tiles = []
    for j in JOURNAL[lang]:
        tiles.append(f"""<a class="feat {j['cls']}" href="{esc(j['href'])}">
<span class="count-chip">{esc(j['count'])}</span>
<span class="kicker">{esc(j['kicker'])}</span>
<h3>{esc(j['h'])}</h3>
<p>{esc(j['p'])}</p>
</a>""")
    return f"""<section class="editorial">
<div class="wrap">
<div class="section-head">
<div>
<div class="eyebrow">{esc(t['editorial_eyebrow'])}</div>
<h2>{esc(t['editorial_h2'])}</h2>
</div>
</div>
<div class="edit-grid">
{chr(10).join(tiles)}
</div>
</div>
</section>"""


# ---------- HERO -------------------------------------------------------------

def render_hero(lang: str, total_places: int, total_cats: int, top_pin: dict | None) -> str:
    t = UI[lang]
    pre = prefix(lang)
    # Popular tag chips
    tag_links = "".join(
        f'<a href="{pre}/{slug}/">{esc(label)}</a>'
        for slug, label in zip(
            ["vets","pet-friendly-hotels","grooming","relocation","rescue"],
            t["popular_tags"]
        )
    )
    # Map pin
    if top_pin:
        pin_name = top_pin["name"]
        pin_meta = f"{top_pin['rating']:.1f} ★ · {fmt_reviews(top_pin['review_count'])} " + ("تقييمًا" if lang=="ar" else "reviews")
        pin_init = pin_name[:1].upper() if pin_name else "Q"
        pin_html = f"""<div class="map-pin" aria-hidden="true">
<div class="avatar">{esc(pin_init)}</div>
<div>
<div class="n">{esc(pin_name)}</div>
<div class="m">{esc(pin_meta)}</div>
</div>
</div>"""
    else:
        pin_html = ""

    # Hero headline: different structure per language
    if lang == "en":
        headline_html = f'{esc(t["hero_h1_a"])} <em>{esc(t["hero_h1_em"])}</em><br>{esc(t["hero_h1_amp"])} <span class="amp">go</span> in Qatar.'
    else:
        headline_html = f'{esc(t["hero_h1_a"])} <em>{esc(t["hero_h1_em"])}</em> {esc(t["hero_h1_amp"])} {esc(t["hero_h1_b"])}'

    eyebrow_full = f"{t['hero_eyebrow']} · {total_places} " + ("مكانًا" if lang=="ar" else "places")
    return f"""<section class="hero">
<div class="wrap hero-grid">
<div class="hero-copy">
<span class="eyebrow-pill"><span class="dot"></span> {esc(eyebrow_full)}</span>
<h1>{headline_html}</h1>
<p class="lead">{esc(t['hero_lead'])}</p>

<form class="search" onsubmit="event.preventDefault()" role="search">
<span class="ico">{SVG['search']}</span>
<input type="text" id="searchInput" placeholder="{esc(t['search_placeholder'])}" aria-label="{esc(t['search_placeholder'])}" autocomplete="off">
<button type="submit" class="go">{esc(t['search_go'])}</button>
<div id="searchResults" class="search-dropdown" role="listbox"></div>
</form>

<div class="search-tags" aria-label="{esc(t['popular'])}">
<span class="label">{esc(t['popular'])} →</span>
{tag_links}
</div>

<div class="stats">
<div class="stat"><div class="n">{total_places}</div><div class="l">{esc(t['stat_places'])}</div></div>
<div class="stat"><div class="n">{total_cats}</div><div class="l">{esc(t['stat_cats'])}</div></div>
<div class="stat"><div class="n">{esc(t['stat_lang'])}</div><div class="l">{esc(t['stat_lang_l'])}</div></div>
<div class="stat"><div class="n">{esc(t['stat_year'])}</div><div class="l">{esc(t['stat_year_l'])}</div></div>
</div>
</div>

<div class="map-card" role="img" aria-label="{esc(t['map_chip_a'])}">
<div class="map-toolbar">
<span class="map-chip"><span class="dot"></span> {esc(t['map_chip_a'])}</span>
<span class="map-chip ghost">{esc(t['map_chip_b'])}</span>
</div>
{pin_html}
<div class="map-legend">
<span><span class="sq" style="background:var(--maroon-600)"></span>{esc(CAT_BY_SLUG['vets']['ar' if lang=='ar' else 'en'])}</span>
<span><span class="sq" style="background:var(--teal-600)"></span>{esc(CAT_BY_SLUG['pet-shops']['ar' if lang=='ar' else 'en'])}</span>
<span><span class="sq" style="background:oklch(0.45 0.12 75)"></span>{esc(CAT_BY_SLUG['grooming']['ar' if lang=='ar' else 'en'])}</span>
<span><span class="sq" style="background:var(--ink-900)"></span>{esc(CAT_BY_SLUG['pet-friendly-hotels']['ar' if lang=='ar' else 'en'])}</span>
</div>
</div>
</div>
</section>"""


# ---------- GUIDE / COMPARE --------------------------------------------------

def render_guide(lang: str, top_vets: list[dict]) -> str:
    t = UI[lang]
    pre = prefix(lang)
    rows = []
    for i, v in enumerate(top_vets[:4]):
        tone_cls = ["m","t","g","m"][i]
        name = v["name"]
        initial = (name[:1].upper() if name else "?")
        loc = v.get("address") or (v.get("locality") or "")
        sub = loc[:36] + ("…" if len(loc) > 36 else "")
        stars_txt = star_row(v["rating"])
        price_txt = f"{int(v['rating']*10)}+ " + ("تقييمًا" if lang=="ar" else "reviews")
        rows.append(f"""<div class="compare-row">
<div class="who">
<div class="avatar {tone_cls}">{esc(initial)}</div>
<div><div class="name">{esc(name)}</div><div class="sub">{esc(sub)}</div></div>
</div>
<div style="text-align:right"><div class="stars">{stars_txt}</div><div class="price">{esc(price_txt)}</div></div>
</div>""")
    guide_headline = f"{esc(t['guide_h2_a'])} <em>{esc(t['guide_h2_em'])}</em>"
    return f"""<section class="guide">
<div class="wrap guide-grid">
<div>
<div class="eyebrow">{esc(t['guide_eyebrow'])}</div>
<h2>{guide_headline}</h2>
<p>{esc(t['guide_p'])}</p>
<div class="actions">
<a href="{pre}/vets/" class="btn primary">{esc(t['guide_cta1'])} →</a>
<a href="{pre}/about.html" class="btn ghost">{esc(t['guide_cta2'])}</a>
</div>
</div>
<div class="guide-visual" aria-hidden="true">
<div class="compare-header"><span>{esc(t['compare_h'])}</span><span>{esc(t['compare_h2'])}</span></div>
{chr(10).join(rows)}
</div>
</div>
</section>"""


# ---------- HOMEPAGE ---------------------------------------------------------

def build_homepage(lang: str, all_businesses: list[dict], counts: dict[str,int]) -> str:
    t = UI[lang]
    pre = prefix(lang)
    businesses_lang = [b for b in all_businesses if b["lang"] == lang]
    total_places = len(businesses_lang)
    total_cats = sum(1 for c in CATS if counts.get(c["slug"], 0) > 0)

    # Sort by rating*log(reviews) to feature genuinely popular ones
    import math
    def score(b):
        r = b.get("rating", 0) or 0
        c = b.get("review_count", 0) or 0
        return r * math.log10(max(c, 1) + 1)

    sorted_biz = sorted(businesses_lang, key=score, reverse=True)

    top_pin = None
    for b in sorted_biz:
        if b.get("cat_slug") == "vets":
            top_pin = b
            break
    top_pin = top_pin or (sorted_biz[0] if sorted_biz else None)

    # Near-you cards: top 9, first one wide
    near = sorted_biz[:9]
    cards_html = []
    for i, b in enumerate(near):
        is_wide = (i == 0)
        badge = t["editors_pick"] if i == 0 else (t["top_rated"] if i < 3 else None)
        cards_html.append(render_card(b, lang, wide=is_wide, badge=badge))

    # Filter pills: All + top categories
    pre_cats = ["vets","pet-shops","grooming","pet-friendly-cafes","boarding"]
    filter_buttons = [f'<a class="on" href="{pre}/">{esc(t["filter_all"])}</a>']
    for slug in pre_cats:
        if counts.get(slug, 0) > 0:
            filter_buttons.append(f'<a href="{pre}/{slug}/">{esc(cat_label(slug, lang))}</a>')
    # Top vets for compare widget
    top_vets = [b for b in sorted_biz if b.get("cat_slug") == "vets"][:4]

    # Assemble
    title = "QatarPaws — The Pet Guide to Qatar" if lang=="en" else "قطر بوز — دليل الحيوانات الأليفة في قطر"
    description = t["hero_lead"]

    org_ldjson = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"WebSite","name":"QatarPaws","alternateName":"{'قطر بوز' if lang=='ar' else 'Qatar Pet Directory'}","url":"{SITE}/","inLanguage":["en","ar"]}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Organization","name":"QatarPaws","url":"{SITE}/","description":{json.dumps(description, ensure_ascii=False)},"sameAs":[]}}
</script>"""

    head = head_block(lang=lang, title=title, description=description,
                      path=f"{pre}/", og_type="website", extra_ldjson=[org_ldjson])

    near_html = f"""<section class="near">
<div class="wrap">
<div class="section-head">
<div>
<div class="eyebrow">{esc(t['near_eyebrow'])}</div>
<h2>{esc(t['near_h2'])}</h2>
</div>
<a class="more" href="{pre}/vets/">{esc(t['near_more'])} →</a>
</div>
<div class="filters" role="tablist">
{''.join(filter_buttons)}
</div>
<div class="cards">
{chr(10).join(cards_html)}
</div>
</div>
</section>"""

    guide_html = render_guide(lang, top_vets) if top_vets else ""

    ad_zone = '<div class="ad-zone"><div class="ad-placeholder">Ad slot · Responsive</div></div>'

    body = f"""<body>
{header_block(lang)}
<main id="main" role="main">
{render_hero(lang, total_places, total_cats, top_pin)}
{render_cat_rail(lang, counts)}
{ad_zone}
{render_journal(lang)}
{near_html}
{ad_zone}
{guide_html}
</main>
{footer_block(lang)}
<script src="/js/fuse.min.js" defer></script>
<script src="/js/search.js" defer></script>
</body>
</html>"""

    return head + "\n" + body


# ---------- CATEGORY PAGE ----------------------------------------------------

def build_category(lang: str, slug: str, cat_businesses: list[dict], counts: dict[str,int]) -> str:
    t = UI[lang]
    pre = prefix(lang)
    c = CAT_BY_SLUG[slug]
    label = c["ar"] if lang == "ar" else c["en"]
    tag = c["ar_tag"] if lang == "ar" else c["en_tag"]

    # Sort by rating*reviews
    import math
    def score(b):
        r = b.get("rating", 0) or 0
        n = b.get("review_count", 0) or 0
        return r * math.log10(max(n, 1) + 1)
    sorted_biz = sorted(cat_businesses, key=score, reverse=True)

    cards = []
    for i, b in enumerate(sorted_biz):
        badge = t["editors_pick"] if i == 0 and b.get("rating", 0) >= 4.5 else (t["top_rated"] if i < 3 and b.get("rating", 0) >= 4.5 else None)
        cards.append(render_card(b, lang, wide=False, badge=badge))

    count = len(sorted_biz)
    results_line = f'{count} {t["page_results"]}'

    # Breadcrumb JSON-LD
    bc_ldjson = json.dumps({
        "@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":t["bc_home"],"item":SITE + pre + "/"},
            {"@type":"ListItem","position":2,"name":label}
        ]
    }, ensure_ascii=False)
    ldjson = f'<script type="application/ld+json">{bc_ldjson}</script>'

    title = f"{label} | QatarPaws" if lang == "en" else f"{label} | قطر بوز"
    head = head_block(lang=lang, title=title, description=tag,
                      path=f"{pre}/{slug}/", og_type="website", extra_ldjson=[ldjson])

    cards_html = "\n".join(cards) if cards else f'<div class="coming-soon"><div class="glyph">🐾</div><h2>{esc(t["blog_soon_h"])}</h2><p>{esc(tag)}</p></div>'

    body = f"""<body>
{header_block(lang)}
<main id="main" role="main">
<section class="page-title">
<div class="wrap">
<div class="eyebrow">{esc(t['near_eyebrow'])}</div>
<h1>{esc(label)}</h1>
<p class="lead">{esc(tag)}</p>
</div>
</section>
<div class="wrap">
<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="{pre}/">{esc(t['bc_home'])}</a>
<span class="sep">›</span>
<span>{esc(label)}</span>
</nav>
<p class="eyebrow" style="margin:4px 0 18px">{esc(results_line)}</p>
<div class="cards">
{cards_html}
</div>
</div>
<div class="ad-zone"><div class="ad-placeholder">Ad slot · Responsive</div></div>
</main>
{footer_block(lang)}
<script src="/js/fuse.min.js" defer></script>
<script src="/js/search.js" defer></script>
</body>
</html>"""
    return head + "\n" + body


# ---------- BUSINESS DETAIL PAGE --------------------------------------------

def build_business(b: dict, all_businesses: list[dict]) -> str:
    lang = b["lang"]
    t = UI[lang]
    pre = prefix(lang)
    c = CAT_BY_SLUG.get(b.get("cat_slug") or "")
    cat_label_display = (c["ar"] if c and lang=="ar" else (c["en"] if c else b["cat_label"]))
    cat_slug = b.get("cat_slug") or ""

    # Service tags (from category)
    tags_src = []
    if c:
        tags_src = c["ar_tags"] if lang == "ar" else c["en_tags"]
    service_tags_html = "".join(f"<span>{esc(x)}</span>" for x in tags_src)

    # Action buttons
    actions = []
    if b["tel_href"]:
        actions.append(f'<a href="{esc(b["tel_href"])}" class="btn primary">📞 {esc(t["biz_call"])}</a>')
    if b["maps_dir"]:
        actions.append(f'<a href="{esc(b["maps_dir"])}" target="_blank" rel="noopener" class="btn ghost">📍 {esc(t["biz_dir"])}</a>')
    if b["website"]:
        actions.append(f'<a href="{esc(b["website"])}" target="_blank" rel="noopener" class="btn ghost">↗ {esc(t["biz_web"])}</a>')
    actions_html = "\n".join(actions)

    # Facts grid
    facts = []
    if b["address"]:
        facts.append(f'<div class="fact">{SVG["pin_lg"]}<div><span class="k">{esc(t["biz_address"])}</span><span class="v">{esc(b["address"])}</span></div></div>')
    if b["phone"]:
        facts.append(f'<div class="fact">{SVG["phone"]}<div><span class="k">{esc(t["biz_phone"])}</span><span class="v" dir="ltr">{esc(b["phone"])}</span></div></div>')
    facts_html = "\n".join(facts)

    # Hero media — local watermarked image if we have one, else branded placeholder
    if b["image"]:
        media = (f'<img src="{esc(b["image"])}" alt="{esc(b["name"])}" '
                 f'loading="lazy" '
                 f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
                 f'<div class="ph" style="display:none"><span>qatarpaws.com</span></div>'
                 f'<small class="photo-credit">{esc(t["photo_credit"])}</small>')
    else:
        media = '<div class="ph"><span>qatarpaws.com</span></div>'

    rating_pill = ""
    if b["rating"] > 0:
        rating_pill = f'<span class="rating-pill" aria-label="{b["rating"]:.1f} / 5">{SVG["star"]} {b["rating"]:.1f} <em>({fmt_reviews(b["review_count"])})</em></span>'

    badges_html = '<span class="badge verified">' + esc(t["verified"]) + '</span>' if b["rating"] >= 4.5 else ""

    # Map embed (Google, no key needed, lazy-loaded)
    map_html = ""
    if b["lat"] and b["lng"]:
        src = f"https://maps.google.com/maps?q={b['lat']},{b['lng']}&z=15&output=embed"
        map_html = f"""<section class="biz-section">
<div class="wrap">
<div class="biz-map-frame">
<iframe src="{esc(src)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Map" allowfullscreen></iframe>
</div>
</div>
</section>"""

    # Photos
    photos_html = ""
    if b["photos"]:
        imgs = "".join(f'<img src="{esc(p)}" alt="{esc(b["name"])}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'">' for p in b["photos"][:12])
        photos_html = f"""<section class="biz-section">
<div class="wrap">
<h2>{esc(t['biz_photos'])}</h2>
<div class="photos-row">{imgs}</div>
</div>
</section>"""

    # Reviews
    reviews_html = ""
    if b["reviews"]:
        review_cards = []
        for r in b["reviews"][:6]:
            stars = "★" * r["stars"] + "☆" * max(0, 5 - r["stars"])
            txt = r["text"][:360] + ("…" if len(r["text"]) > 360 else "")
            review_cards.append(f"""<article class="review-card">
<div class="review-header">
<span class="review-author">{esc(r['author'])}</span>
<span class="review-time">{esc(r['time'])}</span>
</div>
<div class="review-stars" aria-label="{r['stars']} / 5">{stars}</div>
<p class="review-text">{esc(txt)}</p>
</article>""")
        more_link = ""
        if b["lat"] and b["lng"]:
            more_link = f'<p style="margin-top:18px"><a href="https://www.google.com/maps/search/?api=1&query={b["lat"]},{b["lng"]}" target="_blank" rel="noopener" class="btn ghost">{esc(t["biz_more_google"])} →</a></p>'
        reviews_html = f"""<section class="biz-section">
<div class="wrap">
<h2>{esc(t['biz_reviews'])}</h2>
<div class="reviews-grid">
{chr(10).join(review_cards)}
</div>
{more_link}
</div>
</section>"""

    # Similar places: 3 others in same category, same lang, by rating
    similar = []
    if cat_slug:
        cand = [x for x in all_businesses if x["lang"] == lang and x.get("cat_slug") == cat_slug and x["slug"] != b["slug"]]
        cand.sort(key=lambda x: (x.get("rating", 0), x.get("review_count", 0)), reverse=True)
        similar = cand[:3]
    similar_html = ""
    if similar:
        sim_cards = "\n".join(render_card(s, lang) for s in similar)
        similar_html = f"""<section class="biz-section">
<div class="wrap">
<h2>{esc(t['biz_similar'])}</h2>
<div class="similar-grid">
{sim_cards}
</div>
</div>
</section>"""

    # JSON-LD (clean LocalBusiness + BreadcrumbList + up to 5 Reviews)
    ld_lb = {
        "@context":"https://schema.org","@type":"LocalBusiness",
        "name": b["name"],
        "address": {"@type":"PostalAddress","addressLocality":b["locality"],"addressCountry":"QA","streetAddress":b["address"]},
        "url": b["canonical"] or (SITE + pre + f"/business/{b['slug']}.html"),
    }
    if b["phone"]: ld_lb["telephone"] = b["phone"]
    if b["lat"] and b["lng"]: ld_lb["geo"] = {"@type":"GeoCoordinates","latitude":str(b["lat"]),"longitude":str(b["lng"])}
    if b["rating"] and b["review_count"]:
        ld_lb["aggregateRating"] = {"@type":"AggregateRating","ratingValue":f"{b['rating']:.1f}","reviewCount":str(b["review_count"])}
    if b["image"]: ld_lb["image"] = SITE + b["image"]

    ld_bc = {
        "@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":t["bc_home"],"item":SITE + pre + "/"},
            {"@type":"ListItem","position":2,"name":cat_label_display,"item":SITE + pre + f"/{cat_slug}/" if cat_slug else SITE + pre + "/"},
            {"@type":"ListItem","position":3,"name":b["name"]},
        ]
    }

    ld_reviews = []
    for r in b["reviews"][:5]:
        ld_reviews.append({
            "@context":"https://schema.org","@type":"Review",
            "author":{"@type":"Person","name":r["author"]},
            "reviewRating":{"@type":"Rating","ratingValue":str(r["stars"]),"bestRating":"5"},
            "reviewBody":r["text"],
            "itemReviewed":{"@type":"LocalBusiness","url":ld_lb["url"]},
        })

    ldjson_parts = [f'<script type="application/ld+json">{json.dumps(ld_lb, ensure_ascii=False)}</script>',
                    f'<script type="application/ld+json">{json.dumps(ld_bc, ensure_ascii=False)}</script>']
    for lr in ld_reviews:
        ldjson_parts.append(f'<script type="application/ld+json">{json.dumps(lr, ensure_ascii=False)}</script>')

    title = f"{b['name']} | QatarPaws" if lang == "en" else f"{b['name']} | قطر بوز"
    desc_parts = [b["name"], f"{cat_label_display}"]
    if lang == "en":
        desc_parts.append(f"in Qatar. Rating: {b['rating']:.1f}/5" if b["rating"] else "in Qatar.")
    else:
        desc_parts.append(f"في قطر. التقييم: {b['rating']:.1f}/5" if b["rating"] else "في قطر.")
    if b["phone"]: desc_parts.append(("Phone: " if lang=="en" else "هاتف: ") + b["phone"])
    if b["address"]: desc_parts.append(b["address"])
    description = ". ".join([p for p in desc_parts if p])[:300]

    path = (f"/ar/business/{b['slug']}.html" if lang == "ar" else f"/business/{b['slug']}.html")
    head = head_block(lang=lang, title=title, description=description, path=path, og_type="website", extra_ldjson=ldjson_parts)

    ad_zone = '<div class="ad-zone"><div class="ad-placeholder">Ad slot · Responsive</div></div>'

    body = f"""<body>
{header_block(lang)}
<main id="main" role="main" class="biz-page">
<div class="wrap">
<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="{pre}/">{esc(t['bc_home'])}</a>
<span class="sep">›</span>
{'<a href="'+pre+'/'+cat_slug+'/">'+esc(cat_label_display)+'</a>' if cat_slug else ''}
{'<span class="sep">›</span>' if cat_slug else ''}
<span>{esc(b['name'])}</span>
</nav>

<section class="biz-hero-v2">
<div class="media">
{media}
<div class="badges">{badges_html}</div>
{rating_pill}
</div>
<div class="info">
<div class="cat-kicker">{esc(cat_label_display)}</div>
<h1>{esc(b['name'])}</h1>
<div class="neighborhood">{SVG['pin_lg']}<span>{esc(b['address'] or b['locality'] or ('Doha' if lang=='en' else 'الدوحة'))}</span></div>
{'<div class="service-tags">'+service_tags_html+'</div>' if service_tags_html else ''}
<div class="biz-facts">
{facts_html}
</div>
<div class="biz-actions-v2">
{actions_html}
</div>
</div>
</section>
</div>

{ad_zone}
{map_html}
{photos_html}
{reviews_html}
{ad_zone}
{similar_html}
</main>
{footer_block(lang)}
<script src="/js/fuse.min.js" defer></script>
<script src="/js/search.js" defer></script>
</body>
</html>"""

    return head + "\n" + body


# ---------- ABOUT / BLOG / LIST-YOUR-BUSINESS --------------------------------

def build_about(lang: str) -> str:
    t = UI[lang]
    pre = prefix(lang)
    title = f"{t['about_h1']} | QatarPaws"
    description = t["about_lead"]
    head = head_block(lang=lang, title=title, description=description, path=f"{pre}/about.html", og_type="website")

    if lang == "en":
        body_prose = """
<h2>What is QatarPaws?</h2>
<p>QatarPaws is an independent, bilingual directory of every pet service in Qatar — vets, groomers, pet shops, boarders, cafés, rescues and more. Built for Qatar's pet community, updated weekly, free to use.</p>

<h2>Our mission</h2>
<p>We make it easy for pet owners in Qatar to find trusted services. Every listing is verified against publicly available sources (Google Maps, official business records) and includes contact details, ratings, photos and recent reviews.</p>

<h2>What you'll find</h2>
<ul>
<li>Veterinary clinics and animal hospitals</li>
<li>Pet grooming — salons and mobile services</li>
<li>Pet shops and supplies stores</li>
<li>Boarding, daycare and pet sitting</li>
<li>Rescue centers and adoption shelters</li>
<li>Pet relocation and travel specialists</li>
<li>Pet-friendly cafés, hotels and parks</li>
<li>Professional dog training</li>
</ul>

<h2>How we collect information</h2>
<p>All listings are drawn from publicly available sources. If you own a business and want to update your listing, correct details, or be added, please <a href="/list-your-business.html">send us a note</a>.</p>

<h2>Bilingual by default</h2>
<p>Every page is available in English and Arabic. We serve Qatar's diverse community, not a subset of it.</p>

<h2>Photos &amp; takedown policy</h2>
<p>Photos shown on listings are sourced from publicly available Google Maps pages to help visitors recognize each business. We do not claim ownership of any photo. If you are the owner of a business or photo featured here and want it updated or removed, email us at <a href="mailto:qatarpaw@gmail.com">qatarpaw@gmail.com</a> — we'll respond within 7 days.</p>
"""
    else:
        body_prose = """
<h2>ما هو قطر بوز؟</h2>
<p>قطر بوز هو دليل مستقل وثنائي اللغة لكلّ خدمة تخصّ الحيوانات الأليفة في قطر — من العيادات البيطرية، والعناية، والمتاجر، وفنادق الإيواء، والمقاهي، ومآوي الإنقاذ وأكثر. مصمَّم لمجتمع الحيوانات الأليفة في قطر، يُحدَّث أسبوعيًا، ومجانيّ تمامًا.</p>

<h2>مهمّتنا</h2>
<p>نسهّل على مربّي الحيوانات في قطر إيجاد الخدمات الموثوقة. كلّ إدراج موثَّق من مصادر عامّة (جوجل مابس، وسجلات الأعمال الرسمية)، ويتضمّن بيانات الاتصال، والتقييمات، والصور، والتعليقات الحديثة.</p>

<h2>ماذا ستجد هنا</h2>
<ul>
<li>العيادات البيطرية والمستشفيات</li>
<li>عناية بالحيوانات — صالونات وخدمات متنقلة</li>
<li>متاجر الحيوانات الأليفة ومستلزماتها</li>
<li>الإيواء، والرعاية النهارية، والتربية في المنزل</li>
<li>مآوي الإنقاذ والتبنّي</li>
<li>متخصّصون في نقل الحيوانات والسفر</li>
<li>مقاهٍ، وفنادق، وحدائق ترحّب بالحيوانات</li>
<li>تدريب احترافي للكلاب</li>
</ul>

<h2>كيف نجمع المعلومات</h2>
<p>تُستمدّ كلّ المعلومات من مصادر عامّة. إذا كنت صاحب نشاط وتريد تحديث إدراجك، أو تصحيح البيانات، أو إضافتك، <a href="/ar/list-your-business.html">أرسل لنا رسالة</a>.</p>

<h2>ثنائي اللغة افتراضيًا</h2>
<p>كلّ صفحة متوفّرة بالإنجليزية والعربية. نخدم مجتمع قطر المتنوّع بالكامل.</p>

<h2>الصور وسياسة الإزالة</h2>
<p>الصور المعروضة في القوائم مأخوذة من صفحات خرائط جوجل المتاحة للعموم لمساعدة الزوّار على التعرّف على كلّ نشاط. نحن لا ندّعي ملكية أيّ صورة. إذا كنت صاحب نشاط أو صورة معروضة هنا وتريد تحديثها أو إزالتها، راسلنا على <a href="mailto:qatarpaw@gmail.com">qatarpaw@gmail.com</a> — سنردّ خلال 7 أيام.</p>
"""

    body = f"""<body>
{header_block(lang)}
<main id="main" role="main">
<section class="page-title">
<div class="wrap">
<div class="eyebrow">{esc(t['about_lead'])}</div>
<h1>{esc(t['about_h1'])}</h1>
</div>
</section>
<div class="wrap">
<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="{pre}/">{esc(t['bc_home'])}</a>
<span class="sep">›</span>
<span>{esc(t['about_h1'])}</span>
</nav>
<article class="prose">
{body_prose}
</article>
</div>
</main>
{footer_block(lang)}
</body>
</html>"""
    return head + "\n" + body


def build_blog(lang: str) -> str:
    t = UI[lang]
    pre = prefix(lang)
    title = f"{t['blog_h1']} | QatarPaws"
    # noindex for coming-soon
    robots = '<meta name="robots" content="noindex, follow">'
    head = head_block(lang=lang, title=title, description=t["blog_lead"], path=f"{pre}/blog/", og_type="website", extra_ldjson=[robots])
    body = f"""<body>
{header_block(lang)}
<main id="main" role="main">
<section class="page-title">
<div class="wrap">
<div class="eyebrow">{esc(t['editorial_eyebrow'])}</div>
<h1>{esc(t['blog_h1'])}</h1>
<p class="lead">{esc(t['blog_lead'])}</p>
</div>
</section>
<div class="wrap">
<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="{pre}/">{esc(t['bc_home'])}</a>
<span class="sep">›</span>
<span>{esc(t['blog_h1'])}</span>
</nav>
<div class="coming-soon">
<div class="glyph">📝</div>
<h2>{esc(t['blog_soon_h'])}</h2>
<p>{esc(t['blog_soon_p'])}</p>
</div>
</div>
</main>
{footer_block(lang)}
</body>
</html>"""
    return head + "\n" + body


def build_list(lang: str) -> str:
    t = UI[lang]
    pre = prefix(lang)
    subject = quote(t["list_mail_subject"])
    mail = f"mailto:hello@qatarpaws.com?subject={subject}"
    title = f"{t['list_h1']} | QatarPaws"
    head = head_block(lang=lang, title=title, description=t["list_lead"], path=f"{pre}/list-your-business.html", og_type="website")

    if lang == "en":
        prose = """
<h2>How it works</h2>
<ol>
<li>You email us the details of your business — name, address, phone, website, photos if you have them.</li>
<li>We verify against public records and Google Maps.</li>
<li>We publish your listing in both English and Arabic, free, usually within a week.</li>
</ol>

<h2>What we need from you</h2>
<ul>
<li>Business name (in English; Arabic also welcome)</li>
<li>Physical address in Qatar</li>
<li>Phone number and website (if any)</li>
<li>Which category fits (vet, pet shop, grooming, etc.)</li>
<li>2–3 photos (optional)</li>
<li>A 1-paragraph description (optional)</li>
</ul>

<h2>Why list with QatarPaws</h2>
<p>Free forever. Bilingual by default. Verified listings, real Google-synced reviews, mobile-friendly. No paid placement — we rank by genuine reviews, not by who pays. Your customers find you the same way you'd want to find a vet: by looking for the best, not the loudest.</p>
"""
    else:
        prose = """
<h2>كيف تعمل الخدمة</h2>
<ol>
<li>ترسل لنا بريدًا إلكترونيًا بتفاصيل نشاطك — الاسم، العنوان، الهاتف، الموقع، والصور إن وُجدت.</li>
<li>نتحقّق من السجلّات العامّة وجوجل مابس.</li>
<li>ننشر إدراجك بالعربية والإنجليزية، مجّانًا، خلال أسبوع عادةً.</li>
</ol>

<h2>ما نحتاجه منك</h2>
<ul>
<li>اسم النشاط (بالعربية و/أو الإنجليزية)</li>
<li>العنوان الفعلي في قطر</li>
<li>رقم الهاتف والموقع الإلكتروني (إن وُجد)</li>
<li>الفئة الأنسب (بيطري، متجر، عناية، إلخ)</li>
<li>٢–٣ صور (اختياري)</li>
<li>وصف بفقرة واحدة (اختياري)</li>
</ul>

<h2>لماذا قطر بوز</h2>
<p>مجّاني إلى الأبد. ثنائي اللغة افتراضيًا. إدراج موثَّق، وتقييمات حقيقية مزامَنة مع جوجل، ومُحسَّن للهواتف. لا إدراج مدفوع — نرتّب حسب التقييمات الحقيقية، لا حسب من يدفع. زبائنك يجدونك بنفس الطريقة التي تبحث بها عن طبيب بيطري: بالبحث عن الأفضل، لا عن الأعلى صوتًا.</p>
"""

    body = f"""<body>
{header_block(lang)}
<main id="main" role="main">
<section class="page-title">
<div class="wrap">
<div class="eyebrow">{esc(t['list_lead'])}</div>
<h1>{esc(t['list_h1'])}</h1>
<div style="margin-top:22px"><a href="{mail}" class="btn primary">{esc(t['list_cta'])} →</a></div>
</div>
</section>
<div class="wrap">
<nav class="breadcrumb" aria-label="Breadcrumb">
<a href="{pre}/">{esc(t['bc_home'])}</a>
<span class="sep">›</span>
<span>{esc(t['list_h1'])}</span>
</nav>
<article class="prose">
{prose}
<p style="margin-top:28px"><a href="{mail}" class="btn maroon">{esc(t['list_cta'])} →</a></p>
</article>
</div>
</main>
{footer_block(lang)}
</body>
</html>"""
    return head + "\n" + body


# ---------- SITEMAP + MANIFEST + FAVICON -------------------------------------

def regenerate_sitemap(business_files: list[Path]) -> str:
    entries = []
    def add(loc: str, lastmod: str, changefreq: str, priority: str):
        entries.append(f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>")
    # Home
    add(f"{SITE}/", BUILD_DATE, "weekly", "1.0")
    add(f"{SITE}/ar/", BUILD_DATE, "weekly", "1.0")
    # Static pages
    for p in ["about.html", "blog/", "list-your-business.html"]:
        add(f"{SITE}/{p}", BUILD_DATE, "monthly", "0.7")
        add(f"{SITE}/ar/{p}", BUILD_DATE, "monthly", "0.7")
    # Category pages
    for c in CATS:
        add(f"{SITE}/{c['slug']}/", BUILD_DATE, "weekly", "0.8")
        add(f"{SITE}/ar/{c['slug']}/", BUILD_DATE, "weekly", "0.8")
    # Businesses (URL-encode path segments)
    for f in business_files:
        slug = f.stem
        enc = quote(slug, safe="-_")
        add(f"{SITE}/business/{enc}.html", BUILD_DATE, "monthly", "0.6")
        add(f"{SITE}/ar/business/{enc}.html", BUILD_DATE, "monthly", "0.6")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(entries) + "\n</urlset>\n"


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
<circle cx="20" cy="20" r="19" fill="#141210"/>
<g fill="#F6F1E8">
<ellipse cx="13" cy="15.5" rx="2.6" ry="3.4"/>
<ellipse cx="20" cy="12.5" rx="2.6" ry="3.4"/>
<ellipse cx="27" cy="15.5" rx="2.6" ry="3.4"/>
<ellipse cx="30.5" cy="22" rx="2.3" ry="3"/>
<path d="M20 18c-5 0-8.5 3.6-8.5 7.6 0 2.8 2.2 4.4 5 4.4 1.7 0 2.5-.7 3.5-.7s1.8.7 3.5.7c2.8 0 5-1.6 5-4.4 0-4-3.5-7.6-8.5-7.6z"/>
</g>
<circle cx="30" cy="11" r="1.4" fill="#7B1E1E"/>
</svg>"""

OG_DEFAULT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
<defs>
<pattern id="grain" x="0" y="0" width="7" height="7" patternUnits="userSpaceOnUse">
<circle cx="1" cy="1" r="0.5" fill="rgba(120,80,40,.14)"/>
<circle cx="4" cy="3" r="0.5" fill="rgba(120,80,40,.10)"/>
</pattern>
</defs>
<rect width="1200" height="630" fill="#F3EBDD"/>
<rect width="1200" height="630" fill="url(#grain)"/>
<g transform="translate(120 160)">
<circle cx="60" cy="60" r="58" fill="#141210"/>
<g fill="#F6F1E8">
<ellipse cx="38" cy="46" rx="8" ry="10"/>
<ellipse cx="60" cy="37" rx="8" ry="10"/>
<ellipse cx="82" cy="46" rx="8" ry="10"/>
<ellipse cx="92" cy="66" rx="7" ry="9"/>
<path d="M60 55c-15 0-25 11-25 23 0 9 7 13 15 13 5 0 8-2 10-2s5 2 10 2c8 0 15-4 15-13 0-12-10-23-25-23z"/>
</g>
<circle cx="88" cy="23" r="4" fill="#7B1E1E"/>
</g>
<text x="120" y="380" font-family="Georgia, serif" font-size="96" font-weight="500" fill="#141210" letter-spacing="-2">QatarPaws</text>
<text x="120" y="440" font-family="Georgia, serif" font-size="36" font-style="italic" fill="#7B1E1E">The Pet Guide to Qatar</text>
<text x="120" y="510" font-family="monospace" font-size="20" fill="#5a4838" letter-spacing="3">267 VERIFIED PLACES · EN · AR</text>
</svg>"""

WEBMANIFEST = {
    "name": "QatarPaws — The Pet Guide to Qatar",
    "short_name": "QatarPaws",
    "description": "Qatar's bilingual directory of pet services.",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#F3EBDD",
    "theme_color": "#F6F1E8",
    "icons": [
        {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml"}
    ],
}


# ---------- MAIN -------------------------------------------------------------

def collect_businesses() -> list[dict]:
    out: list[dict] = []
    for d in ["business", "ar/business"]:
        dp = ROOT / d
        if not dp.exists():
            continue
        for f in dp.glob("*.html"):
            b = extract_business(f)
            if b and b.get("name"):
                out.append(b)
    return out


def write_file(relpath: str, content: str) -> None:
    p = ROOT / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main() -> None:
    # 1. Collect all business data from existing pages
    print("[1/7] Extracting businesses from existing HTML …", flush=True)
    all_businesses = collect_businesses()
    print(f"      found {len(all_businesses)} business pages")

    # 2. Compute per-category counts (per lang — use EN count as canonical since AR mirrors)
    counts = {}
    for c in CATS:
        counts[c["slug"]] = sum(1 for b in all_businesses if b["lang"] == "en" and b.get("cat_slug") == c["slug"])

    # 3. Homepages
    print("[2/7] Building homepages …", flush=True)
    write_file("index.html",       build_homepage("en", all_businesses, counts))
    write_file("ar/index.html",    build_homepage("ar", all_businesses, counts))

    # 4. Category pages
    print("[3/7] Building category pages …", flush=True)
    for c in CATS:
        en_list = [b for b in all_businesses if b["lang"] == "en" and b.get("cat_slug") == c["slug"]]
        ar_list = [b for b in all_businesses if b["lang"] == "ar" and b.get("cat_slug") == c["slug"]]
        write_file(f"{c['slug']}/index.html",    build_category("en", c["slug"], en_list, counts))
        write_file(f"ar/{c['slug']}/index.html", build_category("ar", c["slug"], ar_list, counts))

    # 5. Business detail pages
    print(f"[4/7] Building {len(all_businesses)} business pages …", flush=True)
    n_ok = 0
    for b in all_businesses:
        try:
            html_out = build_business(b, all_businesses)
            rel = str(Path(b["file"]).relative_to(ROOT)).replace("\\", "/")
            write_file(rel, html_out)
            n_ok += 1
        except Exception as e:
            print(f"      WARN: {b.get('name','?')} ({b.get('file')}): {e}")
    print(f"      wrote {n_ok} pages")

    # 6. About, Blog, List-your-business
    print("[5/7] Building about / blog / list pages …", flush=True)
    write_file("about.html",                 build_about("en"))
    write_file("ar/about.html",              build_about("ar"))
    write_file("blog/index.html",            build_blog("en"))
    write_file("ar/blog/index.html",         build_blog("ar"))
    write_file("list-your-business.html",    build_list("en"))
    write_file("ar/list-your-business.html", build_list("ar"))

    # 7. Assets: favicon, webmanifest, OG image, sitemap
    print("[6/7] Writing assets + sitemap …", flush=True)
    write_file("favicon.svg", FAVICON_SVG)
    write_file("site.webmanifest", json.dumps(WEBMANIFEST, ensure_ascii=False, indent=2))
    write_file("images/og-default.svg", OG_DEFAULT_SVG)
    business_files = [ROOT / b["file"] for b in all_businesses if b["lang"] == "en"]
    sitemap_xml = regenerate_sitemap(business_files)
    write_file("sitemap.xml", sitemap_xml)

    print("[7/7] Done.", flush=True)
    print(f"      Total pages rewritten: ~{2 + 22 + n_ok + 6}")


if __name__ == "__main__":
    main()
