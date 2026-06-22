"""Debug forward DP in detail."""
import numpy as np
from PIL import Image
from resizer import _forward_cost, _find_seam_forward

img = np.asarray(Image.open("test_images/picsum_0.jpg").convert("RGB"))
h, w = img.shape[:2]
CL, CU, CR = _forward_cost(img)

# Debug: check cost matrices at the first few rows/cols
print("CU row 1 first 10:", [f"{x:.1f}" for x in CU[1, :10]])
print("CR row 1 first 10:", [f"{x:.1f}" for x in CR[1, :10]])
print("CL row 1 first 10:", [f"{x:.1f}" for x in CL[1, :10]])

# Check the image values in the first few rows to see if they make sense
print("img row 0, first 5 pixels:", img[0, :5])
print("img row 1, first 5 pixels:", img[1, :5])

# Now trace the DP manually for first 2 rows
dp = np.zeros((h, w), dtype=np.float64)

# Row 0: dp[0]=0 everywhere

# Row 1:
i = 1
dp_left = np.roll(dp[0], 1); dp_left[0] = np.inf
dp_right = np.roll(dp[0], -1); dp_right[-1] = np.inf
left = dp_left + CL[i]
up = dp[0] + CU[i]
right = dp_right + CR[i]
print(f"\nRow 1, col 0: left={left[0]:.3f} up={up[0]:.3f} right={right[0]:.3f}")
print(f"Row 1, col 1: left={left[1]:.3f} up={up[1]:.3f} right={right[1]:.3f}")
print(f"Row 1, col 2: left={left[2]:.3f} up={up[2]:.3f} right={right[2]:.3f}")

best = np.minimum(np.minimum(left, up), right)
print(f"Row 1, best first 10: {[f'{x:.2f}' for x in best[:10]]}")

# Now let's also test the backward energy to compare
from resizer import compute_energy
energy = compute_energy(img)
print(f"\nBackward energy row 1 first 10: {[f'{x:.2f}' for x in energy[1, :10]]}")
