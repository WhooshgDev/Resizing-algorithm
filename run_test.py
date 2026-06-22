import subprocess, sys, os

files = sorted([f for f in os.listdir("test_images") if f.endswith(".jpg")])
rows = []
for fn in files:
    path = os.path.join("test_images", fn)
    proc = subprocess.run(
        [sys.executable, "resizer.py", path, "--info"],
        capture_output=True, text=True
    )
    info = {}
    for line in proc.stdout.strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    cls = info.get("Class", "?")
    ed = info.get("Edge density", "?")
    ee = info.get("Energy entr.", "?")
    cr = info.get("Color ratio", "?")
    sel = info.get("Selected", "?")
    rows.append((fn, cls, ed, ee, cr, sel))
    print(f"{fn:30s} | {cls:10s} | {ed:8s} | {ee:8s} | {cr:8s} | {sel}")
