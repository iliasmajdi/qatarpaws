#!/bin/bash

# Add Blog links to header nav and footer on all pages
# Skip pages that already have Blog links (blog/index.html, about.html)

count=0

while IFS= read -r file; do
  # Skip if already has Blog link
  if grep -q 'href="/blog/"' "$file" || grep -q 'href="/ar/blog/"' "$file"; then
    continue
  fi

  # Determine if this is an Arabic page
  is_arabic=false
  if [[ "$file" == *"/ar/"* ]]; then
    is_arabic=true
  fi

  # Add Blog link to header nav
  # Insert before the language switcher button
  if [ "$is_arabic" = true ]; then
    # Arabic page: add Arabic blog link
    perl -i -pe 's|(<a href="/#categories" class="nav-link">الفئات</a>)|$1\n<a href="/ar/blog/" class="nav-link">المدونة</a>|' "$file"
    # Also update if pattern is /ar/#categories
    perl -i -pe 's|(<a href="/ar/#categories" class="nav-link">الفئات</a>)|$1\n<a href="/ar/blog/" class="nav-link">المدونة</a>|' "$file"
  else
    # English page: add English blog link
    perl -i -pe 's|(<a href="/#categories" class="nav-link">Categories</a>)|$1\n<a href="/blog/" class="nav-link">Blog</a>|' "$file"
  fi

  # Add Blog link to footer Quick Links
  # Insert after Home link
  if [ "$is_arabic" = true ]; then
    perl -i -pe 's|(<li><a href="/ar/">الرئيسية</a></li>)|$1<li><a href="/ar/blog/">المدونة</a></li>|' "$file"
  else
    perl -i -pe 's|(<li><a href="/">Home</a></li>)|$1\n<li><a href="/blog/">Blog</a></li>|' "$file"
  fi

  count=$((count+1))
done < <(find . -name "*.html" -type f ! -path "./blog/*" ! -path "./ar/blog/*" ! -path "./about.html" ! -path "./ar/about.html")

echo "Added Blog links to $count pages"
