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
    global _REMBG_SESSION
    try:
        from rembg import remove, new_session
        if _REMBG_SESSION is None:
            try:
                _REMBG_SESSION = new_session("u2net")
            except Exception as e:
                logger.warning(f"Failed to initialize u2net session: {e}")
                _REMBG_SESSION = False
        session = _REMBG_SESSION if _REMBG_SESSION is not False else None
        return remove, session
    except Exception as e:
        logger.warning(f"rembg unavailable: {e}")
        return None, None


def order_points(pts):
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def get_card_corners(mask):
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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


def crop_business_card(image_input, crop_margin=0.02):
    """
    Crops business card from photo:
    - Background removal via rembg (with contour fallback)
    - 4-corner contour extraction
    - Perspective warp to rectangular card
    - Edge bleed crop
    - Quality enhancement via enhance_card_image
    """
    if isinstance(image_input, (str, os.PathLike)):
        input_img = Image.open(image_input)
    elif isinstance(image_input, bytes):
        input_img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, Image.Image):
        input_img = image_input
    else:
        input_img = Image.fromarray(image_input)

    rembg_fn, rembg_session = _get_rembg()
    if rembg_fn is not None:
        try:
            if rembg_session:
                removed = rembg_fn(input_img, session=rembg_session)
            else:
                removed = rembg_fn(input_img)
            arr = np.array(removed)
            alpha = arr[:, :, 3] if arr.shape[2] == 4 else np.full(arr.shape[:2], 255, dtype=np.uint8)
        except Exception as e:
            logger.warning(f"rembg processing error, falling back: {e}")
            arr = np.array(input_img.convert('RGBA'))
            alpha = np.full(arr.shape[:2], 255, dtype=np.uint8)
    else:
        arr = np.array(input_img.convert('RGBA'))
        alpha = np.full(arr.shape[:2], 255, dtype=np.uint8)

    mask = (alpha > 10).astype(np.uint8) * 255
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    pts = get_card_corners(mask)
    if pts is None:
        bgr = cv2.cvtColor(np.array(input_img.convert('RGB')), cv2.COLOR_RGB2BGR)
        return enhance_card_image(bgr)

    rect = order_points(pts)

    widthA = np.linalg.norm(rect[2] - rect[3])
    widthB = np.linalg.norm(rect[1] - rect[0])
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(rect[1] - rect[2])
    heightB = np.linalg.norm(rect[0] - rect[3])
    maxHeight = int(max(heightA, heightB))

    if maxWidth <= 10 or maxHeight <= 10:
        bgr = cv2.cvtColor(np.array(input_img.convert('RGB')), cv2.COLOR_RGB2BGR)
        return enhance_card_image(bgr)

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype=np.float32)

    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(bgr, M, (maxWidth, maxHeight))

    # Crop to remove corner bleed
    h, w = warped.shape[:2]
    m = crop_margin
    warped = warped[int(h * m):int(h * (1 - m)), int(w * m):int(w * (1 - m))]

    # Quality enhancement
    warped = enhance_card_image(warped)

    return warped
