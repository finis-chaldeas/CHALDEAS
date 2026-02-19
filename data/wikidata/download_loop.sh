#!/bin/bash
# Wikidata 다운로드 자동 재시도 스크립트

URL="https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2"
OUTPUT="C:/Projects/Chaldeas/data/wikidata/latest-all.json.bz2"
TARGET_SIZE=99911199739  # 93GB

while true; do
    CURRENT_SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || echo 0)

    if [ "$CURRENT_SIZE" -ge "$TARGET_SIZE" ]; then
        echo "Download complete! Size: $CURRENT_SIZE"
        break
    fi

    echo "Current size: $CURRENT_SIZE / $TARGET_SIZE bytes"
    echo "Resuming download..."

    curl -L -C - --retry 10 --retry-delay 5 -o "$OUTPUT" "$URL"

    echo "Connection lost. Waiting 5 seconds before retry..."
    sleep 5
done

echo "Done!"
