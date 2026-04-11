#!/usr/bin/env python3
import re
from html.parser import HTMLParser

# Category priority order (lower number = higher priority)
CATEGORY_PRIORITY = {
    'Veterinary Clinics': 1,
    'العيادات البيطرية': 1,
    'Pet Shops & Stores': 2,
    'متاجر الحيوانات الأليفة': 2,
    'Pet Grooming': 3,
    'العناية بالحيوانات': 3,
    'Pet Boarding & Daycare': 4,
    'إيواء الحيوانات': 4,
    'Pet Sitting': 5,
    'رعاية الحيوانات': 5,
    'Rescue & Adoption': 6,
    'الإنقاذ والتبني': 6,
    'Pet Relocation': 7,
    'نقل الحيوانات': 7,
    'Pet-Friendly Cafés': 8,
    'مقاهي صديقة للحيوانات': 8,
    'Pet-Friendly Hotels': 9,
    'فنادق صديقة للحيوانات': 9,
    'Parks & Outdoor': 10,
    'حدائق ومتنزهات': 10,
}

def extract_rating(card_html):
    """Extract rating from card HTML"""
    match = re.search(r'<span class="star">★</span>\s*([0-9.]+)', card_html)
    if match:
        return float(match.group(1))
    return 0.0

def extract_category(card_html):
    """Extract category from card HTML"""
    match = re.search(r'<div class="card-cat">([^<]+)</div>', card_html)
    if match:
        return match.group(1).strip()
    return "Other"

def get_category_priority(category):
    """Get priority for a category (lower = higher priority)"""
    return CATEGORY_PRIORITY.get(category, 999)

def reorder_homepage_cards(filepath):
    """Reorder business cards on homepage by category priority"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the grid section with all business cards
    grid_match = re.search(r'(<div class="grid">)(.*?)(</div>\s*</main>)', content, re.DOTALL)

    if not grid_match:
        print(f"Could not find grid in {filepath}")
        return False

    before_grid = content[:grid_match.start(1)]
    grid_start = grid_match.group(1)
    cards_html = grid_match.group(2)
    after_grid = grid_match.group(3) + content[grid_match.end(3):]

    # Extract individual card HTML blocks
    # Each card starts with <a href="/business/ and ends with </a>
    card_pattern = r'<a href="[^"]*business/[^"]+\.html" class="card">.*?</a>'
    cards = re.findall(card_pattern, cards_html, re.DOTALL)

    if not cards:
        print(f"No cards found in {filepath}")
        return False

    print(f"Found {len(cards)} cards in {filepath}")

    # Extract category and rating for each card
    card_data = []
    for card in cards:
        category = extract_category(card)
        rating = extract_rating(card)
        priority = get_category_priority(category)
        card_data.append({
            'html': card,
            'category': category,
            'rating': rating,
            'priority': priority
        })

    # Sort by:
    # 1. Category priority (ascending - lower number first)
    # 2. Rating (descending - higher rating first)
    card_data.sort(key=lambda x: (x['priority'], -x['rating']))

    # Print first 15 for verification
    print(f"\nFirst 15 businesses after reordering:")
    for i, card in enumerate(card_data[:15], 1):
        try:
            print(f"{i}. {card['category']} - Rating: {card['rating']}")
        except UnicodeEncodeError:
            print(f"{i}. [Category] - Rating: {card['rating']}")

    # Rebuild the grid with sorted cards
    sorted_cards_html = '\n'.join(card['html'] for card in card_data)

    # Reconstruct the full HTML
    new_content = before_grid + grid_start + '\n' + sorted_cards_html + '\n' + after_grid

    # Write back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\nSuccessfully reordered {filepath}")
    return True

def main():
    # Reorder English homepage
    print("=" * 60)
    print("REORDERING ENGLISH HOMEPAGE")
    print("=" * 60)
    reorder_homepage_cards('index.html')

    # Reorder Arabic homepage
    print("\n" + "=" * 60)
    print("REORDERING ARABIC HOMEPAGE")
    print("=" * 60)
    reorder_homepage_cards('ar/index.html')

if __name__ == '__main__':
    main()
