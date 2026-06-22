import base64, os, json

def img_to_b64(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
        ext = path.rsplit(".", 1)[-1].lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
        return f"data:{mime.get(ext, 'image/jpeg')};base64,{b64}"

ORIG_MAP = {"photo": "picsum_0", "text": "gen_text", "chart": "gen_chart", "ui": "gen_ui", "graphic": "gen_graphic"}
PREFIX_MAP = {"photo": "photo", "text": "text", "chart": "chart", "ui": "ui", "graphic": "graphic"}

def out_path(label, algo):
    l = label.lower()
    if algo == "original":
        return f"test_images/{ORIG_MAP[l]}.jpg"
    return f"out_{PREFIX_MAP[l]}_{algo}.jpg"

sets = [
    {
        "name": "Photo (Landscape)",
        "label": "Photo",
        "algo_files": {a: out_path("Photo", a) for a in ["original", "seam", "scale", "crop", "letterbox", "hybrid"]},
        "class": "default",
        "note": "Natural scene with varied content — seam carving preserves important features"
    },
    {
        "name": "Text Document",
        "label": "Text",
        "algo_files": {a: out_path("Text", a) for a in ["original", "seam", "scale", "crop", "letterbox", "hybrid"]},
        "class": "graphic",
        "note": "Text-heavy — seam carving distorts lines, scale is best"
    },
    {
        "name": "Chart / Data Viz",
        "label": "Chart",
        "algo_files": {a: out_path("Chart", a) for a in ["original", "seam", "scale", "crop", "letterbox", "hybrid"]},
        "class": "graphic",
        "note": "Bar chart — seam carving distorts proportions, scale preserves data integrity"
    },
    {
        "name": "UI Screenshot",
        "label": "UI",
        "algo_files": {a: out_path("UI", a) for a in ["original", "seam", "scale", "crop", "letterbox", "hybrid"]},
        "class": "graphic",
        "note": "UI layout — seam carving misaligns elements, scale is safe"
    },
    {
        "name": "Abstract Graphic",
        "label": "Graphic",
        "algo_files": {a: out_path("Graphic", a) for a in ["original", "seam", "scale", "crop", "letterbox", "hybrid"]},
        "class": "default",
        "note": "Random circles — seam carving preserves circle shapes in sparse regions"
    },
]

# Embed all images as base64
for s in sets:
    for algo, fpath in s["algo_files"].items():
        s[f"b64_{algo}"] = img_to_b64(fpath) if os.path.exists(fpath) else ""

algos = ["original", "seam", "scale", "crop", "letterbox", "hybrid"]
algo_labels = {
    "original": "Original",
    "seam": "Seam Carve",
    "scale": "Scale (Lanczos)",
    "crop": "Smart Crop",
    "letterbox": "Letterbox",
    "hybrid": "Adaptive Hybrid"
}
algo_colors = {
    "original": "#6b7280",
    "seam": "#ef4444",
    "scale": "#3b82f6",
    "crop": "#10b981",
    "letterbox": "#f59e0b",
    "hybrid": "#8b5cf6"
}
algo_best_for = {
    "original": "",
    "seam": "Photos with clear subjects",
    "scale": "Graphics, text, UI, charts",
    "crop": "Strong focal point",
    "letterbox": "Aspect-ratio preservation",
    "hybrid": "General-purpose / photos (adaptive)"
}
algo_class_match = {
    "original": "",
    "seam": "photo",
    "scale": "graphic · text · default",
    "crop": "graphic",
    "letterbox": "any",
    "hybrid": "default · photo"
}

# Algorithm explanation cards
algo_explain = {
    "seam": {
        "how": "Finds and removes the lowest-energy path of pixels (a 'seam') using dynamic programming. Each seam removal reduces image width or height by 1. Uses <strong>forward energy</strong> (Rubinstein et al. 2008): it minimizes the new edges <em>created</em> by seam removal, not just the energy of removed pixels.",
        "when": "Photos with clear subjects against uniform backgrounds. Avoid for text, UI, charts — seams cut through structured content and distort lines."
    },
    "scale": {
        "how": "Standard interpolation using Lanczos resampling. Maps the original image grid onto the target grid, computing each output pixel as a weighted sum of nearby input pixels. Lanczos-3 sinc-based kernel preserves sharpness better than bilinear or bicubic.",
        "when": "Universal safe choice. Best for text, screenshots, UI, charts, diagrams — anything where content must remain geometrically intact."
    },
    "crop": {
        "how": "Divides the image into 16&times;16 tiles and computes the entropy (information density) of each. Uses a summed-area table to efficiently find the rectangular crop window that maximizes total entropy. The crop is then scaled to the exact target size.",
        "when": "Images with a strong focal point surrounded by uniform regions (e.g., a face in the center). Fails when important content is near the edges."
    },
    "letterbox": {
        "how": "Scales the image to fit within the target dimensions while preserving aspect ratio, then fills the remaining area with a solid color (default black).",
        "when": "When aspect ratio must be preserved exactly. Common for video thumbnails, social media previews, and presentation slides."
    },
    "hybrid": {
        "how": "<strong>Two-stage retargeting (Rubinstein et al. 2009):</strong><br><br>"
             "<strong>Stage 1 — Adaptive seam carving:</strong> Remove seams one at a time using forward-energy DP. Track a rolling median of seam energies. When the current seam's energy exceeds 2&times; the baseline, stop — the remaining content is too important to carve safely.<br><br>"
             "<strong>Stage 2 — Lanczos scale:</strong> The pixel deficit not handled by seam carving is covered with standard interpolation. This preserves content that would have been distorted by aggressive carving.<br><br>"
             "<strong>Key insight:</strong> The image <em>itself</em> decides the split. Uniform regions are carved away (zero cost), while dense content triggers early switching to scaling.",
        "when": "General-purpose resizing. Auto-classifier selects this for photos and default-class images."
    }
}

rows_html = ""
for s in sets:
    row_cells = ""
    for a in algos:
        b64 = s.get(f"b64_{a}", "")
        label = algo_labels[a]
        color = algo_colors[a]
        best = algo_best_for[a]
        match = algo_class_match[a]
        if a == "original":
            sizes = "800 &times; 600"
        else:
            sizes = "400 &times; 300" if s["label"] != "Photo" else "400 &times; 400"
        row_cells += f"""
        <td class="algo-col">
            <div class="algo-header" style="--accent:{color}">
                <span class="algo-name">{label}</span>
                <span class="algo-size">{sizes}</span>
            </div>
            <div class="img-wrap">
                <img src="{b64}" alt="{label}" loading="lazy">
            </div>
            <div class="algo-meta">
                <span class="badge" style="background:{color}20;color:{color}">{match}</span>
                <span class="best-for">{best}</span>
            </div>
        </td>"""

    rows_html += f"""
    <tr>
        <td class="info-col">
            <div class="img-label">{s['label']}</div>
            <div class="img-name">{s['name']}</div>
            <div class="class-badge" style="background:{'#8b5cf6' if s['class']=='default' else '#3b82f6'}">{s['class']}</div>
            <div class="img-note">{s['note']}</div>
        </td>
        {row_cells}
    </tr>"""

# Build algorithm explanation cards
algo_cards = ""
for a in algos:
    if a == "original":
        continue
    expl = algo_explain[a]
    color = algo_colors[a]
    label = algo_labels[a]
    match = algo_class_match[a]
    best = algo_best_for[a]
    how = expl["how"]
    when = expl["when"]
    algo_cards += f"""
    <div class="algo-card" style="border-left:3px solid {color};">
        <div class="card-header">
            <span class="card-badge" style="background:{color}20;color:{color}">{match}</span>
            <span class="card-label" style="color:{color}">{label}</span>
            <span class="card-best">{best}</span>
        </div>
        <div class="card-body">
            <div class="card-section">
                <div class="card-section-title">How it works</div>
                <p>{how}</p>
            </div>
            <div class="card-section">
                <div class="card-section-title">When to use</div>
                <p>{when}</p>
            </div>
        </div>
    </div>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Image Resizing Algorithm Comparison</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0e0e10; color:#e5e5e5; padding:24px; }}
h1 {{ text-align:center; font-size:1.8rem; font-weight:700; margin-bottom:6px; letter-spacing:-0.02em; }}
.subtitle {{ text-align:center; color:#888; font-size:0.9rem; margin-bottom:6px; }}
.hero-desc {{ max-width:720px; margin:0 auto 28px; text-align:center; font-size:0.82rem; color:#999; line-height:1.6; }}

.table-wrap {{ overflow-x:auto; margin-bottom:40px; }}
table {{ border-collapse:collapse; width:100%; min-width:1000px; background:#141416; border-radius:8px; overflow:hidden; }}
th {{ padding:10px 8px; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:#888; text-align:center; border-bottom:1px solid #2a2a2d; background:#1a1a1e; }}
th:first-child {{ text-align:left; width:180px; }}
td {{ padding:0; vertical-align:top; border-right:1px solid #222226; }}
td:last-child {{ border-right:none; }}
.info-col {{ padding:16px !important; width:180px; min-width:160px; }}
.img-label {{ font-size:1.1rem; font-weight:700; color:#fff; margin-bottom:2px; }}
.img-name {{ font-size:0.75rem; color:#888; margin-bottom:8px; }}
.class-badge {{ display:inline-block; padding:2px 10px; border-radius:99px; font-size:0.7rem; font-weight:600; color:#fff; margin-bottom:8px; }}
.img-note {{ font-size:0.72rem; color:#999; line-height:1.4; }}
.algo-col {{ text-align:center; }}
.algo-header {{ padding:10px 8px; border-bottom:2px solid var(--accent); background:#1a1a1e; }}
.algo-name {{ display:block; font-size:0.8rem; font-weight:600; color:var(--accent); }}
.algo-size {{ display:block; font-size:0.65rem; color:#666; margin-top:2px; }}
.img-wrap {{ padding:8px; }}
.img-wrap img {{ width:100%; height:auto; display:block; border-radius:4px; }}
.algo-meta {{ padding:6px 8px 10px; }}
.badge {{ display:inline-block; padding:1px 8px; border-radius:99px; font-size:0.65rem; font-weight:600; margin-bottom:4px; }}
.best-for {{ display:block; font-size:0.62rem; color:#666; line-height:1.3; }}
.legend {{ display:flex; justify-content:center; gap:24px; flex-wrap:wrap; margin:24px 0 20px; padding:14px 20px; background:#1a1a1e; border-radius:8px; }}
.legend-item {{ display:flex; align-items:center; gap:8px; font-size:0.78rem; color:#bbb; }}
.legend-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}

.section-title {{ font-size:1.2rem; font-weight:600; margin-bottom:16px; margin-top:8px; }}
.section-desc {{ font-size:0.82rem; color:#999; line-height:1.6; margin-bottom:20px; max-width:720px; }}

.algo-cards {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:40px; }}
@media(max-width:800px) {{ .algo-cards {{ grid-template-columns:1fr; }} }}
.algo-card {{ background:#1a1a1e; border-radius:8px; padding:16px; }}
.card-header {{ display:flex; align-items:center; gap:10px; margin-bottom:14px; flex-wrap:wrap; }}
.card-badge {{ display:inline-block; padding:1px 8px; border-radius:99px; font-size:0.65rem; font-weight:600; }}
.card-label {{ font-size:0.9rem; font-weight:700; }}
.card-best {{ font-size:0.7rem; color:#666; }}
.card-body {{ font-size:0.78rem; color:#ccc; line-height:1.6; }}
.card-section {{ margin-bottom:12px; }}
.card-section:last-child {{ margin-bottom:0; }}
.card-section-title {{ font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:#666; margin-bottom:4px; }}
.card-body p {{ margin:0; }}
.card-body code {{ background:#2a2a2e; padding:1px 5px; border-radius:3px; font-size:0.75rem; }}

.info-panels {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; max-width:800px; margin:0 auto 30px; }}
@media(max-width:700px) {{ .info-panels {{ grid-template-columns:1fr; }} }}
.panel {{ padding:20px; background:#1a1a1e; border-radius:8px; }}
.panel h2 {{ font-size:1rem; margin-bottom:10px; }}
.panel table {{ width:100%; font-size:0.78rem; border-collapse:collapse; }}
.panel th {{ text-align:left; padding:6px 8px; border-bottom:1px solid #2a2a2d; color:#888; font-weight:600; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em; background:transparent; }}
.panel td {{ padding:6px 8px; border-bottom:1px solid #2a2a2e; }}
.panel p {{ font-size:0.75rem; color:#888; margin-top:10px; line-height:1.5; }}
.panel code {{ background:#2a2a2e; padding:1px 5px; border-radius:3px; font-size:0.72rem; }}

.num {{ font-weight:600; }}
.num-carve {{ color:#8b5cf6; }}
.num-scale {{ color:#3b82f6; }}

footer {{ text-align:center; color:#444; font-size:0.7rem; margin-top:40px; padding-top:20px; border-top:1px solid #222; }}
</style>
</head>
<body>

<h1>&#9670; Image Resizing Algorithm Comparison</h1>
<p class="subtitle">Five algorithms &middot; Five image types &middot; 30 comparisons &middot; Auto-classifier</p>
<p class="hero-desc">
This page compares six approaches to resizing images: <strong>seam carving</strong>, <strong>Lanczos scaling</strong>,
<strong>entropy-based cropping</strong>, <strong>letterboxing</strong>, and an <strong>adaptive hybrid</strong> that
intelligently switches between seam carving and scaling based on the image content.
The <strong>auto-classifier</strong> examines edge density, color richness, and energy entropy to pick the best algorithm automatically.
</p>

<div class="legend">
    <span class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>Seam Carve</span>
    <span class="legend-item"><span class="legend-dot" style="background:#3b82f6"></span>Scale (Lanczos)</span>
    <span class="legend-item"><span class="legend-dot" style="background:#10b981"></span>Smart Crop</span>
    <span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span>Letterbox</span>
    <span class="legend-item"><span class="legend-dot" style="background:#8b5cf6"></span>Adaptive Hybrid</span>
</div>

<div class="table-wrap">
<table>
<thead>
<tr>
    <th>Image</th>
    <th>Original</th>
    <th>Seam Carve</th>
    <th>Scale (Lanczos)</th>
    <th>Smart Crop</th>
    <th>Letterbox</th>
    <th>Adaptive Hybrid</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>

<h2 class="section-title">How each algorithm works</h2>
<p class="section-desc">Each algorithm makes different tradeoffs between content preservation, distortion, and aspect ratio. The table above shows the visual results; here is how each one works under the hood.</p>

<div class="algo-cards">
{algo_cards}
</div>

<h2 class="section-title">Adaptive hybrid &mdash; detailed walkthrough</h2>
<p class="section-desc">
The hybrid algorithm is the most sophisticated approach. It combines seam carving with scaling and uses the image's
own energy landscape to decide which pixels to carve and which to preserve. Here is exactly how it works.
</p>

<div class="algo-card" style="border-left:3px solid #8b5cf6;margin-bottom:26px;max-width:800px;">
    <div class="card-body">
        <div class="card-section">
            <div class="card-section-title">Forward-energy seam carving (stage 1)</div>
            <p>
            Traditional seam carving (<em>Avidan &amp; Shamir 2007</em>) removes pixels with the lowest <strong>backward energy</strong>
            (gradient magnitude = how much the pixel differs from its neighbors). But this ignores a key fact:
            removing a pixel creates <em>new edges</em> between its former neighbors.
            </p>
            <p style="margin-top:8px;">
            <strong>Forward energy</strong> (<em>Rubinstein et al. 2008</em>) fixes this. It precomputes the cost of the
            new edges that would appear after removal. For a pixel <code>(i,j)</code>, it computes three costs
            depending on which direction the seam entered from above:
            </p>
            <pre style="background:#2a2a2e;border-radius:6px;padding:12px;font-size:0.72rem;line-height:1.5;margin-top:8px;overflow-x:auto;">
M_LR = |I(i,j+1) - I(i,j-1)|           # new edge between left & right neighbors
M_LU = |I(i-1,j) - I(i,j-1)|           # extra cost if seam came from top-left
M_RU = |I(i-1,j) - I(i,j+1)|           # extra cost if seam came from top-right

CL = M_LR + M_LU   # cost when seam enters from top-left
CU = M_LR          # cost when seam enters straight from above
CR = M_LR + M_RU   # cost when seam enters from top-right

dp[i,j] = min(dp[i-1,j-1]+CL, dp[i-1,j]+CU, dp[i-1,j+1]+CR)</pre>
            <p style="margin-top:8px;">
            The DP finds the seam that introduces the <em>least visible change</em> to the image —
            not just the one through boring pixels.
            </p>
        </div>
        <div class="card-section">
            <div class="card-section-title">Adaptive stopping criterion (the key innovation)</div>
            <p>
            The algorithm tracks the forward energy of every seam it removes. After each seam, it computes a <strong>rolling median</strong>
            of non-zero seam energies (skipping zero-energy seams through uniform regions). When the current seam's energy exceeds
            <strong>2&times; the median baseline</strong>, it stops carving immediately:
            </p>
            <pre style="background:#2a2a2e;border-radius:6px;padding:12px;font-size:0.72rem;line-height:1.5;margin-top:8px;overflow-x:auto;">
nonzero = [e for e in seam_energies if e > 1e-6]
if len(nonzero) >= 5 and i >= 10:
    baseline = median(nonzero)            # median, not mean — robust to outliers
    if norm_e > baseline * 2.0:           # energy spiked — switch to scaling
        break</pre>
            <p style="margin-top:8px;">
            Using <strong>median</strong> instead of mean prevents a single expensive seam from raising the
            baseline. Skipping zero-energy seams avoids triggering the stop when the first uneven pixel is
            encountered in an otherwise uniform image.
            </p>
        </div>
        <div class="card-section">
            <div class="card-section-title">Lanczos scaling (stage 2)</div>
            <p>
            Any remaining pixel deficit not handled by seam carving is covered with <strong>Lanczos-3 interpolation</strong>.
            This preserves the geometric integrity of dense content (faces, text, edges) that the adaptive criterion
            identified as too expensive to carve.
            </p>
        </div>
        <div class="card-section">
            <div class="card-section-title">Why this beats a fixed fraction</div>
            <p>
            A fixed 70/30 split (carve 70%, scale 30%) applies the same policy to every image. The adaptive
            approach lets the <em>image itself</em> decide:
            </p>
            <ul style="margin-top:6px;padding-left:18px;font-size:0.76rem;">
            <li><strong>Photo with 60% uniform sky:</strong> Adaptive carves ~90% of the sky. Only stops when hitting trees. Fixed 70% would carve 70% indiscriminately and potentially cut into important ground content.</li>
            <li style="margin-top:4px;"><strong>Text document with narrow margins:</strong> Adaptive carves ~10% (the white margins), then switches to scaling. Fixed 70% would carve too deep and distort letters.</li>
            <li style="margin-top:4px;"><strong>Chart with wide borders:</strong> Adaptive carves all borders (zero cost), stops at the bars. Fixed 70% might carve into the bars and distort the data.</li>
            </ul>
        </div>
    </div>
</div>

<div class="info-panels">
<div class="panel">
    <h2>How the auto-classifier decides</h2>
    <table>
        <tr><th>Feature</th><th>Photo</th><th>Graphic</th><th>Text</th></tr>
        <tr><td>Edge density</td><td>low</td><td>low-mid</td><td>high</td></tr>
        <tr><td>Color richness</td><td>high</td><td>low</td><td>low</td></tr>
        <tr><td>Selected algo</td><td><span class="num" style="color:#8b5cf6">hybrid</span></td><td><span class="num" style="color:#3b82f6">scale</span></td><td><span class="num" style="color:#3b82f6">scale</span></td></tr>
    </table>
    <p>Run <code>python resizer.py image.jpg --info</code> to see per-image classification. The classifier examines <strong>three features</strong> at 256&times;256 resolution: edge density (&gt;50% max gradient), normalized energy entropy, and approximate unique color ratio via random sampling (4096 pixels).</p>
</div>
<div class="panel">
    <h2>Adaptive hybrid decisions</h2>
    <p style="font-size:0.72rem;color:#999;margin-top:0;">Format: <span class="num num-carve">carved</span> + <span class="num num-scale">scaled</span> (width+height)</p>
    <table>
        <tr><th>Image</th><th style="text-align:right;">Seams carved</th><th style="text-align:right;">Scaled</th></tr>
        <tr><td>Photo</td><td style="text-align:right;"><span class="num num-carve">400 + 15</span></td><td style="text-align:right;"><span class="num num-scale">0 + 285</span></td></tr>
        <tr><td>Text</td><td style="text-align:right;"><span class="num num-carve">96 + 102</span></td><td style="text-align:right;"><span class="num num-scale">304 + 198</span></td></tr>
        <tr><td>Chart</td><td style="text-align:right;"><span class="num num-carve">234 + 300</span></td><td style="text-align:right;"><span class="num num-scale">166 + 0</span></td></tr>
        <tr><td>UI</td><td style="text-align:right;"><span class="num num-carve">144 + 210</span></td><td style="text-align:right;"><span class="num num-scale">256 + 90</span></td></tr>
        <tr><td>Graphic</td><td style="text-align:right;"><span class="num num-carve">365 + 300</span></td><td style="text-align:right;"><span class="num num-scale">35 + 0</span></td></tr>
    </table>
    <p>Seams are removed from low-energy regions first. The algorithm switches to scaling as soon as seam energy spikes above 2&times; the baseline median, protecting important content from distortion.</p>
</div>
</div>

<footer>
    Generated with <code>resizer.py</code> &mdash; Forward-energy seam carving &middot; Adaptive multi-operator hybrid &middot; Auto-classifier<br>
    Based on Avidan &amp; Shamir 2007, Rubinstein et al. 2008 &amp; 2009 &mdash; 5 image types, 30 comparisons
</footer>
</body>
</html>"""

with open("comparison.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"comparison.html written ({len(html)} bytes)")
