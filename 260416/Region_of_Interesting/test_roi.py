import cv2
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "leanbot.jpg")
OUT_DIR  = os.path.join(BASE_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(IMG_PATH)
print(f"Kích thước ảnh: {img.shape}")  # (height, width, channels)

# Chọn các tọa độ muốn ROI 
x_start, y_start, x_end, y_end = 540, 400, 780, 570

# ROI – tham chiếu (không copy)
roi = img[y_start:y_end, x_start:x_end]
print(f"ROI size: {roi.shape}")

# Cropping – bản sao độc lập
cropped = img[y_start:y_end, x_start:x_end].copy()

# Vẽ hình chữ nhật lên ảnh gốc để đánh dấu vùng ROI
img_with_rect = img.copy()
cv2.rectangle(img_with_rect, (x_start, y_start), (x_end, y_end), (0, 255, 0), 3)
cv2.putText(img_with_rect, "ROI - Leanbot", (x_start, y_start - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

cv2.imwrite(f"{OUT_DIR}/01_original_with_roi.jpg", img_with_rect)
cv2.imwrite(f"{OUT_DIR}/02_cropped_leanbot.jpg", cropped)

print(f"Đã lưu kết quả vào {OUT_DIR}")

cv2.imshow("Original + ROI", cv2.resize(img_with_rect, (800, 600)))
cv2.imshow("Cropped Leanbot", cropped)
cv2.waitKey(0)
cv2.destroyAllWindows()
