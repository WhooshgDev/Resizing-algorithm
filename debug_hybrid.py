"""Debug: show how many seams the adaptive hybrid removes vs scales."""
import numpy as np
from PIL import Image
from resizer import _carve_adaptive, resize_scale

for name in ["test_images/picsum_0.jpg", "test_images/gen_text.jpg",
             "test_images/gen_chart.jpg", "test_images/gen_ui.jpg",
             "test_images/gen_graphic.jpg"]:
    img = np.asarray(Image.open(name).convert("RGB"))
    h, w = img.shape[:2]
    new_w, new_h = 400, 300
    dw, dh = w - new_w, h - new_h

    # Vertical
    result_v, n_w = _carve_adaptive(img, dw, axis=0, energy_ratio=2.0)
    n_w_scale = dw - n_w

    # Horizontal
    result, n_h = _carve_adaptive(result_v, dh, axis=1, energy_ratio=2.0)
    n_h_scale = dh - n_h

    print(f"{name:35s} dw={dw:3d}: carve={n_w:3d} scale={n_w_scale:3d}  |  dh={dh:3d}: carve={n_h:3d} scale={n_h_scale:3d}")
