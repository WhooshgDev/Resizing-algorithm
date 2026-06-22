"""Debug: track seam energies during adaptive carving."""
import numpy as np
from PIL import Image
from resizer import compute_energy, _forward_cost, _find_seam_forward, _remove_seam

for name in ["test_images/picsum_0.jpg", "test_images/gen_text.jpg",
             "test_images/gen_chart.jpg", "test_images/gen_ui.jpg"]:
    img = np.asarray(Image.open(name).convert("RGB"))
    h, w = img.shape[:2]
    
    working = img.astype(np.float64)
    energies = []
    
    for i in range(min(20, w - 1)):
        seam, fe = _find_seam_forward(working)
        norm_e = fe / working.shape[0]
        energies.append(norm_e)
        working = _remove_seam(working, seam)
    
    print(f"{name:35s} first5 mean={np.mean(energies[:5]):.2f}  ", end="")
    for j in range(0, 20, 5):
        print(f" e[{j}]={energies[min(j, len(energies)-1)]:.2f}", end="")
    print(f"  ratio={energies[-1]/max(1e-8,energies[0]):.2f}")
