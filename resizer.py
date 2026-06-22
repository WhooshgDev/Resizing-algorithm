"""
Smart image resizer — automatically picks the best algorithm for any image.

Algorithms:
  seam       Content-aware seam carving (forward energy)
  scale      Standard interpolation (Lanczos)
  crop       Entropy-based smart crop
  letterbox  Scale + pad to target
  hybrid     Adaptive: seam-carve low-energy regions, scale the rest
  auto       Classifies image type, picks best algo

Hybrid uses a dynamic stopping criterion (from Rubinstein et al. 2009
Multi-Operator Media Retargeting).  Instead of a fixed fraction, it
tracks average seam energy and switches to scaling once seams start
cutting through important content — avoids both over-carving and
under-carving automatically.

Classification:
  photo     → hybrid
  graphic   → scale / crop
  text      → scale
  default   → hybrid
"""

import numpy as np
from PIL import Image
import sys, os, math
from enum import Enum
from typing import Literal


# ─── Energy & helpers ───────────────────────────────────────────────────────

def compute_energy(img: np.ndarray) -> np.ndarray:
    """Gradient magnitude (RGB channels summed), vectorized."""
    f = img.astype(np.float64)
    dx2 = np.zeros((f.shape[0], f.shape[1]), dtype=np.float64)
    dy2 = np.zeros_like(dx2)
    n_ch = 3 if f.ndim == 3 else 1
    for c in range(n_ch):
        ch = f[..., c] if f.ndim == 3 else f
        dx2[:, 1:-1] += (ch[:, 2:] - ch[:, :-2]) ** 2
        dy2[1:-1, :] += (ch[2:, :] - ch[:-2, :]) ** 2
    return np.sqrt(dx2 + dy2)


# ─── Forward-energy seam carving ───────────────────────────────────────────
#
# Rubinstein et al. 2008 "Improved Seam Carving":
# Instead of removing pixels with lowest backward energy (gradient mag),
# we minimise the *energy created* when a seam is removed.
#
# For each pixel (i,j) we precompute the cost of new edges between
# the neighbours that become adjacent after removal:
#
#   M_LR = |I(i,j+1) - I(i,j-1)|   (new left-right neighbour cost)
#   M_LU = |I(i-1,j) - I(i,j-1)|   (cost if seam came from top-left)
#   M_RU = |I(i-1,j) - I(i,j+1)|   (cost if seam came from top-right)
#
#   CL = M_LR + M_LU   (seam arrived from left)
#   CU = M_LR          (seam arrived straight)
#   CR = M_LR + M_RU   (seam arrived from right)
#
# DP then picks the minimum-cost transition.

