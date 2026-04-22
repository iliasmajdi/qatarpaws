#!/bin/bash
cd "ar/business"
count=0

for file in *.html; do
  # Extract business name from title
  biz_name=$(grep -oP '<title>\K[^|]+' "$file" | sed 's/ *$//')

  # Extract category name from breadcrumb
  cat_name=$(grep -oP 'href="/ar/[^/]+/">\K[^<]+' "$file" | head -1)

  # Extract category URL
  cat_url=$(grep -oP 'href="\K/ar/[^/]+/' "$file" | head -1)

  # Add breadcrumb schema before </head>
  awk -v biz="$biz_name" -v cat="$cat_name" -v caturl="$cat_url" '
  {
    if (/<\/head>/ && !done) {
      print "<script type=\"application/ld+json\">"
      print "{"
      print "  \"@context\": \"https://schema.org\","
      print "  \"@type\": \"BreadcrumbList\","
      print "  \"itemListElement\": ["
      print "    {"
      print "      \"@type\": \"ListItem\","
      print "      \"position\": 1,"
      print "      \"name\": \"الرئيسية\","
      print "      \"item\": \"https://qatarpaws.com/ar/\""
      print "    },"
      print "    {"
      print "      \"@type\": \"ListItem\","
      print "      \"position\": 2,"
      print "      \"name\": \"" cat "\","
      print "      \"item\": \"https://qatarpaws.com" caturl "\""
      print "    },"
      print "    {"
      print "      \"@type\": \"ListItem\","
      print "      \"position\": 3,"
      print "      \"name\": \"" biz "\""
      print "    }"
      print "  ]"
      print "}"
      print "</script>"
      done=1
    }
    print
  }' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

  count=$((count+1))
done

echo "Processed $count Arabic business pages"
