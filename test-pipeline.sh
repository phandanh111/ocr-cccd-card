#!/usr/bin/env bash
set -euo pipefail

# Mirror style of test.sh and test-crop-img.sh

source /Users/macbook/Documents/ocr-cccd-card/myenv/bin/activate

# Inputs
IMAGE_PATH="/Users/macbook/Documents/ocr-cccd-card/test-model/img/7739.jpg"
OUTPUT_JSON="/Users/macbook/Documents/ocr-cccd-card/output_pipeline.json"

# Crop stage params (detect 4 corners and warp)
CROP_WEIGHTS="/Users/macbook/Documents/ocr-cccd-card/weights/models/best-corner-detect.pt"
CROP_DEVICE="cpu"
CROP_CONF=0.4
CROP_EXPAND=0.1
CROP_ASPECT=1.585

# OCR stage params (detect fields + VietOCR)
OCR_WEIGHTS="/Users/macbook/Documents/ocr-cccd-card/weights/models/best-fields-detect.pt"
OCR_DEVICE="cpu"
OCR_CONF=0.4
OCR_IOU=0.5

echo "Running full pipeline (crop -> OCR)..."
python /Users/macbook/Documents/ocr-cccd-card/pipeline-ocr-cccd.py \
  --image "$IMAGE_PATH" \
  --output "$OUTPUT_JSON" \
  --crop-model "$CROP_WEIGHTS" \
  --crop-device "$CROP_DEVICE" \
  --crop-conf "$CROP_CONF" \
  --crop-expand "$CROP_EXPAND" \
  --crop-aspect "$CROP_ASPECT" \
  --weights "$OCR_WEIGHTS" \
  --device "$OCR_DEVICE" \
  --conf "$OCR_CONF" \
  --iou "$OCR_IOU" | cat

echo "Saved to $OUTPUT_JSON"


