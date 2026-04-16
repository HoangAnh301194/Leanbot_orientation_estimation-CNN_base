import sys
import io
import time
import cv2
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).parent
MOTION_TYPE = cv2.MOTION_AFFINE
THRESH_VAL = 25

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)



def preprocess(gray: np.ndarray) -> np.ndarray:
    # Cân bằng tương phản cục bộ bằng CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Làm mượt ảnh
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    return gray

def save_diff(name: str, ref_gray: np.ndarray, test_gray: np.ndarray, out_dir: Path):
    diff = cv2.absdiff(ref_gray, test_gray)
    _, mask = cv2.threshold(diff, THRESH_VAL, 255, cv2.THRESH_BINARY)

    cv2.imwrite(str(out_dir / f"{name}_diff.jpg"), diff)
    cv2.imwrite(str(out_dir / f"{name}_mask.jpg"), mask)

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
    
    # Đường dẫn file nền bắt buộc
    ref_path = folder_path / "backGround.jpg"
    if not ref_path.exists():
        print(f"  Error: 'backGround.jpg' not found in {folder_path.name}")
        return

    # Đọc ảnh nền
    ref = cv2.imread(str(ref_path), cv2.IMREAD_GRAYSCALE)
    if ref is None:
        print(f"  Error: Could not read {ref_path.name}")
        return
        
    ref_p = preprocess(ref)
    
    # Tìm tất cả các file .jpg khác ngoại trừ backGround.jpg
    test_files = [f for f in folder_path.glob("*.jpg") if f.name != "backGround.jpg"]
    
    if not test_files:
        print("  No target images found to process.")
        return

    processed_in_folder = 0
    for test_path in test_files:
        print(f"  -> Alighning: {test_path.name}")
        
        # Thư mục output cho riêng ảnh này: {tên_ảnh}_output
        target_out_dir = folder_path / f"{test_path.stem}_output"
        ensure_dir(target_out_dir)
        
        test = cv2.imread(str(test_path), cv2.IMREAD_GRAYSCALE)
        if test is None:
            print(f"    Error: Could not read {test_path.name}")
            continue

        # Resize nếu kích thước khác nhau
        if ref.shape != test.shape:
            test = cv2.resize(test, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_LINEAR)

        test_p = preprocess(test)

        # Trước alignment
        nonzero0, mean0 = save_diff("02_before", ref_p, test_p, target_out_dir)

        # Thực hiện ECC Alignment và đo thời gian
        try:
            start_time = time.perf_counter()
            aligned, warp, cc = align_ecc(ref_p, test_p, MOTION_TYPE)
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000

            cv2.imwrite(str(target_out_dir / "03_ecc_aligned.jpg"), aligned)

            # Sau alignment
            nonzero1, mean1 = save_diff("04_after_ecc", ref_p, aligned, target_out_dir)
            
            # Ghi metrics
            with open(target_out_dir / "metrics.txt", "w", encoding="utf-8") as f:
                f.write(f"Ref: {ref_path.name}\n")
                f.write(f"Test: {test_path.name}\n\n")
                f.write(f"Before ECC: nonzero={nonzero0}, mean_diff={mean0:.6f}\n")
                f.write(f"After ECC : nonzero={nonzero1}, mean_diff={mean1:.6f}\n")
                f.write(f"ECC cc    : {cc:.8f}\n")
                f.write(f"Alignment Time: {elapsed_ms:.2f} ms\n")
                f.write("Warp matrix:\n")
                f.write(str(warp))
            
            processed_in_folder += 1
        except cv2.error as e:
            print(f"    Failed aligned {test_path.name}: {e}")

    print(f"  Done! Processed {processed_in_folder} images in {folder_path.name}")

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
