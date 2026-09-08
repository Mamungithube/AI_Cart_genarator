import cv2
import numpy as np


def enhance_card_image(bgr: np.ndarray) -> np.ndarray:
    """
    Exact enhance_card_image ported from milo22_image_processing_ai-main (app/services/cropper.py):
    - Converts to LAB color space
    - CLAHE on luminance channel (local contrast adaptation)
    - Bilateral filter on luminance channel (edge-preserving denoising)
    - Merges channels back to BGR
    - Mild unsharp mask (1.4x - 0.4x) with sigmaX=1.0 for sharp, crisp text
    """
    if bgr is None:
        return None

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # CLAHE on luminance only — adapts to local contrast, not global
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)

    # Gentle denoise on L only before merging
    l = cv2.bilateralFilter(l, d=9, sigmaColor=75, sigmaSpace=75)

    lab = cv2.merge([l, a, b])
    result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Mild unsharp mask — don't go 1.8x, that creates halos in dark lighting
    gaussian = cv2.GaussianBlur(result, (0, 0), sigmaX=1.0)
    result = cv2.addWeighted(result, 1.4, gaussian, -0.4, 0)

    return result
