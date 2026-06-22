"""Debug forward seam with middle rows."""
import numpy as np
from PIL import Image
from resizer import _forward_cost, _find_seam_forward, compute_energy

img = np.asarray(Image.open("test_images/picsum_0.jpg").convert("RGB"))
h, w = img.shape[:2]

# Check non-zero content
for row in [0, 100, 300, 500]:
    vals = img[row, :, :]
    non_zero = np.any(vals > 10, axis=1)
    print(f"Row {row}: {np.sum(non_zero)}/{w} non-black pixels")

# Run debug on a sub-region that has content
# Cut to a region with actual image content
sub = img[100:300, 100:300, :]
print(f"\nSub-image shape: {sub.shape}")
CL, CU, CR = _forward_cost(sub)
print(f"CU min={CU.min():.1f} max={CU.max():.1f} mean={CU.mean():.1f}")

seam, energy = _find_seam_forward(sub)
print(f"Seam: {seam}")
print(f"Energy: {energy:.6f}")

# Compare with backward
be = compute_energy(sub)
from resizer import _find_seam_backward
bseam, benergy = _find_seam_backward(be)
print(f"Backward seam: {bseam[:10]}..{bseam[-5:]}")
print(f"Backward energy: {benergy:.6f}")
