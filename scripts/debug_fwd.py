"""Debug forward cost computation."""
import numpy as np
from PIL import Image
from resizer import _forward_cost, _find_seam_forward

img = np.asarray(Image.open("test_images/picsum_0.jpg").convert("RGB"))
print(f"img dtype={img.dtype} shape={img.shape} min={img.min()} max={img.max()}")

CL, CU, CR = _forward_cost(img)
print(f"CL shape={CL.shape} min={CL.min():.6f} max={CL.max():.6f} mean={CL.mean():.6f}")
print(f"CU shape={CU.shape} min={CU.min():.6f} max={CU.max():.6f} mean={CU.mean():.6f}")
print(f"CR shape={CR.shape} min={CR.min():.6f} max={CR.max():.6f} mean={CR.mean():.6f}")

seam, energy = _find_seam_forward(img)
print(f"Seam: first5={seam[:5]} last5={seam[-5:]}")
print(f"Energy: {energy:.6f}")
