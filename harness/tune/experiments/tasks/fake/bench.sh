#!/usr/bin/env bash
# 偽のベンチマーカー。{"pass": bool, "score": N} を出す。
wd=$1
speed=$(cat "$wd/speed.txt" 2>/dev/null || echo 0)
score=$(awk -v s="$speed" -v r="$RANDOM" 'BEGIN{printf "%d", s * (0.95 + (r % 1000) / 10000)}')
if [ -e "$wd/broken.txt" ]; then
  echo '{"pass": false, "score": 0, "error": "GET /api/items returned 500"}'; exit 1
fi
echo "{\"pass\": true, \"score\": $score}"
