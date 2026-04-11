#!/bin/bash

# Add Google Analytics 4 and Search Console to all HTML files

count=0

# Process all HTML files recursively
while IFS= read -r file; do
  # Check if already has GA4 (skip if already added)
  if grep -q 'gtag/js' "$file"; then
    continue
  fi

  # Add GA4 and Search Console meta before </head>
  perl -i -pe 'if (/<\/head>/) {
    print qq{<!-- Google Analytics 4 -->\n};
    print qq{<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>\n};
    print qq{<script>\n};
    print qq{  window.dataLayer = window.dataLayer || [];\n};
    print qq{  function gtag(){dataLayer.push(arguments);}\n};
    print qq{  gtag('\''js'\'', new Date());\n};
    print qq{  gtag('\''config'\'', '\''G-XXXXXXXXXX'\'');\n};
    print qq{</script>\n};
    print qq{<!-- Google Search Console -->\n};
    print qq{<meta name="google-site-verification" content="PLACEHOLDER_VERIFICATION_CODE">\n};
  }' "$file"

  count=$((count+1))
done < <(find . -name "*.html" -type f)

echo "Added analytics to $count pages"
