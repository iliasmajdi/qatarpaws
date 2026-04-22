#!/bin/bash
cd "business"
count=0

for file in *.html; do
  # Extract first image URL (this is the hero image)
  img_url=$(grep -oP '<img src="\K[^"]+' "$file" | head -1)

  # Only process if we found an image and the schema doesn't already have an image field
  if [ -n "$img_url" ] && ! grep -q '"image"' "$file"; then
    # Add image field to LocalBusiness schema before the closing brace
    # We insert it after the "url" field
    perl -i -pe 's|("url": "https://qatarpaws\.com/business/[^"]+")}\Q</script>\E|$1, "image": "'"$img_url"'"}</script>|' "$file"
    count=$((count+1))
  fi
done

echo "Added images to $count English business schemas"
