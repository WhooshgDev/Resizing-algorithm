# Image Resizing Algorithms with Seam Carving

A content-aware image resizing system with multiple algorithms and an auto-classifier.

## Quick Start

```bash
pip install -r requirements.txt

# Streamlit UI
streamlit run app.py

# CLI
python resizer.py input.jpg output.jpg 400 300
python resizer.py input.jpg output.jpg 400 300 --algo hybrid
python resizer.py input.jpg --info   # show classification
```

## Algorithms

| Algorithm | Description |
|-----------|-------------|
| `seam` | Seam carving (forward/backward energy) |
| `scale` | Lanczos interpolation |
| `crop` | Entropy-based smart crop |
| `letterbox` | Scale + aspect-ratio padding |
| `hybrid` | Adaptive: carve low-energy seams, then scale |
| `auto` | Classify image → pick best algorithm |

## Adaptive Hybrid

Dynamically switches from seam carving to scaling when seam energy exceeds a rolling median threshold:

```bash
python resizer.py input.jpg output.jpg 400 300 --algo hybrid --energy-ratio 2.0
```

## Auto-Classifier

Classifies images into TEXT/GRAPHIC/PHOTO/DEFAULT using edge density, color richness, and energy entropy. Maps to algorithm via predefined rules.

## Report

See `report/report.pdf` for full documentation (17 pages, English).

## Project structure

```
├── app.py              # Streamlit UI
├── resizer.py          # Main program
├── requirements.txt
├── report/             # LaTeX source + compiled PDF
├── output/             # Comparison images + HTML
└── test_images/        # 24 test images
```
