"""Debug forward seam DP values."""
import numpy as np
from PIL import Image
from resizer import _forward_cost, _find_seam_forward, compute_energy

img = np.asarray(Image.open("test_images/picsum_0.jpg").convert("RGB"))
sub = img[100:300, 100:300, :]
h, w = sub.shape[:2]

CL, CU, CR = _forward_cost(sub)

# Manual DP to see values
dp = np.zeros((h, w), dtype=np.float64)
parent = np.zeros((h, w), dtype=np.int32)
dp[0] = CU[0]

for i in range(1, h):
    dp_left   = np.roll(dp[i-1], 1);  dp_left[0]   = np.inf
    dp_right  = np.roll(dp[i-1], -1); dp_right[-1]  = np.inf
    left  = dp_left  + CL[i]
    up    = dp[i-1]  + CU[i]
    right = dp_right + CR[i]
    best = np.minimum(np.minimum(left, up), right)
    best_col = np.argmin(best)
    parent[i] = np.argmin([left, up, right], axis=0) - 1
    dp[i] = best

# Print dp values for first few rows and columns
for i in range(5):
    print(f"dp[{i}] first 10: {[f'{x:.1f}' for x in dp[i, :10]]}")
    print(f"dp[{i}] argmin: {np.argmin(dp[i])}")

# Print dp values around middle to see if they vary
mid = w // 2
print(f"\nMiddle row dp values around center:")
for offset in [-5, -3, -1, 0, 1, 3, 5]:
    col = mid + offset
    if 0 <= col < w:
        print(f"  dp[50, {col}] = {dp[50, col]:.2f}")
