"""
Clean up source assets that lack proper alpha channels by removing their
edge-connected solid-color backgrounds. Saves results in-place as PNG.

Targets:
  - 8 character files saved as RGB with a black backdrop
  - stickers/29_NyanKitty.jpg with a white backdrop (also converted to PNG)
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

REPO = os.path.dirname(os.path.abspath(__file__))


def strip_edge_bg(img, predicate):
    """Make pixels matching `predicate(rgb_array)` transparent IF they are
    connected (4-neighbour) to one of the four image edges. Returns RGBA image."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    rgb = arr[..., :3].astype(np.int32)
    bg_pixels = predicate(rgb)              # H x W bool

    labels, _ = ndimage.label(bg_pixels)

    edge_labels = set()
    edge_labels.update(np.unique(labels[0,  :]))
    edge_labels.update(np.unique(labels[-1, :]))
    edge_labels.update(np.unique(labels[:,  0]))
    edge_labels.update(np.unique(labels[:, -1]))
    edge_labels.discard(0)

    if not edge_labels:
        return img

    bg_mask = np.isin(labels, list(edge_labels))
    arr[..., 3][bg_mask] = 0
    return Image.fromarray(arr, "RGBA")


def is_dark(rgb, threshold=60):
    return rgb.sum(axis=2) <= threshold


def is_near_white(rgb, threshold=720):  # >= 240 avg
    return rgb.sum(axis=2) >= threshold


def process(path, predicate, out_path=None, delete_original=False):
    img = Image.open(path)
    cleaned = strip_edge_bg(img, predicate)
    out_path = out_path or path
    cleaned.save(out_path, "PNG")
    if delete_original and path != out_path:
        os.remove(path)
    # Quick stats
    alpha = np.array(cleaned)[..., 3]
    pct_transparent = (alpha == 0).sum() / alpha.size
    print(f"  {os.path.basename(path):40s} -> {os.path.basename(out_path):40s}  ({pct_transparent:.0%} transparent)")


def main():
    print("Characters (black backdrop -> transparent):")
    char_dir = os.path.join(REPO, "Characters")
    for f in sorted(os.listdir(char_dir)):
        if not f.lower().endswith(".png"):
            continue
        path = os.path.join(char_dir, f)
        if Image.open(path).mode == "RGB":
            process(path, is_dark)

    print("\nStickers (NyanKitty: white backdrop -> transparent, .jpg -> .png):")
    sticker_path = os.path.join(REPO, "stickers", "29_NyanKitty.jpg")
    if os.path.exists(sticker_path):
        png_path = sticker_path[:-4] + ".png"
        process(sticker_path, is_near_white, out_path=png_path, delete_original=True)


if __name__ == "__main__":
    main()
