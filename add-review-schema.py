#!/usr/bin/env python3
import re
import json
import html
import glob
import os

def count_stars(star_string):
    """Count the number of ★ characters in the rating"""
    return star_string.count('★')

def extract_reviews_from_html(html_content):
    """Extract review data from HTML content"""
    reviews = []

    # Find all review-card divs with their content
    # Pattern matches from review-card opening to the next review-card or closing div
    pattern = r'<div class="review-card">\s*<div class="review-header"><span class="review-author">([^<]+)</span><span class="review-time">([^<]+)</span></div>\s*<div class="review-stars">([^<]+)</div>\s*<p class="review-text">([^<]+(?:<[^/]|[^<])*?)</p>'

    matches = re.finditer(pattern, html_content, re.DOTALL)

    for match in matches:
        author = html.unescape(match.group(1).strip())
        # time_ago = match.group(2).strip()  # We won't use relative dates
        stars_str = match.group(3).strip()
        review_text_raw = match.group(4).strip()

        # Clean up review text - remove quotes and decode HTML entities
        review_text = html.unescape(review_text_raw)
        review_text = review_text.strip('"\'')

        # Count stars for rating
        rating = count_stars(stars_str)

        if rating > 0 and author and review_text:
            reviews.append({
                "author": author,
                "rating": rating,
                "text": review_text
            })

    return reviews

def create_review_schema(review, business_url):
    """Create a Review schema object"""
    return {
        "@context": "https://schema.org",
        "@type": "Review",
        "author": {
            "@type": "Person",
            "name": review["author"]
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": str(review["rating"]),
            "bestRating": "5"
        },
        "reviewBody": review["text"],
        "itemReviewed": {
            "@type": "LocalBusiness",
            "url": business_url
        }
    }

def add_review_schemas_to_file(filepath, lang_prefix=""):
    """Add Review schemas to a business page"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if Review schema already exists
    if '"@type": "Review"' in content:
        return False

    # Extract business URL from canonical link
    url_match = re.search(r'<link rel="canonical" href="([^"]+)"', content)
    if not url_match:
        return False
    business_url = url_match.group(1)

    # Extract reviews
    reviews = extract_reviews_from_html(content)

    if not reviews:
        return False

    # Create Review schemas (limit to first 5 reviews to avoid bloat)
    review_schemas = []
    for review in reviews[:5]:
        schema = create_review_schema(review, business_url)
        review_schemas.append(schema)

    # Convert to JSON strings
    json_scripts = []
    for schema in review_schemas:
        json_str = json.dumps(schema, ensure_ascii=False, indent=2)
        json_scripts.append(f'<script type="application/ld+json">\n{json_str}\n</script>')

    # Insert after the LocalBusiness schema (before </head>)
    # Find the LocalBusiness schema closing tag
    localbusiness_pattern = r'(<script type="application/ld+json">\{[^}]*"@type": "LocalBusiness"[^<]*</script>)'
    match = re.search(localbusiness_pattern, content)

    if match:
        insert_pos = match.end()
        new_content = content[:insert_pos] + '\n' + '\n'.join(json_scripts) + content[insert_pos:]

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    return False

# Process English business pages
os.chdir('business')
count = 0
for filepath in glob.glob('*.html'):
    if add_review_schemas_to_file(filepath):
        count += 1

print(f"Added review schemas to {count} English business pages")

# Process Arabic business pages
os.chdir('../ar/business')
count_ar = 0
for filepath in glob.glob('*.html'):
    if add_review_schemas_to_file(filepath, "/ar"):
        count_ar += 1

print(f"Added review schemas to {count_ar} Arabic business pages")
print(f"Total: {count + count_ar} pages updated")
