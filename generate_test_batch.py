"""
Sweetardios test batch generator — 20 NFTs.

Layer order (bottom to top): Background → Character → Face → Sticker
Canvas: 1080x1080 RGBA. All layers are resized (preserving aspect via fit-to-canvas)
to the canvas size before alpha compositing.
"""
import os
import json
import random
import hashlib
from PIL import Image

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "test_batch_20")
os.makedirs(OUT, exist_ok=True)

# Canvas at native source resolution. Characters are 1254-1341 px, faces are
# 1341-1343 px. Setting the canvas to 1343 means faces and most characters
# render at native resolution; smaller layers (stickers at 1080, smaller bgs)
# get upscaled rather than anything being downscaled and losing detail.
CANVAS_SIZE = (1343, 1343)
COLLECTION_NAME = "Sweetardios"
BATCH_SIZE = 20
SEED = 555  # batch with refreshed face set

# Layer order requested by user: background, character, Face, sticker
LAYERS = [
    ("Background", "Backgrounds"),
    ("Character",  "Characters"),
    ("Face",       "Face"),
    ("Sticker",    "stickers"),
]

VALID_EXT = (".png", ".webp", ".jpg", ".jpeg")


def list_assets(folder):
    """Return validated list of image files in folder, skipping anything PIL can't open."""
    folder_path = os.path.join(REPO, folder)
    out = []
    for f in sorted(os.listdir(folder_path)):
        if not f.lower().endswith(VALID_EXT):
            continue
        try:
            with Image.open(os.path.join(folder_path, f)) as im:
                im.verify()
            out.append(f)
        except Exception:
            print(f"  [skip] {folder}/{f} (not a valid image)")
    return out


def fit_to_canvas(img, size):
    """Resize so the image covers the canvas, preserving aspect, centered crop if needed.
    For backgrounds we want full coverage; for other transparent layers we just scale."""
    img = img.convert("RGBA")
    if img.size == size:
        return img
    # Scale preserving aspect ratio so the longer dim matches canvas, then paste centered.
    src_w, src_h = img.size
    scale = max(size[0] / src_w, size[1] / src_h)
    new_w, new_h = int(round(src_w * scale)), int(round(src_h * scale))
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    # Center-crop to canvas
    left = (new_w - size[0]) // 2
    top  = (new_h - size[1]) // 2
    return img.crop((left, top, left + size[0], top + size[1]))


def fit_inside(img, size):
    """Resize preserving aspect to fit inside the canvas (no crop). Pads with transparency."""
    img = img.convert("RGBA")
    if img.size == size:
        return img
    src_w, src_h = img.size
    scale = min(size[0] / src_w, size[1] / src_h)
    new_w, new_h = int(round(src_w * scale)), int(round(src_h * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(resized, ((size[0] - new_w) // 2, (size[1] - new_h) // 2), resized)
    return canvas


def trait_name_from_filename(filename):
    """Strip extension and clean up filename to make a presentable trait value."""
    name = os.path.splitext(filename)[0]
    # Tidy common patterns
    return name


def main():
    random.seed(SEED)

    # Load all assets
    assets = {}
    for trait, folder in LAYERS:
        files = list_assets(folder)
        assets[trait] = files
        print(f"{trait:12s} ({folder}): {len(files)} assets")

    print()
    if any(len(v) == 0 for v in assets.values()):
        raise SystemExit("Missing assets in one or more layers.")

    seen_combos = set()
    manifest = []

    for idx in range(1, BATCH_SIZE + 1):
        # Pick a unique combination
        for _ in range(200):
            combo = tuple(random.choice(assets[t]) for t, _ in LAYERS)
            if combo not in seen_combos:
                seen_combos.add(combo)
                break
        else:
            raise SystemExit(f"Could not find a unique combo for #{idx}")

        bg_file, char_file, face_file, sticker_file = combo

        # Build the canvas
        canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 255))

        # 1. Background — cover the canvas (crop/scale to fill)
        bg = Image.open(os.path.join(REPO, "Backgrounds", bg_file))
        canvas.alpha_composite(fit_to_canvas(bg, CANVAS_SIZE))

        # 2. Character, 3. Face, 4. Sticker — fit inside canvas preserving transparency
        for trait, folder, fname in [
            ("Character", "Characters", char_file),
            ("Face",      "Face",       face_file),
            ("Sticker",   "stickers",   sticker_file),
        ]:
            layer = Image.open(os.path.join(REPO, folder, fname))
            canvas.alpha_composite(fit_inside(layer, CANVAS_SIZE))

        # Save PNG
        out_png = os.path.join(OUT, f"{idx}.png")
        # Flatten transparency onto opaque before save (keeps it as RGBA but no alpha leftovers from BG)
        canvas.save(out_png, optimize=True)

        # Metadata
        attrs = [
            {"trait_type": "Background", "value": trait_name_from_filename(bg_file)},
            {"trait_type": "Character",  "value": trait_name_from_filename(char_file)},
            {"trait_type": "Face",       "value": trait_name_from_filename(face_file)},
            {"trait_type": "Sticker",    "value": trait_name_from_filename(sticker_file)},
        ]
        meta = {
            "name": f"{COLLECTION_NAME} #{idx}",
            "description": f"Test batch mint for the {COLLECTION_NAME} NFT collection.",
            "image": f"ipfs://CID/{idx}.png",
            "edition": idx,
            "attributes": attrs,
        }
        out_json = os.path.join(OUT, f"{idx}.json")
        with open(out_json, "w") as f:
            json.dump(meta, f, indent=2)

        # DNA hash for uniqueness reference
        dna = hashlib.sha1("|".join(combo).encode()).hexdigest()[:12]
        manifest.append({"id": idx, "dna": dna, **dict(zip(["bg","char","face","sticker"], combo))})
        print(f"#{idx:2d}  bg={bg_file[:38]:38s}  char={char_file[:22]:22s}  face={face_file[:14]:14s}  sticker={sticker_file[:30]}")

    # Save manifest
    with open(os.path.join(OUT, "_manifest.json"), "w") as f:
        json.dump({
            "collection": COLLECTION_NAME,
            "count": BATCH_SIZE,
            "layer_order": [t for t, _ in LAYERS],
            "canvas": list(CANVAS_SIZE),
            "seed": SEED,
            "items": manifest,
        }, f, indent=2)

    print(f"\nDone. Output: {OUT}")


if __name__ == "__main__":
    main()
