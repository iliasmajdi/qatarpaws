#!/usr/bin/env python3
import os
import json
import re
import glob
import html as htmllib
from html.parser import HTMLParser

class BusinessExtractor(HTMLParser):
    """Extract business information from HTML"""
    def __init__(self):
        super().__init__()
        self.business = {}
        self.in_title = False
        self.in_localbusiness = False
        self.json_content = ""

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        elif tag == "script":
            for attr, value in attrs:
                if attr == "type" and value == "application/ld+json":
                    self.in_localbusiness = True

    def handle_data(self, data):
        if self.in_title:
            # Extract business name from title (before |)
            match = re.match(r'(.+?)\s*\|', data)
            if match:
                self.business['name'] = match.group(1).strip()
        elif self.in_localbusiness:
            self.json_content += data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_localbusiness:
            self.in_localbusiness = False
            # Parse JSON-LD
            try:
                data = json.loads(self.json_content)
                if data.get('@type') == 'LocalBusiness':
                    self.business['phone'] = data.get('telephone', '')
                    rating_data = data.get('aggregateRating', {})
                    self.business['rating'] = float(rating_data.get('ratingValue', 0))
                    self.business['reviews'] = int(rating_data.get('reviewCount', 0))
            except:
                pass
            self.json_content = ""

def extract_category_from_breadcrumb(html_content):
    """Extract category name from breadcrumb (supports new + legacy markup)."""
    # New markup: <a href="/vets/">Veterinary Clinics</a><span class="sep">›</span><span>...
    match = re.search(r'<nav class="breadcrumb"[^>]*>.*?<a href="(?:/ar)?/([^/]+)/"[^>]*>([^<]+)</a>', html_content, re.DOTALL)
    if match:
        return htmllib.unescape(match.group(2).strip())
    # Legacy: <a href="/category/">Label</a> <span>›</span> <span>
    match = re.search(r'href="/([^/]+)/">([^<]+)</a>\s*<span>›</span>\s*<span>', html_content)
    if match:
        return htmllib.unescape(match.group(2).strip())
    return "Other"

def extract_business_data(filepath):
    """Extract business data from a single HTML file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    parser = BusinessExtractor()
    parser.feed(content)

    business = parser.business

    # Extract category from breadcrumb
    business['category'] = extract_category_from_breadcrumb(content)

    # Build URL from filepath
    rel_path = os.path.relpath(filepath, '.')
    rel_path = rel_path.replace('\\', '/')
    business['url'] = f'/{rel_path}'

    return business

def main():
    businesses = []

    # Process English business pages
    os.chdir('business')
    for filepath in glob.glob('*.html'):
        try:
            business = extract_business_data(filepath)
            if business.get('name'):
                business['lang'] = 'en'
                businesses.append(business)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # Process Arabic business pages
    os.chdir('../ar/business')
    for filepath in glob.glob('*.html'):
        try:
            business = extract_business_data(filepath)
            if business.get('name'):
                business['lang'] = 'ar'
                businesses.append(business)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # Sort by rating descending
    businesses.sort(key=lambda x: x.get('rating', 0), reverse=True)

    # Write to JSON file
    os.chdir('../..')
    output_path = 'js/search-data.json'
    os.makedirs('js', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(businesses, f, ensure_ascii=False, indent=2)

    print(f"Generated search data with {len(businesses)} businesses")
    print(f"Output: {output_path}")

if __name__ == '__main__':
    main()
