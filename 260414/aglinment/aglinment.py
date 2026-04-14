import sys
import io
import cv2
import numpy as np
from pathlib import Path

# Fix Unicode issues on Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).parent
MOTION_TYPE = cv2.MOTION_AFFINE
THRESH_VAL = 25

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def imread_utf8(path: Path):
    """Đọc ảnh từ đường dẫn Unicode"""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    except Exception as e:
        print(f"  Error reading {path.name}: {e}")
        return None

def imwrite_utf8(path: Path, img: np.ndarray):
    """Lưu ảnh vào đường dẫn Unicode"""
    try:
        ext = path.suffix
        res, buf = cv2.imencode(ext, img)
        if res:
            buf.tofile(str(path))
            return True
    except Exception as e:
        print(f"  Error writing {path.name}: {e}")
    return False

def preprocess(gray: np.ndarray) -> np.ndarray:
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    return gray

def save_diff(name: str, ref_gray: np.ndarray, test_gray: np.ndarray, out_dir: Path):
    diff = cv2.absdiff(ref_gray, test_gray)
    _, mask = cv2.threshold(diff, THRESH_VAL, 255, cv2.THRESH_BINARY)

    imwrite_utf8(out_dir / f"{name}_diff.jpg", diff)
    imwrite_utf8(out_dir / f"{name}_mask.jpg", mask)

    nonzero = int(np.count_nonzero(mask))
    mean_diff = float(diff.mean())

    return nonzero, mean_diff

def align_ecc(ref_gray: np.ndarray, test_gray: np.ndarray, motion_type=cv2.MOTION_EUCLIDEAN):
    h, w = ref_gray.shape[:2]

    if motion_type == cv2.MOTION_HOMOGRAPHY:
        warp = np.eye(3, 3, dtype=np.float32)
    else:
        warp = np.eye(2, 3, dtype=np.float32)

    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        200,      # số vòng lặp tối đa
        1e-6      # epsilon hội tụ
    )

    cc, warp = cv2.findTransformECC(
        ref_gray,
        test_gray,
        warp,
        motion_type,
        criteria
    )

    if motion_type == cv2.MOTION_HOMOGRAPHY:
        aligned = cv2.warpPerspective(
            test_gray,
            warp,
            (w, h),
            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
            borderMode=cv2.BORDER_REPLICATE
        )
    else:
        aligned = cv2.warpAffine(
            test_gray,
            warp,
            (w, h),
            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
            borderMode=cv2.BORDER_REPLICATE
        )

    return aligned, warp, cc

def process_folder(folder_path: Path):
    print(f"--- Processing: {folder_path.name} ---")
    
    # Tìm file ảnh
    jpg_files = list(folder_path.glob("*.jpg"))
    if len(jpg_files) < 2:
        print(f"  Skipping: Not enough images (.jpg) in {folder_path.name}")
        return

    ref_path = None
    test_path = None

    # Tìm file reference dựa trên từ khóa
    for f in jpg_files:
        name_lower = f.name.lower()
        if "back" in name_lower or "background" in name_lower:
            ref_path = f
            break
            
    # Xác định file test là file còn lại (nếu có 2 file)
    if ref_path:
        remaining = [f for f in jpg_files if f != ref_path]
        if remaining:
            test_path = remaining[0]
    else:
        # Nếu không tìm thấy từ khóa, mặc định lấy 2 file đầu tiên
        ref_path = jpg_files[0]
        test_path = jpg_files[1]

    if not ref_path or not test_path:
        print(f"  Error: Could not identify image pair in {folder_path.name}")
        return

    print(f"  Ref: {ref_path.name}")
    print(f"  Test: {test_path.name}")

    out_dir = folder_path / "output"
    ensure_dir(out_dir)

    ref = imread_utf8(ref_path)
    test = imread_utf8(test_path)

    if ref is None or test is None:
        print(f"  Error: Could not read images in {folder_path.name}")
        return

    if ref.shape != test.shape:
        test = cv2.resize(test, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_LINEAR)

    ref_p = preprocess(ref)
    test_p = preprocess(test)

    # Trước align
    nonzero0, mean0 = save_diff("02_before", ref_p, test_p, out_dir)

    # Sau ECC
    try:
        aligned, warp, cc = align_ecc(ref_p, test_p, MOTION_TYPE)
        imwrite_utf8(out_dir / "03_ecc_aligned.jpg", aligned)

        nonzero1, mean1 = save_diff("04_after_ecc", ref_p, aligned, out_dir)
        
        with open(out_dir / "metrics.txt", "w", encoding="utf-8") as f:
            f.write(f"Ref: {ref_path.name}\n")
            f.write(f"Test: {test_path.name}\n\n")
            f.write(f"Before ECC: nonzero={nonzero0}, mean_diff={mean0:.6f}\n")
            f.write(f"After ECC : nonzero={nonzero1}, mean_diff={mean1:.6f}\n")
            f.write(f"ECC cc    : {cc:.8f}\n")
            f.write("Warp matrix:\n")
            f.write(str(warp))
        
        print(f"  Done! Results saved to: {out_dir.relative_to(BASE_DIR)}")

    except cv2.error as e:
        print(f"  Failed in {folder_path.name}: {e}")

def main():
    print("--- Starting batch processing ---")
    
    # Duyệt qua các thư mục con trong BASE_DIR
    subdirs = [d for d in BASE_DIR.iterdir() if d.is_dir()]
    
    processed_count = 0
    for subdir in subdirs:
        # Bỏ qua các thư mục output cũ hoặc thư mục hệ thống
        if subdir.name in ["output", "align_test_output", "__pycache__"]:
            continue
            
        process_folder(subdir)
        processed_count += 1

    if processed_count == 0:
        print("No subdirectories found to process.")
    else:
        print(f"\n--- Finished processing {processed_count} folders ---")

if __name__ == "__main__":
    main()