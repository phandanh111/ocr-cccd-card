import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

# Pillow 10+ removed Image.ANTIALIAS; some libs still reference it.
# Provide a compatibility alias to avoid runtime errors inside VietOCR.
try:
    _ = Image.ANTIALIAS  # type: ignore[attr-defined]
except AttributeError:
    try:
        Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
    except Exception:
        pass

from ultralytics import YOLO

from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg


DESIRED_FIELDS = [
    "id",
    "name",
    "dob",
    "gender",
    "nationality",
    "origin_place",
    "current_place",
    "expire_date",
    "issue_date",
]

# Fields that may appear in multiple stacked boxes and should be merged
MULTILINE_FIELDS = {
    "name",
    "origin_place",
    "current_place",
}


def clamp_bbox(xyxy: np.ndarray, width: int, height: int) -> np.ndarray:
    x1, y1, x2, y2 = xyxy.tolist()
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width - 1))
    y2 = max(0, min(y2, height - 1))
    if x2 <= x1:
        x2 = min(width - 1, x1 + 1)
    if y2 <= y1:
        y2 = min(height - 1, y1 + 1)
    return np.array([x1, y1, x2, y2], dtype=np.int32)


def pad_bbox(xyxy: np.ndarray, width: int, height: int, pad_ratio: float = 0.04) -> np.ndarray:
    x1, y1, x2, y2 = xyxy.astype(float)
    w = x2 - x1
    h = y2 - y1
    pad_w = w * pad_ratio
    pad_h = h * pad_ratio
    x1 -= pad_w
    y1 -= pad_h
    x2 += pad_w
    y2 += pad_h
    return clamp_bbox(np.array([x1, y1, x2, y2]), width, height)


def init_vietocr(device: str = "cpu") -> Predictor:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    base_cfg_path = project_root / "configs/base.yml"
    model_cfg_path = project_root / "configs/vgg-transformer.yml"
    vocab_path = project_root / "configs/vocab/vi.yml"

    base_cfg = Cfg.load_config_from_file(str(base_cfg_path))
    model_cfg = Cfg.load_config_from_file(str(model_cfg_path))
    cfg = {**base_cfg, **model_cfg}
    cfg["device"] = device
    cfg["cnn"]["pretrained"] = True
    cfg.setdefault("predictor", {})["beamsearch"] = False
    cfg.setdefault("vocab", str(vocab_path))
    local_vietocr_weights = project_root / "weights/vgg_transformer.pth"
    if local_vietocr_weights.exists():
        cfg["weights"] = str(local_vietocr_weights)
    return Predictor(cfg)


def predict_with_confidence(ocr, image):
    """
    Predict text with confidence score from VietOCR
    Returns (text, confidence_score)
    """
    try:
        # Get prediction with beam search to get confidence
        result = ocr.predict(image, return_prob=True)
        if isinstance(result, tuple):
            text, confidence = result
        else:
            text = result
            # Estimate confidence based on text length and character patterns
            confidence = estimate_confidence(text)
        return text, confidence
    except Exception as e:
        return "", 0.0


def estimate_confidence(text):
    """
    Estimate confidence based on text characteristics
    This is a heuristic approach since VietOCR doesn't always return confidence
    """
    if not text or len(text.strip()) == 0:
        return 0.0
    
    confidence = 0.5  # Base confidence
    
    # Increase confidence for common patterns
    if any(char.isdigit() for char in text):  # Contains numbers
        confidence += 0.1
    if any(char.isalpha() for char in text):  # Contains letters
        confidence += 0.1
    if len(text) > 3:  # Reasonable length
        confidence += 0.1
    if not any(char in text for char in ['?', '!', '@', '#', '$', '%']):  # No special chars
        confidence += 0.1
    if text.count(' ') <= len(text) // 4:  # Not too many spaces
        confidence += 0.1
    
    # Decrease confidence for suspicious patterns
    if text.count('?') > 0:  # Contains question marks (uncertainty)
        confidence -= 0.2
    if len(text) < 2:  # Too short
        confidence -= 0.2
    if text.count(' ') > len(text) // 2:  # Too many spaces
        confidence -= 0.1
    
    return max(0.0, min(1.0, confidence))


