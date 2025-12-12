import argparse
import cv2
from insightface.app import FaceAnalysis
import json
import os
from pathlib import Path


EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp']

app = FaceAnalysis(name='buffalo_l')  # Use 'CPUExecutionProvider' if no GPU
app.prepare(ctx_id=0, det_size=(640, 640))


def find_image_in_dir(dir_path):
    exts = EXTENSIONS
    for f in os.listdir(dir_path):
        p = os.path.join(dir_path, f)
        if os.path.isfile(p) and Path(p).suffix.lower() in exts:
            return p
    return None


def resolve_image_path(image_path):
        p = Path(image_path)
        # If p is a directory, find the first supported file
        if p.is_dir():
            for f in p.iterdir():
                if f.is_file() and f.suffix.lower() in EXTENSIONS:
                    return str(f)
            return None
        # If it's a file with a known extension, accept it
        if p.is_file() and p.suffix.lower() in EXTENSIONS:
            return str(p)
        # If it exists but has unknown extension, try adding known extensions
        if p.exists() and p.is_file() and p.suffix.lower() not in EXTENSIONS:
            for ext in EXTENSIONS:
                candidate = p.with_suffix(ext)
                if candidate.is_file():
                    return str(candidate)
            return None
        # If p doesn't exist, try parent directory + stem + ext
        parent = p.parent if p.parent != Path('.') else Path.cwd()
        for ext in EXTENSIONS:
            candidate = parent / (p.stem + ext)
            if candidate.is_file():
                return str(candidate)
        return None


def generate_embedding(image_path, save_path):
    # Resolve image path; support directories, filenames without extension, or exact files
    found = resolve_image_path(image_path)
    if not found:
        raise FileNotFoundError(f"No supported image found at or near: {image_path}")
    image_path = found

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image file at: {image_path}. Check the path and file integrity.")

    faces = app.get(img)
    if not faces:
        raise RuntimeError("No faces detected in provided image. Try a different photo with a clear frontal face.")

    emb = faces[0].embedding.tolist()
    # Ensure directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w') as f:
        json.dump(emb, f)
    print(f"✅ Saved embedding to {save_path}")

def main():
    parser = argparse.ArgumentParser(description="Register a student's face embedding")
    parser.add_argument('--name', '-n', help='Student name (no spaces recommended)')
    parser.add_argument('--image', '-i', help='Path to student image (file or directory containing image)')
    parser.add_argument('--bulk', action='store_true', help='Register all images in a directory (use --image PATH_TO_DIR)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing embedding files')
    args = parser.parse_args()

    if args.name:
        name = args.name.strip()
    else:
        name = input("Enter the name of the student: ").strip()

    if args.image:
        image_path = args.image.strip()
    else:
        image_path = input("Enter the path of the image (file or folder): ").strip()

    if not name:
        print("Student name is required.")
        return

    if not image_path and not args.bulk:
        print("Image path is required (unless using --bulk directory registration).")
        return

    if args.bulk:
        folder = Path(image_path)
        if not folder.is_dir():
            print("Bulk mode requires a directory path in --image")
            return
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS]
        if not files:
            print(f"No supported images found in {folder}")
            return
        for f in files:
            student_name = f.stem
            save_path = Path('student_data') / f"{student_name}_embedding.json"
            if save_path.exists() and not args.overwrite:
                print(f"Skipping {student_name} - embedding exists. Use --overwrite to replace.")
                continue
            try:
                generate_embedding(str(f), str(save_path))
            except Exception as e:
                print(f"❌ Failed to generate embedding for {f.name}: {e}")
        print("✅ Bulk registration complete.")
        return

    save_path = f"student_data/{name}_embedding.json"

    if Path(save_path).exists() and not args.overwrite:
        print(f"Embedding for '{name}' already exists at {save_path}. Use --overwrite to replace.")
        return

    try:
        generate_embedding(image_path, save_path)
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")
        return


if __name__ == "__main__":
    main()