import numpy as np
from PIL import Image
import sys
import os
from typing import Literal

def compute_energy(img: np.ndarray) -> np.ndarray:
    """Vectorized energy computation using forward differences."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    dx = (r[:, 2:] - r[:, :-2])**2 + (g[:, 2:] - g[:, :-2])**2 + (b[:, 2:] - b[:, :-2])**2
    dy = (r[2:, :] - r[:-2, :])**2 + (g[2:, :] - g[:-2, :])**2 + (b[2:, :] - b[:-2, :])**2
    energy = np.zeros(img.shape[:2], dtype=np.float64)
    energy[1:-1, 1:-1] = np.sqrt(dx[:, 1:-1] + dy[1:-1, :])
    return energy

def _find_seam(energy: np.ndarray) -> np.ndarray:
    """DP + backtracking O(h*w). Returns column index of seam per row."""
    h, w = energy.shape
    dp = energy.copy()
    parent = np.zeros((h, w), dtype=np.int32)
    dp[0] = energy[0]
    for i in range(1, h):
        left = np.roll(dp[i-1], 1); left[0] = np.inf
        right = np.roll(dp[i-1], -1); right[-1] = np.inf
        up = dp[i-1]
        best = np.minimum(np.minimum(left, up), right)
        parent[i] = np.argmin([left, up, right], axis=0) - 1
        dp[i] = energy[i] + best

    seam = np.zeros(h, dtype=np.int32)
    seam[-1] = np.argmin(dp[-1])
    for i in range(h - 2, -1, -1):
        seam[i] = seam[i+1] + parent[i+1, seam[i+1]]
    return seam

def remove_seam(img: np.ndarray, seam: np.ndarray) -> np.ndarray:
    """Vectorized seam removal."""
    h, w, c = img.shape
    out = np.zeros((h, w - 1, c), dtype=img.dtype)
    rows = np.arange(h)
    # Build mask: True for columns to keep
    mask = np.ones((h, w), dtype=bool)
    mask[rows, seam] = False
    for ch in range(c):
        out[..., ch] = img[..., ch][mask].reshape(h, w - 1)
    return out

def seam_carve(img: np.ndarray, new_w: int, new_h: int | None = None) -> np.ndarray:
    """Resize image using seam carving with forward energy.
    
    Removes vertical seams to reduce width and/or horizontal seams to reduce height.
    Maintains aspect ratio of remaining content.
    """
    if new_h is None:
        new_h = img.shape[0]
    
    h, w = img.shape[:2]
    
    if new_w < w:
        n_vertical = w - new_w
        # Compute all seams first, then remove in bulk (faster)
        seams = []
        working = img.astype(np.float64)
        for _ in range(n_vertical):
            energy = compute_energy(working)
            seam = _find_seam(energy)
            seams.append(seam)
            working = remove_seam(working, seam)
        img = working.astype(img.dtype)
    
    if new_h < h:
        # Transpose, carve vertically, transpose back
        img_t = np.transpose(img, (1, 0, 2))
        n_horizontal = h - new_h
        seams = []
        working = img_t.astype(np.float64)
        for _ in range(n_horizontal):
            energy = compute_energy(working)
            seam = _find_seam(energy)
            seams.append(seam)
            working = remove_seam(working, seam)
        img = np.transpose(working.astype(img.dtype), (1, 0, 2))
    
    return img

def main():
    if len(sys.argv) < 4:
        print("Usage: python seam_carve.py <input> <output> <new_width> [new_height]")
        print("  If new_height omitted, keeps original height.")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2]
    new_w = int(sys.argv[3])
    new_h = int(sys.argv[4]) if len(sys.argv) > 4 else None

    img = np.asarray(Image.open(in_path).convert("RGB"))
    result = seam_carve(img, new_w, new_h)
    Image.fromarray(result).save(out_path)
    print(f"Saved {img.shape[1]}x{img.shape[0]} -> {result.shape[1]}x{result.shape[0]} to {out_path}")

if __name__ == "__main__":
    main()
