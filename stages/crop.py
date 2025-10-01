import os
import sys
import argparse
import math
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from ultralytics import YOLO
except Exception as exc:  # pragma: no cover
    YOLO = None  # Allows help/--usage without ultralytics installed


MODEL_PATH_DEFAULT = "/Users/macbook/Documents/ocr-cccd-card/weights/models/best-corners-detect.pt"


Corner = Tuple[float, float]


def _center_of_box(xyxy: np.ndarray) -> Corner:
    x1, y1, x2, y2 = xyxy
    return float((x1 + x2) / 2.0), float((y1 + y2) / 2.0)


def _order_corners_robust(points: List[Corner]) -> List[Corner]:
    """Order 4 points as [tl, tr, br, bl] using sum/diff heuristic.

    This is robust for most quadrilaterals and ensures a consistent perspective mapping.
    """
    if len(points) != 4:
        raise ValueError("points must contain exactly 4 elements")
    pts = np.array(points, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    tl = pts[int(np.argmin(s))]
    br = pts[int(np.argmax(s))]
    tr = pts[int(np.argmin(diff))]
    bl = pts[int(np.argmax(diff))]
    return [tuple(tl), tuple(tr), tuple(br), tuple(bl)]


def _compute_warp(image: np.ndarray, ordered_pts: List[Corner]) -> Tuple[np.ndarray, np.ndarray]:
    (tl, tr, br, bl) = ordered_pts

    width_top = float(np.hypot(tl[0] - tr[0], tl[1] - tr[1]))
    width_bottom = float(np.hypot(bl[0] - br[0], bl[1] - br[1]))
    out_width = int(round((width_top + width_bottom) / 2.0))

    height_left = float(np.hypot(tl[0] - bl[0], tl[1] - bl[1]))
    height_right = float(np.hypot(tr[0] - br[0], tr[1] - br[1]))
    out_height = int(round((height_left + height_right) / 2.0))

    src = np.float32([tl, tr, br, bl])
    dst = np.float32([[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]])

    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(image, matrix, (out_width, out_height))
    return warped, matrix


def _deskew_by_dominant_lines(image: np.ndarray) -> np.ndarray:
    """Deskew the image by estimating dominant edge orientation with Hough.

    Steps:
    - Canny edges
    - Probabilistic Hough to get long lines
    - Compute angles, take median near 0/180 and rotate accordingly
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Prefer horizontal structures using Sobel X
    sobelx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
    abs_sobelx = cv2.convertScaleAbs(sobelx)
    edges = cv2.Canny(abs_sobelx, 50, 150, apertureSize=3)

    h, w = gray.shape[:2]
    min_line_len = max(h, w) * 0.5
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=60,
                            minLineLength=int(min_line_len), maxLineGap=20)
    if lines is None or len(lines) == 0:
        return image

    angles = []
    weights = []
    for l in lines.reshape(-1, 4):
        x1, y1, x2, y2 = l
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Normalize to [-90, 90]
        if angle > 90:
            angle -= 180
        if angle < -90:
            angle += 180
        # Focus on near-horizontal lines only
        if -25 <= angle <= 25:
            length = np.hypot(x2 - x1, y2 - y1)
            angles.append(angle)
            weights.append(length)

    if len(angles) == 0:
        return image

    # Weighted median/mean (fall back to mean if needed)
    if len(weights) == len(angles) and len(angles) > 0:
        median_angle = float(np.average(angles, weights=weights))
    else:
        median_angle = float(np.median(angles))
    # Snap angles near 90 to 0 by subtracting multiples of 90
    if abs(median_angle) > 45:
        if median_angle > 0:
            median_angle -= 90.0
        else:
            median_angle += 90.0

    if abs(median_angle) < 0.3:  # already straight enough
        return image

    center = (w / 2.0, h / 2.0)
    rot = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, rot, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # Ensure landscape orientation (ID card) after rotation
    rh, rw = rotated.shape[:2]
    if rh > rw:
        rotated = cv2.rotate(rotated, cv2.ROTATE_90_CLOCKWISE)
    return rotated


def _rotate_to_place_point_top_left(image: np.ndarray, point_xy: Optional[Corner]) -> np.ndarray:
    if point_xy is None:
        return image
    h, w = image.shape[:2]
    x, y = point_xy
    # Try 4 rotations; pick the one with point in TL quadrant (x<w/2, y<h/2)
    def quadrant(px: float, py: float, width: int, height: int) -> bool:
        return px < width / 2.0 and py < height / 2.0

    # rotation 0
    img0 = image
    if quadrant(x, y, w, h):
        return img0

    # rotation 90 CW
    img1 = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    x1, y1 = h - y, x
    if quadrant(x1, y1, h, w):
        return img1

    # rotation 180
    img2 = cv2.rotate(image, cv2.ROTATE_180)
    x2, y2 = w - x, h - y
    if quadrant(x2, y2, w, h):
        return img2

    # rotation 270 CW
    img3 = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    x3, y3 = y, w - x
    return img3


def _inflate_quad(points: List[Corner], expand: float, image_shape: Tuple[int, int, int]) -> List[Corner]:
    if expand <= 0:
        return points
    h, w = image_shape[:2]
    cx = sum(p[0] for p in points) / 4.0
    cy = sum(p[1] for p in points) / 4.0
    inflated: List[Corner] = []
    scale = 1.0 + float(expand)
    for (x, y) in points:
        nx = cx + (x - cx) * scale
        ny = cy + (y - cy) * scale
        nx = float(np.clip(nx, 0, w - 1))
        ny = float(np.clip(ny, 0, h - 1))
        inflated.append((nx, ny))
    return inflated


def _pad_to_aspect(image: np.ndarray, target_aspect: Optional[float]) -> np.ndarray:
    if not target_aspect or target_aspect <= 0:
        return image
    h, w = image.shape[:2]
    cur = w / max(h, 1)
    if abs(cur - target_aspect) < 1e-3:
        return image
    if cur < target_aspect:
        # need more width
        new_w = int(round(h * target_aspect))
        pad_total = max(new_w - w, 0)
        left = pad_total // 2
        right = pad_total - left
        return cv2.copyMakeBorder(image, 0, 0, left, right, cv2.BORDER_REPLICATE)
    else:
        # need more height
        new_h = int(round(w / target_aspect))
        pad_total = max(new_h - h, 0)
        top = pad_total // 2
        bottom = pad_total - top
        return cv2.copyMakeBorder(image, top, bottom, 0, 0, cv2.BORDER_REPLICATE)


def _normalize_label(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


def detect_points(model: "YOLO", image: np.ndarray, device: Optional[str] = None, conf_thres: float = 0.3) -> Tuple[Optional[Corner], List[Corner]]:
    result = model.predict(image, device=device, verbose=False)[0]

    class_id_to_name = result.names

    corners: List[Tuple[Corner, float]] = []  # (center, confidence)
    emblem: Optional[Corner] = None

    for box in result.boxes:
        conf = float(getattr(box, "conf", 1.0))
        if conf < conf_thres:
            continue
        xyxy = box.xyxy.cpu().numpy().reshape(-1)[:4]
        cls_id = int(box.cls.item())
        name = _normalize_label(class_id_to_name.get(cls_id, str(cls_id)))
        center = _center_of_box(xyxy)

        if name in {"tren-trai", "tren-phai", "duoi-trai", "duoi-phai", "top-left", "top-right", "bottom-left", "bottom-right"}:
            corners.append((center, conf))
        elif name in {"quoc-huy", "quoc_huy", "huy-hieu", "emblem"}:
            emblem = center

    # Nếu có nhiều hơn 4 góc, chọn 4 góc có confidence cao nhất
    if len(corners) > 4:
        # Sắp xếp theo confidence giảm dần và lấy 4 góc tốt nhất
        corners.sort(key=lambda x: x[1], reverse=True)
        corners = corners[:4]
        print(f"[INFO] Phát hiện {len(corners)} góc, chọn 4 góc có confidence cao nhất")
    
    # Chỉ lấy tọa độ, bỏ confidence
    final_corners = [corner[0] for corner in corners]
    
    return emblem, final_corners


def deskew_by_top_edge(image, corners):
    """
    Xoay ảnh sao cho cạnh trên (TL->TR) nằm ngang.
    corners: list [(x,y), (x,y), (x,y), (x,y)] theo thứ tự [TL, TR, BR, BL]
    """
    (tl, tr, br, bl) = corners
    dx = tr[0] - tl[0]
    dy = tr[1] - tl[1]
    angle = math.degrees(math.atan2(dy, dx))

    # Xoay ngược lại
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated    


def crop_cccd(
    image_path: str,
    output_path: Optional[str] = None,
    model_path: str = MODEL_PATH_DEFAULT,
    device: Optional[str] = None,
    conf_thres: float = 0.3,
    deskew: bool = True,
    expand: float = 0.06,
    aspect: Optional[float] = 1.585,
) -> Optional[str]:
    if YOLO is None:
        raise RuntimeError("ultralytics is required. Please install it: pip install ultralytics")

    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    model = YOLO(model_path)
    emblem, corners = detect_points(model, image, device=device, conf_thres=conf_thres)

    if len(corners) < 3:
        return None

    # Nếu có 3 góc thì nội suy ra góc thứ 4
    if len(corners) == 3:
        pts = np.array(corners, dtype=np.float32)
        dists = [(i, j, float(np.hypot(*(pts[i] - pts[j])))) for i in range(3) for j in range(i + 1, 3)]
        i, j, _ = max(dists, key=lambda x: x[2])
        k = {0, 1, 2}.difference({i, j}).pop()
        corners.append((float(pts[i][0] + pts[j][0] - pts[k][0]),
                        float(pts[i][1] + pts[j][1] - pts[k][1])))

    # Sắp xếp góc [TL, TR, BR, BL]
    ordered = _order_corners_robust(corners)
    ordered = _inflate_quad(ordered, expand, image.shape)

    # Warp perspective
    warped, M = _compute_warp(image, ordered)

    # --- NEW: deskew theo cạnh trên ---
    try:
        (tl, tr, br, bl) = [(0,0), (warped.shape[1]-1,0), (warped.shape[1]-1, warped.shape[0]-1), (0, warped.shape[0]-1)]
        dx = tr[0] - tl[0]
        dy = tr[1] - tl[1]
        angle = math.degrees(math.atan2(dy, dx))
        if abs(angle) > 0.3:  # nếu lệch đáng kể
            (h, w) = warped.shape[:2]
            center = (w // 2, h // 2)
            rotM = cv2.getRotationMatrix2D(center, angle, 1.0)
            warped = cv2.warpAffine(warped, rotM, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception as e:
        print(f"[WARN] Deskew by top edge failed: {e}")

    # Xoay để đảm bảo quốc huy nằm top-left
    if emblem is not None:
        # OpenCV expects shape (N,1,2) with dtype float32
        emblem_pt = np.array([[[float(emblem[0]), float(emblem[1])]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(emblem_pt, M)[0][0]
        warped = _rotate_to_place_point_top_left(warped, (float(projected[0]), float(projected[1])))

    # Pad theo tỷ lệ chuẩn
    warped = _pad_to_aspect(warped, aspect)

    if output_path is None:
        root, ext = os.path.splitext(image_path)
        output_path = f"{root}_cropped{ext or '.jpg'}"

    if not cv2.imwrite(output_path, warped):
        raise IOError(f"Failed to write output image to {output_path}")

    return output_path



def main() -> None:
    parser = argparse.ArgumentParser(description="Detect corners and crop CCCD image")
    parser.add_argument("image", help="Path to the input image")
    parser.add_argument("--out", dest="out", default=None, help="Path to save the cropped image")
    parser.add_argument("--model", dest="model", default=MODEL_PATH_DEFAULT, help="Path to YOLO model weights")
    parser.add_argument("--device", dest="device", default=None, help="Device for inference, e.g. 'cpu', 'cuda:0'")
    parser.add_argument("--conf", dest="conf", type=float, default=0.3, help="Confidence threshold to accept boxes (default: 0.3)")
    parser.add_argument("--deskew", dest="deskew", action="store_true", help="Enable deskew after warp (default on)")
    parser.add_argument("--no-deskew", dest="deskew", action="store_false")
    parser.set_defaults(deskew=True)
    parser.add_argument("--expand", dest="expand", type=float, default=0.06, help="Expand the detected quad outward ratio (default 0.06)")
    parser.add_argument("--aspect", dest="aspect", type=float, default=1.585, help="Target aspect ratio to pad to (default 1.585≈ID-1)")
    args = parser.parse_args()

    try:
        out_path = crop_cccd(args.image, args.out, args.model, args.device, args.conf, args.deskew, args.expand, args.aspect)
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}")
        sys.exit(1)

    if out_path is None:
        print("Không đủ góc để crop (ít hơn 3 điểm).")
        sys.exit(2)

    print(f"Đã lưu ảnh crop: {out_path}")


if __name__ == "__main__":
    main()
