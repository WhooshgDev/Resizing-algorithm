"""Debug chart image seams."""
import numpy as np
from PIL import Image
from resizer import _forward_cost, _find_seam_forward, _remove_seam

name = "test_images/gen_chart.jpg"
img = np.asarray(Image.open(name).convert("RGB"))
print(f"Chart image shape: {img.shape}")

# Check if the image is all white initially
print(f"Unique values in first row: {len(np.unique(img[0, :, :]))}")
print(f"First row min/max: {img[0, :, :].min()}/{img[0, :, :].max()}")

working = img.astype(np.float64)
for i in range(5):
    seam, fe = _find_seam_forward(working)
    norm_e = fe / working.shape[0]
    # Where does the seam go?
    seam_path = seam
    print(f"Seam {i}: energy/row={norm_e:.6f}, "
          f"col range=[{seam.min()}, {seam.max()}], "
          f"first5={seam[:5]}, mid5={seam[300:305]}, last5={seam[-5:]}")
    working = _remove_seam(working, seam)