def run(image_path: str, weights: str, device: str, conf: float, iou: float, output_json: str, ocr_conf_threshold: float = 0.4) -> None:
    image_path = str(Path(image_path).expanduser().resolve())
    output_json = str(Path(output_json).expanduser().resolve())

    model = YOLO(str(Path(weights).expanduser().resolve()))
    ocr = init_vietocr(device=device)

    image = Image.open(image_path).convert("RGB")
    width, height = image.size
 
    results = model.predict(source=image_path, conf=conf, iou=iou, imgsz=640, device=device, verbose=False)
    result = results[0]

    class_id_to_name = {int(k): v for k, v in result.names.items()} if hasattr(result, "names") else model.model.names
 
    field_to_bboxes = {k: [] for k in DESIRED_FIELDS}
    field_to_text = {k: "" for k in DESIRED_FIELDS}
    field_to_confidence = {k: 0.0 for k in DESIRED_FIELDS}
    field_to_ocr_confidence = {k: 0.0 for k in DESIRED_FIELDS}

    if result.boxes is not None and len(result.boxes) > 0:
        for box in result.boxes:
            cls_id = int(box.cls.item())
            conf_score = float(box.conf.item())
            label = class_id_to_name.get(cls_id, str(cls_id))
            # Allow labels outside DESIRED_FIELDS
            if label not in field_to_bboxes:
                field_to_bboxes[label] = []
                field_to_text.setdefault(label, "")
                field_to_confidence.setdefault(label, 0.0)
                field_to_ocr_confidence.setdefault(label, 0.0)
            
            # Only process boxes with confidence > ocr_conf_threshold
            if conf_score <= ocr_conf_threshold:
                continue
                
            xyxy = box.xyxy.squeeze().cpu().numpy()
           
            padded = pad_bbox(xyxy, width, height)
            if label in MULTILINE_FIELDS:
                field_to_bboxes[label].append((padded, conf_score))
            else:
                if not field_to_bboxes[label] or conf_score > field_to_bboxes[label][0][1]:
                    field_to_bboxes[label] = [(padded, conf_score)]
                    field_to_confidence[label] = conf_score  # Store best confidence for single-line fields

    
    for label, bbox_items in field_to_bboxes.items():
        if not bbox_items:
            continue
       
        bbox_items_sorted = sorted(bbox_items, key=lambda item: item[0][1])
        texts = []
        yolo_confidences = []
        ocr_confidences = []
        
        for bbox, conf_score in bbox_items_sorted:
            x1, y1, x2, y2 = bbox.tolist()
            crop = image.crop((x1, y1, x2, y2))
            
            # Preprocessing for better OCR accuracy
            # 1. Convert to grayscale
            crop_gray = crop.convert('L')
            
            # 2. Resize if too small (minimum 32px height for better OCR)
            if crop_gray.height < 32:
                ratio = 32 / crop_gray.height
                new_width = int(crop_gray.width * ratio)
                crop_gray = crop_gray.resize((new_width, 32), Image.Resampling.LANCZOS)
            
            # 3. Enhance contrast
            enhancer = ImageEnhance.Contrast(crop_gray)
            crop_gray = enhancer.enhance(1.2)  # Increase contrast by 20%
            
            # Get text and OCR confidence
            text, ocr_conf = predict_with_confidence(ocr, crop_gray)
            
            if text:
                texts.append(text)
                yolo_confidences.append(conf_score)
                ocr_confidences.append(ocr_conf)
       
        field_to_text[label] = " ".join(texts).strip()
        
        # Calculate average confidences for multiline fields
        if label in MULTILINE_FIELDS and yolo_confidences:
            field_to_confidence[label] = sum(yolo_confidences) / len(yolo_confidences)
            field_to_ocr_confidence[label] = sum(ocr_confidences) / len(ocr_confidences)
        elif yolo_confidences:  # Single line field
            field_to_ocr_confidence[label] = ocr_confidences[0]

   
    # Create payload with text and confidence scores
    payload = {
        "data": {k: field_to_text.get(k, "") for k in DESIRED_FIELDS},
        "yolo_confidence": {k: round(field_to_confidence.get(k, 0.0), 3) for k in DESIRED_FIELDS},
        "ocr_confidence": {k: round(field_to_ocr_confidence.get(k, 0.0), 3) for k in DESIRED_FIELDS}
    }
   
    Path(Path(output_json).parent).mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    

def main() -> None:
    parser = argparse.ArgumentParser(description="Detect CCCD fields with YOLO then OCR via VietOCR and output JSON")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument(
        "--weights",
        default=str(Path("/Users/macbook/Documents/ocr-cccd-card/weights/models/best-fields-detect.pt").resolve()),
        help="Path to YOLO weights",
    )
    parser.add_argument("--output", default="output.json", help="Path to output JSON file")
    parser.add_argument("--device", default="cpu", help="Computation device, e.g., 'cpu' or '0'")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.5, help="IoU threshold for NMS")
    parser.add_argument("--ocr-conf", type=float, default=0.4, help="OCR confidence threshold (only process boxes above this)")
    args = parser.parse_args()

    run(
        image_path=args.image,
        weights=args.weights,
        device=args.device,
        conf=args.conf,
        iou=args.iou,
        output_json=args.output,
        ocr_conf_threshold=args.ocr_conf,
    )


if __name__ == "__main__":
    main()
