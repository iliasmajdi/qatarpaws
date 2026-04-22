#!/bin/bash

# Add accessibility features to all HTML files
# - Skip to content link
# - ARIA roles

count=0

# Process all HTML files recursively
while IFS= read -r file; do
  # Check if already has skip-link (skip if already added)
  if grep -q 'skip-link' "$file"; then
    continue
  fi

  # Determine language for skip-link text
  if [[ "$file" == *"/ar/"* ]]; then
    skip_text="تخطى إلى المحتوى الرئيسي"
  else
    skip_text="Skip to main content"
  fi

  # Add skip-link after <body>
  perl -i -pe "s|<body>|<body>\n<a href=\"#main-content\" class=\"skip-link\">$skip_text</a>|" "$file"

  # Add ARIA role to header
  perl -i -pe 's|<header class="header">|<header class="header" role="banner">|' "$file"

  # Add ARIA role to header-nav
  perl -i -pe 's|<div class="header-nav">|<div class="header-nav" role="navigation" aria-label="Main navigation">|' "$file"

  # Add ARIA role and id to main container
  # Try different main container patterns
  perl -i -pe 's|<main class="container"([^>]*)>|<main class="container"$1 id="main-content" role="main">|' "$file"
  perl -i -pe 's|<div class="container"([^>]*)(style="[^"]*")>|<div class="container"$1$2 id="main-content" role="main">|' "$file"

  # Add ARIA role to footer
  perl -i -pe 's|<footer class="footer">|<footer class="footer" role="contentinfo">|' "$file"

  count=$((count+1))
done < <(find . -name "*.html" -type f)

echo "Added accessibility features to $count pages"