def _forward_cost(img: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Precompute CL, CU, CR forward-energy cost matrices (per-pixel, summed over RGB)."""
    f = img.astype(np.float64)
    h, w = f.shape[:2]

    # Left-right cost  M_LR(i,j) = |I(i,j+1) - I(i,j-1)|
    M_LR = np.zeros((h, w), dtype=np.float64)
    n_ch = 3 if f.ndim == 3 else 1
    for c in range(n_ch):
        ch = f[..., c] if f.ndim == 3 else f
        M_LR[:, 1:-1] += np.abs(ch[:, 2:] - ch[:, :-2])

    # Left-up cost  M_LU(i,j) = |I(i-1,j) - I(i,j-1)|
    M_LU = np.zeros((h, w), dtype=np.float64)
    for c in range(n_ch):
        ch = f[..., c] if f.ndim == 3 else f
        M_LU[1:, 1:] += np.abs(ch[:-1, 1:] - ch[1:, :-1])

    # Right-up cost  M_RU(i,j) = |I(i-1,j) - I(i,j+1)|
    M_RU = np.zeros((h, w), dtype=np.float64)
    for c in range(n_ch):
        ch = f[..., c] if f.ndim == 3 else f
        M_RU[1:, :-1] += np.abs(ch[:-1, :-1] - ch[1:, 1:])

    # Propagate edge costs from nearest valid neighbor so column 0 / w-1
    # don't have artificially low cost (which would bias seams to sides)
    M_LR[:, 0]  = M_LR[:, 1]
    M_LR[:, -1] = M_LR[:, -2]
    M_LU[:, 0]  = M_LU[:, 1]
    M_RU[:, -1] = M_RU[:, -2]

    CL = M_LR + M_LU
    CU = M_LR
    CR = M_LR + M_RU

    # First row: no pixel above, so left/right-up transitions impossible
    CL[0, :] = CR[0, :] = np.inf
    # Edge columns: prohibit entering from outside
    CL[:, 0] = CR[:, w - 1] = np.inf
    return CL, CU, CR


def _find_seam_forward(img: np.ndarray) -> tuple[np.ndarray, float]:
    """Forward-energy DP seam finding.
    
    Returns (seam, seam_energy).
    seam[i] = column of seam at row i.
    seam_energy = total forward energy of this seam (last dp entry).
    """
    h, w, c = img.shape
    CL, CU, CR = _forward_cost(img)

    dp = np.zeros((h, w), dtype=np.float64)
    parent = np.zeros((h, w), dtype=np.int32)
    # First row: mixed forward + backward energy prevents edge bias when
    # forward cost is zero in uniform regions (e.g. white backgrounds)
    back_energy = compute_energy(img)[0]
    dp[0] = CU[0] + back_energy * 0.1

    for i in range(1, h):
        # dp[i-1] shifted so index j holds dp[i-1][j-1] / dp[i-1][j+1]
        dp_left   = np.roll(dp[i-1], 1);  dp_left[0]   = np.inf
        dp_right  = np.roll(dp[i-1], -1); dp_right[-1]  = np.inf

        left  = dp_left  + CL[i]   # came from (i-1, j-1)
        up    = dp[i-1]  + CU[i]   # came from (i-1, j)
        right = dp_right + CR[i]   # came from (i-1, j+1)

        best = np.minimum(np.minimum(left, up), right)
        parent[i] = np.argmin([left, up, right], axis=0) - 1
        dp[i] = best

    seam = np.zeros(h, dtype=np.int32)
    seam[-1] = np.argmin(dp[-1])
    seam_energy = dp[-1, seam[-1]]
    for i in range(h-2, -1, -1):
        seam[i] = seam[i+1] + parent[i+1, seam[i+1]]
    return seam, seam_energy


def _find_seam_backward(energy: np.ndarray) -> tuple[np.ndarray, float]:
    """Backward-energy DP seam finding (original Avidan & Shamir 2007).
    
    Returns (seam, seam_energy).
    """
    h, w = energy.shape
    dp = energy.copy()
    parent = np.zeros((h, w), dtype=np.int32)
    for i in range(1, h):
        left = np.roll(dp[i-1], 1); left[0] = np.inf
        right = np.roll(dp[i-1], -1); right[-1] = np.inf
        up = dp[i-1]
        parent[i] = np.argmin([left, up, right], axis=0) - 1
        dp[i] = energy[i] + np.minimum(np.minimum(left, up), right)
    seam = np.zeros(h, dtype=np.int32)
    seam[-1] = np.argmin(dp[-1])
    seam_energy = dp[-1, seam[-1]]
    for i in range(h-2, -1, -1):
        seam[i] = seam[i+1] + parent[i+1, seam[i+1]]
    return seam, seam_energy


def _remove_seam(img: np.ndarray, seam: np.ndarray) -> np.ndarray:
    """Vectorized seam removal via boolean mask."""
    h, w, c = img.shape
    mask = np.ones((h, w), dtype=bool)
    mask[np.arange(h), seam] = False
    out = np.zeros((h, w-1, c), dtype=img.dtype)
    for ch in range(c):
        out[..., ch] = img[..., ch][mask].reshape(h, w-1)
    return out


def _seam_energy(img: np.ndarray, seam: np.ndarray) -> float:
    """Mean backward energy along a seam."""
    energy = compute_energy(img)
    return float(energy[np.arange(img.shape[0]), seam].mean())


# ─── Carving drivers ────────────────────────────────────────────────────────

def _carve_seams(img: np.ndarray, n: int, axis: int = 0,
                 forward: bool = True) -> np.ndarray:
    """Remove n seams along axis.
    
    If forward=True, uses forward-energy DP (better quality, ~2x slower).
    """
    if n <= 0:
        return img
    if axis == 1:
        img = np.transpose(img, (1, 0, 2))
    working = img.astype(np.float64)
    for _ in range(n):
        if forward:
            seam, _ = _find_seam_forward(working)
        else:
            energy = compute_energy(working)
            seam, _ = _find_seam_backward(energy)
        working = _remove_seam(working, seam)
    out = working.astype(img.dtype)
    return np.transpose(out, (1, 0, 2)) if axis == 1 else out


def _carve_adaptive(img: np.ndarray, max_n: int, axis: int = 0,
                    energy_ratio: float = 2.0) -> tuple[np.ndarray, int]:
    """Adaptive seam carving — stop early if seam energy spikes.
    
    Based on Rubinstein et al. 2009 multi-operator retargeting.
    Tracks a rolling median of seam energies.  When the current seam's
    energy exceeds `energy_ratio` × the rolling median, it stops and
    switches to scaling — preserving important content.
    
    Skips zero-energy seams (uniform regions) when computing the
    baseline, so the stopping criterion isn't triggered by the very
    first non-zero seam in an otherwise uniform image.
    
    Returns (carved_image, n_removed).
    """
    if max_n <= 0:
        return img, 0
    if axis == 1:
        result, n = _carve_adaptive(np.transpose(img, (1, 0, 2)),
                                     max_n, 0, energy_ratio)
        return np.transpose(result, (1, 0, 2)), n

    working = img.astype(np.float64)
    seam_energies = []
    n_removed = 0

    for i in range(max_n):
        seam, fe = _find_seam_forward(working)
        norm_e = fe / working.shape[0]
        seam_energies.append(norm_e)

        # Build baseline from non-zero energies only
        nonzero = [e for e in seam_energies if e > 1e-6]

        # Check stopping criterion once we have at least 5 seams with
        # non-zero energy and at least 10 total seams carved
        if len(nonzero) >= 5 and i >= 10:
            baseline = np.median(nonzero)
            if norm_e > baseline * energy_ratio:
                break

        working = _remove_seam(working, seam)
        n_removed += 1

    return working.astype(img.dtype), n_removed


# ─── Algorithm implementations ──────────────────────────────────────────────

def resize_seam(img: np.ndarray, new_w: int, new_h: int,
                forward: bool = True) -> np.ndarray:
    """Content-aware seam carving.  Best for photos with clear subjects.
    
    Args:
        forward: if True use forward-energy (better quality), else backward.
    """
    h, w = img.shape[:2]
    if new_w < w:
        img = _carve_seams(img, w - new_w, axis=0, forward=forward)
    if new_h < h:
        img = _carve_seams(img, h - new_h, axis=1, forward=forward)
    return img


def resize_scale(img: np.ndarray, new_w: int, new_h: int,
                 method: int = Image.LANCZOS) -> np.ndarray:
    """Standard interpolation scaling.  Best for graphics, text, UI."""
    pil = Image.fromarray(img)
    return np.asarray(pil.resize((new_w, new_h), method))


def resize_crop(img: np.ndarray, new_w: int, new_h: int) -> np.ndarray:
    """Entropy-based smart crop.  Best for images with strong focal points."""
    h, w = img.shape[:2]
    gray = np.mean(img, axis=2).astype(np.float64)
    tile_h, tile_w = max(16, h // 32), max(16, w // 32)
    nt_h, nt_w = h // tile_h, w // tile_w
    entropy_map = np.zeros((nt_h, nt_w), dtype=np.float64)

    for ty in range(nt_h):
        for tx in range(nt_w):
            tile = gray[ty*tile_h:(ty+1)*tile_h, tx*tile_w:(tx+1)*tile_w]
            hist, _ = np.histogram(tile, bins=16, range=(0, 255), density=True)
            hist = hist[hist > 0]
            entropy_map[ty, tx] = -np.sum(hist * np.log2(hist))

    target_ph = max(1, new_h // tile_h)
    target_pw = max(1, new_w // tile_w)
    if target_ph > nt_h or target_pw > nt_w:
        return resize_scale(img, new_w, new_h)

    integral = np.cumsum(np.cumsum(entropy_map, axis=0), axis=1)

    def rect_sum(y1, x1, y2, x2):
        s = integral[y2, x2]
        if x1 > 0: s -= integral[y2, x1-1]
        if y1 > 0: s -= integral[y1-1, x2]
        if x1 > 0 and y1 > 0: s += integral[y1-1, x1-1]
        return s

    best_score, best_y, best_x = -1.0, 0, 0
    for y in range(nt_h - target_ph + 1):
        for x in range(nt_w - target_pw + 1):
            score = rect_sum(y, x, y+target_ph-1, x+target_pw-1)
            if score > best_score:
                best_score = score
                best_y, best_x = y, x

    px, py = best_x * tile_w, best_y * tile_h
    crop = img[py:py+target_ph*tile_h, px:px+target_pw*tile_w]
    return resize_scale(crop, new_w, new_h)


def resize_letterbox(img: np.ndarray, new_w: int, new_h: int,
                     bg_color=(0, 0, 0)) -> np.ndarray:
    """Scale to fit target, pad remaining area.  Preserves aspect ratio."""
    h, w = img.shape[:2]
    scale = min(new_w / w, new_h / h)
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    scaled = resize_scale(img, sw, sh)
    out = np.full((new_h, new_w, 3), bg_color, dtype=np.uint8)
    y_off, x_off = (new_h - sh) // 2, (new_w - sw) // 2
    out[y_off:y_off+sh, x_off:x_off+sw] = scaled
    return out


def resize_hybrid(img: np.ndarray, new_w: int, new_h: int,
                  energy_ratio: float = 2.0) -> np.ndarray:
    """Adaptive multi-operator retargeting (Rubinstein et al. 2009).
    
    1. Carves seams using forward energy, stopping when seam energy
       exceeds `energy_ratio` × baseline (mean of first 5 seams).
    2. Scales the remaining difference with Lanczos interpolation.
    
    This avoids the fixed-fraction problem: uniform regions (sky, walls)
    get aggressively carved while important content is preserved by
    switching to scaling.
    
    Args:
        energy_ratio: stop carving when a seam's energy exceeds this
                      multiple of the initial baseline.  Lower = stop
                      sooner (less carving, more scaling).  1.5-3.0
                      are reasonable; 2.0 works well for most images.
    """
    h, w = img.shape[:2]
    dw, dh = max(0, w - new_w), max(0, h - new_h)

    result = img
    n_carved_w = 0
    if dw > 0:
        result, n_carved_w = _carve_adaptive(result, dw, axis=0,
                                              energy_ratio=energy_ratio)
    if dh > 0:
        result, _carved_h = _carve_adaptive(result, dh, axis=1,
                                             energy_ratio=energy_ratio)

    rh, rw = result.shape[:2]
    if rw != new_w or rh != new_h:
        result = resize_scale(result, new_w, new_h)

    return result


# ─── Image classifier ──────────────────────────────────────────────────────

class ImageClass(Enum):
    PHOTO = "photo"
    GRAPHIC = "graphic"
    TEXT = "text"
    DEFAULT = "default"

def _unique_colors_approx(img: np.ndarray, sample: int = 4096) -> float:
    """Approximate ratio of unique colors.  Fast via random sampling."""
    h, w = img.shape[:2]
    total = h * w
    if total > sample:
        idx = np.random.choice(total, sample, replace=False)
        pixels = img.reshape(-1, 3)[idx]
    else:
        pixels = img.reshape(-1, 3)
    packed = (pixels[:, 0].astype(np.uint32) << 16 |
              pixels[:, 1].astype(np.uint32) << 8 |
              pixels[:, 2].astype(np.uint32))
    unique = len(np.unique(packed))
    return unique / min(total, sample)

def _edge_density(energy: np.ndarray) -> float:
    """Fraction of pixels above 50% of max energy."""
    thresh = energy.max() * 0.5
    return float(np.mean(energy > thresh))

def _energy_entropy(energy: np.ndarray, bins: int = 32) -> float:
    """Normalized entropy of energy distribution."""
    hist, _ = np.histogram(energy, bins=bins, density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log2(hist)) / np.log2(bins))

def classify_image(img: np.ndarray) -> ImageClass:
    """Auto-detect image type using edge / color / energy features."""
    h, w = img.shape[:2]
    small = resize_scale(img, min(256, w), min(256, h))
    energy = compute_energy(small)

    e_density = _edge_density(energy)
    e_entropy = _energy_entropy(energy)
    color_ratio = _unique_colors_approx(img)

    if e_density > 0.35 and color_ratio < 0.15:
        return ImageClass.TEXT
    if color_ratio < 0.10:
        return ImageClass.GRAPHIC
    if color_ratio < 0.25 and e_density < 0.20:
        return ImageClass.GRAPHIC
    if color_ratio > 0.30 and e_entropy > 0.75:
        return ImageClass.PHOTO
    return ImageClass.DEFAULT


# ─── Smart dispatcher ──────────────────────────────────────────────────────

ALGO_MAP: dict[ImageClass, str] = {
    ImageClass.PHOTO: "hybrid",
    ImageClass.GRAPHIC: "scale",
    ImageClass.TEXT: "scale",
    ImageClass.DEFAULT: "hybrid",
}

def resize_auto(img: np.ndarray, new_w: int, new_h: int,
                prefer: str | None = None) -> np.ndarray:
    """Auto-detect image type and resize with the best algorithm."""
    algo = prefer or ALGO_MAP[classify_image(img)]

    if algo == "seam":
        return resize_seam(img, new_w, new_h)
    if algo == "scale":
        return resize_scale(img, new_w, new_h)
    if algo == "crop":
        return resize_crop(img, new_w, new_h)
    if algo == "letterbox":
        return resize_letterbox(img, new_w, new_h)
    if algo == "hybrid":
        return resize_hybrid(img, new_w, new_h)
    return resize_scale(img, new_w, new_h)


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Smart image resizer — auto-picks best algorithm per image.")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", nargs="?", help="Output image path")
    parser.add_argument("width", type=int, nargs="?", help="Target width")
    parser.add_argument("height", type=int, nargs="?", default=None,
                        help="Target height (default: same as width)")
    parser.add_argument("--algo", "-a",
                        choices=["auto", "seam", "scale", "crop", "letterbox", "hybrid"],
                        default="auto",
                        help="Force algorithm (default: auto)")
    parser.add_argument("--info", action="store_true",
                        help="Show classification info and exit")
    parser.add_argument("--energy-ratio", type=float, default=2.0,
                        help="Hybrid stopping threshold (default: 2.0)")
    args = parser.parse_args()

    img = np.asarray(Image.open(args.input).convert("RGB"))
    h, w = img.shape[:2]

    if args.info:
        cls = classify_image(img)
        energy = compute_energy(resize_scale(img, min(256, w), min(256, h)))
        print(f"Image:        {args.input}")
        print(f"Size:         {w}x{h}")
        print(f"Class:        {cls.value}")
        print(f"Edge density: {_edge_density(energy):.3f}")
        print(f"Energy entr.: {_energy_entropy(energy):.3f}")
        print(f"Color ratio:  {_unique_colors_approx(img):.3f}")
        print(f"Selected:     {ALGO_MAP[cls] if args.algo == 'auto' else args.algo}")
        return

    if args.output is None or args.width is None:
        parser.error("output and width are required unless --info is used")

    new_h = args.height or args.width
    result = resize_auto(img, args.width, new_h,
                         prefer=None if args.algo == "auto" else args.algo)
    Image.fromarray(result).save(args.output)
    print(f"{w}x{h} -> {result.shape[1]}x{result.shape[0]}  ({args.algo})  -> {args.output}")


if __name__ == "__main__":
    main()
