import os
import random
import json
from PIL import Image

# Define paths
repo_path = "/home/ubuntu/Sweetardios_NFT"
output_path = os.path.join(repo_path, "Layered_Test_Mint")
os.makedirs(output_path, exist_ok=True)

# Define trait order
trait_order = ["Background", "Character", "Face", "Eyes", "Stickers"]

# Map traits to folders
trait_folders = {
    "Background": "Backgrounds",
    "Character": "Characters",
    "Face": "Faces",
    "Eyes": "Eyes",
    "Stickers": "Stickers"
}

def get_assets():
    assets = {}
    for trait, folder in trait_folders.items():
        folder_path = os.path.join(repo_path, folder)
        if os.path.exists(folder_path):
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(('.png', '.webp', '.jpg', '.jpeg'))]
            if files:
                assets[trait] = files
    return assets

def generate_nft(index, assets):
    selected_traits = {}
    canvas = None
    
    metadata = {
        "name": f"Layered Sweetardio #{index}",
        "description": "A layered generative test mint for Sweetardios NFT collection.",
        "image": f"ipfs://CID/{index}.png",
        "attributes": []
    }

    for trait in trait_order:
        if trait in assets:
            chosen_file = random.choice(assets[trait])
            selected_traits[trait] = chosen_file
            metadata["attributes"].append({"trait_type": trait, "value": chosen_file})
            
            file_path = os.path.join(repo_path, trait_folders[trait], chosen_file)
            img = Image.open(file_path).convert("RGBA")
            
            if canvas is None:
                canvas = img
            else:
                # Resize to match canvas if necessary
                if img.size != canvas.size:
                    img = img.resize(canvas.size, Image.Resampling.LANCZOS)
                canvas.alpha_composite(img)

    if canvas:
        # Save image
        canvas.save(os.path.join(output_path, f"{index}.png"))
        # Save metadata
        with open(os.path.join(output_path, f"{index}.json"), "w") as f:
            json.dump(metadata, f, indent=4)
        return True
    return False

assets = get_assets()
for i in range(1, 11):
    if generate_nft(i, assets):
        print(f"Generated NFT #{i}")
    else:
        print(f"Failed to generate NFT #{i}")

print(f"Successfully generated 10 layered NFTs in {output_path}")
