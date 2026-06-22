import streamlit as st
import numpy as np
from PIL import Image
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from resizer import (
    resize_seam, resize_scale, resize_crop, resize_letterbox,
    resize_hybrid, resize_auto, classify_image, ImageClass
)

st.set_page_config(page_title="Image Resizer", layout="wide")
st.title("Content-Aware Image Resizer")

algos = {
    "Auto (classify)": "auto",
    "Seam Carving (forward)": "seam_fwd",
    "Seam Carving (backward)": "seam_bwd",
    "Scaling (Lanczos)": "scale",
    "Smart Crop (entropy)": "crop",
    "Letterbox": "letterbox",
    "Adaptive Hybrid": "hybrid",
}

uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "bmp", "tiff"])

if uploaded:
    pil = Image.open(uploaded).convert("RGB")
    img = np.asarray(pil)
    h, w = img.shape[:2]

    st.subheader("Original")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(pil, caption=f"{w}x{h}", use_container_width=True)
    with col2:
        st.markdown(f"**Dimensions:** {w} x {h} px")

    st.subheader("Settings")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        algo_label = st.selectbox("Algorithm", list(algos.keys()), index=0)
        algo = algos[algo_label]
    with c2:
        new_w = st.number_input("Target width", min_value=32, max_value=w, value=w // 2, step=1)
    with c3:
        new_h = st.number_input("Target height", min_value=32, max_value=h, value=h // 2, step=1)
    with c4:
        energy_ratio = st.slider("Energy ratio (hybrid)", 1.0, 5.0, 2.0, 0.1)

    if st.button("Resize", type="primary"):
        with st.spinner("Processing ..."):
            try:
                if algo == "seam_fwd":
                    result = resize_seam(img, new_w, new_h, forward=True)
                    label = "Seam (forward)"
                elif algo == "seam_bwd":
                    result = resize_seam(img, new_w, new_h, forward=False)
                    label = "Seam (backward)"
                elif algo == "scale":
                    result = resize_scale(img, new_w, new_h)
                    label = "Scale"
                elif algo == "crop":
                    result = resize_crop(img, new_w, new_h)
                    label = "Crop"
                elif algo == "letterbox":
                    result = resize_letterbox(img, new_w, new_h)
                    label = "Letterbox"
                elif algo == "hybrid":
                    result = resize_hybrid(img, new_w, new_h, energy_ratio=energy_ratio)
                    label = "Hybrid (adaptive)"
                else:
                    result = resize_auto(img, new_w, new_h)
                    label = "Auto"
                    cls = classify_image(img)
                    st.info(f"Classified as: **{cls.value}** → algorithm: **{({'PHOTO': 'hybrid', 'GRAPHIC': 'scale', 'TEXT': 'scale', 'DEFAULT': 'hybrid'})[cls.name]}**")

                st.subheader("Result")
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.image(Image.fromarray(result), caption=f"{label}  {new_w}x{new_h}", use_container_width=True)
                with col_b:
                    st.markdown(f"**Algorithm:** {label}")
                    st.markdown(f"**Dimensions:** {result.shape[1]} x {result.shape[0]} px")
                    buf = Image.fromarray(result)
                    buf.save("_preview.jpg", quality=92)
                    with open("_preview.jpg", "rb") as f:
                        st.download_button("Download result", f, file_name=f"resized_{uploaded.name}", mime="image/jpeg")

            except Exception as e:
                st.error(f"Error: {e}")
