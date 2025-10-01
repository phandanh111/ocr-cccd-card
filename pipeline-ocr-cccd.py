import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path


def _load_attr_from_py(path: Path, attr_name: str):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    if not hasattr(module, attr_name):
        raise AttributeError(f"{path} does not define '{attr_name}'")
    return getattr(module, attr_name)


def run_pipeline(
    image: Path,
    output_json: Path,
    # Crop params
    crop_model: Path,
    crop_device: str | None,
    crop_conf: float,
    crop_deskew: bool,
    crop_expand: float,
    crop_aspect: float | None,
    # OCR params
    ocr_weights: Path,
    ocr_device: str,
    ocr_conf: float,
    ocr_iou: float,
) -> dict:
    image = image.expanduser().resolve()
    output_json = output_json.expanduser().resolve()
    crop_model = crop_model.expanduser().resolve()
    ocr_weights = ocr_weights.expanduser().resolve()

    crop_path = Path(__file__).parent / "stages/crop.py"
    ocr_path = Path(__file__).parent / "stages/ocr.py"

    crop_cccd = _load_attr_from_py(crop_path, "crop_cccd")
    ocr_run = _load_attr_from_py(ocr_path, "run")

    t0 = time.perf_counter()

    # 1) Crop first
    cropped_image_path = crop_cccd(
        image_path=str(image),
        output_path=None,  # let crop script decide name: <orig>_cropped.jpg
        model_path=str(crop_model),
        device=crop_device,
        conf_thres=crop_conf,
        deskew=crop_deskew,
        expand=crop_expand,
        aspect=crop_aspect,
    )
    if not cropped_image_path:
        raise RuntimeError("Crop step failed: not enough corners detected")

    # 2) OCR on cropped image
    ocr_run(
        image_path=str(cropped_image_path),
        weights=str(ocr_weights),
        device=ocr_device,
        conf=ocr_conf,
        iou=ocr_iou,
        output_json=str(output_json),
        ocr_conf_threshold=ocr_conf,  # reuse same threshold for filtering before OCR
    )

    runtime_ms = int(round((time.perf_counter() - t0) * 1000))

    # 3) Augment JSON with runtime
    if not output_json.exists():
        raise FileNotFoundError(f"Expected output JSON not found: {output_json}")
    with output_json.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    payload["runtime_ms"] = runtime_ms
    payload["cropped_image"] = str(cropped_image_path)

    with output_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline: crop CCCD then OCR and output JSON with runtime")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--output", default="output.json", help="Path to output JSON file")

    # Crop options
    parser.add_argument("--crop-model", default=str(Path("weights/models/best-corner-detect.pt").resolve()), help="Path to crop YOLO weights")
    parser.add_argument("--crop-device", default=None, help="Device for crop model, e.g., 'cpu' or 'cuda:0'")
    parser.add_argument("--crop-conf", type=float, default=0.3, help="Confidence threshold for corner detection")
    parser.add_argument("--no-crop-deskew", dest="crop_deskew", action="store_false")
    parser.add_argument("--crop-deskew", dest="crop_deskew", action="store_true")
    parser.set_defaults(crop_deskew=True)
    parser.add_argument("--crop-expand", type=float, default=0.06, help="Expand detected quad outward ratio")
    parser.add_argument("--crop-aspect", type=float, default=1.585, help="Target aspect ratio to pad to (set <=0 to disable)")

    # OCR options
    parser.add_argument("--weights", default=str(Path("weights/models/best-fields-detect.pt").resolve()), help="Path to OCR detector weights")
    parser.add_argument("--device", default="cpu", help="Computation device for OCR, e.g., 'cpu' or '0'")
    parser.add_argument("--conf", type=float, default=0.25, help="YOLO confidence threshold for OCR boxes")
    parser.add_argument("--iou", type=float, default=0.5, help="IoU threshold for NMS in OCR stage")

    args = parser.parse_args()

    # Convert crop-aspect: allow <=0 to disable
    crop_aspect = None if args.crop_aspect is not None and args.crop_aspect <= 0 else args.crop_aspect

    payload = run_pipeline(
        image=Path(args.image),
        output_json=Path(args.output),
        crop_model=Path(args.crop_model),
        crop_device=args.crop_device,
        crop_conf=args.crop_conf,
        crop_deskew=args.crop_deskew,
        crop_expand=args.crop_expand,
        crop_aspect=crop_aspect,
        ocr_weights=Path(args.weights),
        ocr_device=args.device,
        ocr_conf=args.conf,
        ocr_iou=args.iou,
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
