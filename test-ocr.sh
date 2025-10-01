#!/usr/bin/env bash

set -euo pipefail

source /Users/macbook/Documents/ocr-cccd-card/myenv/bin/activate

echo "Running OCR pipeline..."

python /Users/macbook/Documents/ocr-cccd-card/stages/ocr.py \
    --image /Users/macbook/Documents/ocr-cccd-card/test-model/img/101689.PNG \
    --weights /Users/macbook/Documents/ocr-cccd-card/weights/models/best-fields-detect.pt \
    --device cpu \
    --ocr-conf 0.4 \
    --output /Users/macbook/Documents/ocr-cccd-card/output_ocr.json | cat 

echo "Saved to /Users/macbook/Documents/ocr-cccd-card/output_ocr.json"

