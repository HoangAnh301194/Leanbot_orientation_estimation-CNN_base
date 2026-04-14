import cv2
import numpy as np
from pathlib import Path


# =========================
# Cấu hình
# =========================
IMAGES_DIR = Path("images")    # Thư mục chứa các ảnh
BG_NAME = "background.jpg"     # Tên ảnh nền (nằm trong IMAGES_DIR)
OUT_DIR = Path("output")       # Thư mục xuất kết quả

THRESH_VAL = 30                # ngưỡng tách thay đổi, thử 20-50
MIN_AREA = 500                 # diện tích contour nhỏ hơn giá trị này sẽ bỏ
KERNEL_SIZE = 5                # kernel morphology

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def preprocess(gray: np.ndarray) -> np.ndarray:
    # làm mượt nhẹ để giảm nhiễu
    return cv2.GaussianBlur(gray, (5, 5), 0)


def extract_object(bg: np.ndarray, cur_path: Path, output_subfolder: Path):

    cur = cv2.imread(str(cur_path))
    if cur is None:
        print(f"Không đọc được ảnh: {cur_path}")
        return

    ensure_dir(output_subfolder)
    print(f"Dang xu ly: {cur_path.name} -> {output_subfolder}")

    # đưa về cùng kích thước
    if bg.shape[:2] != cur.shape[:2]:
        cur = cv2.resize(cur, (bg.shape[1], bg.shape[0]), interpolation=cv2.INTER_LINEAR)

    # chuyển grayscale
    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    cur_gray = cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY)

    # tiền xử lý
    bg_gray = preprocess(bg_gray)
    cur_gray = preprocess(cur_gray)

    # sai khác tuyệt đối
    diff = cv2.absdiff(bg_gray, cur_gray)

    # threshold để lấy vùng thay đổi
    _, mask = cv2.threshold(diff, THRESH_VAL, 255, cv2.THRESH_BINARY)

    # morphology để bỏ nhiễu và lấp lỗ
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_SIZE, KERNEL_SIZE))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # tìm contour
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    preview = cur.copy()
    changed_only = cv2.bitwise_and(cur, cur, mask=mask)

    best_box = None
    best_area = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if area > best_area:
            best_area = area
            best_box = (x, y, w, h)

    # lưu bbox lớn nhất riêng
    if best_box is not None:
        x, y, w, h = best_box
        best_crop = cur[y:y + h, x:x + w]
        best_mask_crop = mask[y:y + h, x:x + w]

        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(
            preview,
            f"x={x}, y={y}, w={w}, h={h}",
            (x, max(20, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

        cv2.imwrite(str(output_subfolder / "largest_changed_crop.jpg"), best_crop)
        cv2.imwrite(str(output_subfolder / "largest_changed_mask.jpg"), best_mask_crop)

    # lưu ảnh kết quả
    cv2.imwrite(str(output_subfolder / "01_diff.jpg"), diff)
    cv2.imwrite(str(output_subfolder / "02_mask.jpg"), mask)
    cv2.imwrite(str(output_subfolder / "03_changed_only.jpg"), changed_only)
    cv2.imwrite(str(output_subfolder / "04_preview_bbox.jpg"), preview)


def main():
    # Kiểm tra thư mục images
    if not IMAGES_DIR.exists():
        print(f"Error: Thư mục {IMAGES_DIR} không tồn tại.")
        return

    # Tìm background
    bg_path = IMAGES_DIR / BG_NAME
    if not bg_path.exists():
        # Thử tìm trong thư mục hiện tại nếu không thấy trong images
        bg_path = Path(BG_NAME)
        if not bg_path.exists():
            print(f"Error: Không tìm thấy file background: {BG_NAME}")
            return

    bg = cv2.imread(str(bg_path))
    if bg is None:
        print(f"Error: Không thể đọc ảnh nền: {bg_path}")
        return

    print(f"--- Bat dau xu ly ---")
    print(f"Background: {bg_path}")
    
    # Lấy danh sách ảnh (loại trừ background)
    extensions = ("*.jpg", "*.jpeg", "*.png")
    image_paths = []
    for ext in extensions:
        image_paths.extend(IMAGES_DIR.glob(ext))
    
    # Loại bỏ file background khỏi danh sách cần xử lý
    image_paths = [p for p in image_paths if p.name != bg_path.name]
    
    if not image_paths:
        print("Khong tim thay anh de xu ly trong thu muc images.")
        return

    print(f"Tim thay {len(image_paths)} anh de xu ly.")

    for img_path in image_paths:
        # Tên thư mục con là tên ảnh không bao gồm phần mở rộng
        folder_name = img_path.stem
        output_subfolder = OUT_DIR / folder_name
        
        extract_object(bg, img_path, output_subfolder)

    print(f"\n--- Hoan thanh! ---")
    print(f"Ket qua duoc luu tai: {OUT_DIR}")


if __name__ == "__main__":
    main()
