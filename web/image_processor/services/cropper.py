import io
import os
import logging
import cv2
import numpy as np
from PIL import Image
from .enhancer import enhance_card_image

logger = logging.getLogger(__name__)

_REMBG_SESSION = None


def _get_rembg():
    """
    Initializes rembg session using lightweight u2netp (5-10x faster) with fallback to u2net.
    Reuses session singleton across calls to prevent re-instantiation lag.
    """
    global _REMBG_SESSION
    try:
        from rembg import remove, new_session
        if _REMBG_SESSION is None:
            try:
                # u2netp is ~4MB and specifically designed for high-speed edge devices
                _REMBG_SESSION = new_session("u2netp")
            except Exception:
                try:
                    _REMBG_SESSION = new_session("u2net")
                except Exception as e:
                    logger.warning(f"Failed to initialize rembg session: {e}")
                    _REMBG_SESSION = False
        session = _REMBG_SESSION if _REMBG_SESSION is not False else None
        return remove, session
    except Exception as e:
        logger.warning(f"rembg unavailable: {e}")
        return None, None


def order_points(pts):
    """
    Orders coordinates: [top-left, top-right, bottom-right, bottom-left]
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def detect_card_corners_fast(bgr: np.ndarray):
    """
    Ultra-fast (3-8ms) OpenCV contour-based card detector.
    Looks for a prominent 4-corner quadrilateral matching business card / credit card proportions.
    Returns 4 corner points if detected with high confidence, else None.
    """
    h, w = bgr.shape[:2]
    total_area = h * w
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Denoise & enhance edges
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Dual-pass edge detection: Canny + adaptive thresholding
    edges1 = cv2.Canny(blurred, 30, 150)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges2 = cv2.Canny(thresh, 50, 200)
    combined_edges = cv2.bitwise_or(edges1, edges2)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for c in contours[:5]:
        area = cv2.contourArea(c)
        # Must occupy between 12% and 96% of the frame
        if area < total_area * 0.12 or area > total_area * 0.98:
            continue

        peri = cv2.arcLength(c, True)
        for eps in [0.015, 0.02, 0.03, 0.04]:
            approx = cv2.approxPolyDP(c, eps * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                pts = approx.reshape(4, 2).astype(np.float32)
                rect = order_points(pts)
                widthA = np.linalg.norm(rect[2] - rect[3])
                widthB = np.linalg.norm(rect[1] - rect[0])
                card_w = max(widthA, widthB)

                heightA = np.linalg.norm(rect[1] - rect[2])
                heightB = np.linalg.norm(rect[0] - rect[3])
                card_h = max(heightA, heightB)

                if card_w > 20 and card_h > 20:
                    aspect = max(card_w, card_h) / min(card_w, card_h)
                    # Standard card aspect ratio: 1.2 to 2.5 (business card is ~1.75, credit card ~1.58)
                    if 1.15 <= aspect <= 2.5:
                        return pts

    return None


def get_card_corners_from_mask(mask: np.ndarray):
    """
    Extracts 4 corners from segmentation mask.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    if not contours:
        return None
    largest = contours[0]
    for epsilon in [0.01, 0.02, 0.03, 0.04, 0.05]:
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, epsilon * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
    rect = cv2.minAreaRect(largest)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


