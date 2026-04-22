#!/bin/bash

# Add performance optimizations to all HTML files
# - Preload CSS
# - DNS-prefetch hints

count=0

# Process all HTML files recursively
while IFS= read -r file; do
  # Check if already has preload (skip if already added)
  if grep -q 'rel="preload"' "$file"; then
    continue
  fi

  # Add preload and dns-prefetch before the stylesheet link
  perl -i -pe 'if (/<link rel="stylesheet" href="\/css\/style.css">/) {
    print qq{<link rel="preload" href="/css/style.css" as="style">\n};
    print qq{<link rel="dns-prefetch" href="https://fonts.googleapis.com">\n};
    print qq{<link rel="dns-prefetch" href="https://fonts.gstatic.com">\n};
    print qq{<link rel="dns-prefetch" href="https://lh3.googleusercontent.com">\n};
    print qq{<link rel="dns-prefetch" href="https://maps.google.com">\n};
  }' "$file"

  count=$((count+1))
done < <(find . -name "*.html" -type f)

echo "Added performance optimizations to $count pages"
