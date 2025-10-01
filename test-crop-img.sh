#!/usr/bin/env bash
set -euo pipefail

# Structured test script similar to test.sh style

IMAGE_PATH="/Users/macbook/Documents/ocr-cccd-card/test-model/img/7739.jpg"
WEIGHTS="/Users/macbook/Documents/ocr-cccd-card/weights/models/best-corner-detect.pt"
DEVICE="cpu"
OUTPUT_DIR="/Users/macbook/Documents/ocr-cccd-card/cropped"
CONF=0.4
EXPAND=0.1
ASPECT=1.585
mkdir -p "$OUTPUT_DIR"

python /Users/macbook/Documents/ocr-cccd-card/stages/crop.py \
    "$IMAGE_PATH" \
    --model "$WEIGHTS" \
    --device "$DEVICE" \
    --conf "$CONF" \
    --expand "$EXPAND" \
    --aspect "$ASPECT" \
    --out "$OUTPUT_DIR/$(basename "${IMAGE_PATH%.*}")_cropped.jpg" | cat