def crop_business_card(image_input, crop_margin=0.015, target_max_dim=1200):
    """
    High-performance business card cropper:
    1. Converts input to BGR numpy array and extracts scale factor.
    2. Fast-path OpenCV edge detection (5ms) bypasses heavy neural background removal.
    3. If fast-path fails, executes rembg AI segmentation on downscaled (max 800px) copy (0.3s).
    4. Warps high-resolution original image to standard crisp dimensions (max width 1200px).
    5. Applies optimized enhancement (CLAHE + fast bilateral filter + unsharp mask).
    """
    # 1. Load image to PIL and BGR numpy array
    if isinstance(image_input, (str, os.PathLike)):
        pil_img = Image.open(image_input)
        orig_bgr = cv2.imread(str(image_input))
        if orig_bgr is None:
            orig_bgr = cv2.cvtColor(np.array(pil_img.convert('RGB')), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input))
        nparr = np.frombuffer(image_input, np.uint8)
        orig_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if orig_bgr is None:
            orig_bgr = cv2.cvtColor(np.array(pil_img.convert('RGB')), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, Image.Image):
        pil_img = image_input
        orig_bgr = cv2.cvtColor(np.array(pil_img.convert('RGB')), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        orig_bgr = image_input
        pil_img = Image.fromarray(cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB))
    else:
        raise ValueError(f"Unsupported image_input type: {type(image_input)}")

    orig_h, orig_w = orig_bgr.shape[:2]

    # 2. Downscale for ultra-fast corner detection (max dimension 800px)
    max_orig = max(orig_h, orig_w)
    if max_orig > 800:
        scale = max_orig / 800.0
        scaled_w = int(round(orig_w / scale))
        scaled_h = int(round(orig_h / scale))
        scaled_bgr = cv2.resize(orig_bgr, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
        scaled_pil = pil_img.resize((scaled_w, scaled_h), Image.Resampling.BILINEAR)
    else:
        scale = 1.0
        scaled_bgr = orig_bgr
        scaled_pil = pil_img

    pts = None

    # 3. Fast-path: Instant OpenCV contour detection (~5ms)
    pts = detect_card_corners_fast(scaled_bgr)

    # 4. Fallback: Downscaled rembg AI background removal (~0.3s)
    if pts is None:
        rembg_fn, rembg_session = _get_rembg()
        if rembg_fn is not None:
            try:
                if rembg_session:
                    removed = rembg_fn(scaled_pil, session=rembg_session)
                else:
                    removed = rembg_fn(scaled_pil)
                arr = np.array(removed)
                alpha = arr[:, :, 3] if arr.shape[2] == 4 else np.full(arr.shape[:2], 255, dtype=np.uint8)
            except Exception as e:
                logger.warning(f"rembg processing error: {e}")
                alpha = np.full((scaled_h, scaled_w), 255, dtype=np.uint8)
        else:
            alpha = np.full((scaled_h, scaled_w), 255, dtype=np.uint8)

        mask = (alpha > 15).astype(np.uint8) * 255
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        pts = get_card_corners_from_mask(mask)

    # If no corners found, return enhanced original image
    if pts is None:
        return enhance_card_image(orig_bgr)

    # 5. Map coordinates back to original image space
    pts_orig = pts * scale
    rect = order_points(pts_orig)

    widthA = np.linalg.norm(rect[2] - rect[3])
    widthB = np.linalg.norm(rect[1] - rect[0])
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(rect[1] - rect[2])
    heightB = np.linalg.norm(rect[0] - rect[3])
    maxHeight = int(max(heightA, heightB))

    if maxWidth <= 20 or maxHeight <= 20:
        return enhance_card_image(orig_bgr)

    # 6. Standardize dimensions for fast network transfer & optimal memory (standard ~1200x700)
    if maxWidth > target_max_dim or maxHeight > target_max_dim:
        ratio = min(target_max_dim / float(maxWidth), target_max_dim / float(maxHeight))
        out_w = max(200, int(maxWidth * ratio))
        out_h = max(120, int(maxHeight * ratio))
    else:
        out_w = maxWidth
        out_h = maxHeight

    dst = np.array([
        [0, 0],
        [out_w - 1, 0],
        [out_w - 1, out_h - 1],
        [0, out_h - 1]
    ], dtype=np.float32)

    # Warp from original crisp image
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(orig_bgr, M, (out_w, out_h))

    # 7. Crop bleed margin
    if crop_margin > 0:
        h, w = warped.shape[:2]
        m_y = int(h * crop_margin)
        m_x = int(w * crop_margin)
        if h - 2 * m_y > 50 and w - 2 * m_x > 50:
            warped = warped[m_y:h - m_y, m_x:w - m_x]

    # 8. Enhance image
    warped = enhance_card_image(warped)

    return warped
