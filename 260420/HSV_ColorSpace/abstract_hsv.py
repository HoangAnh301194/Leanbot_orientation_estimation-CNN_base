import cv2
import numpy as np


def compute_hsv_diff(
    img1: np.ndarray,
    img2: np.ndarray,
    w_h: float = 2.0,
    w_s: float = 1.0,
    w_v: float = 1.0,
    threshold: int = 40,
    min_saturation: int = 20,
    blur_ksize: int = 0,
):
    """
    So sánh 2 ảnh BGR theo độ khác nhau HSV từng pixel.

    Parameters
    ----------
    img1, img2 : np.ndarray
        2 ảnh đầu vào dạng BGR (OpenCV), cùng kích thước.
    w_h, w_s, w_v : float
        Trọng số cho Hue, Saturation, Value.
    threshold : int
        Ngưỡng để tạo mask nhị phân cuối cùng, trong khoảng 0..255.
    min_saturation : int
        Nếu S của cả 2 ảnh tại một pixel đều nhỏ hơn ngưỡng này,
        ta xem H ít đáng tin và cho đóng góp của dH = 0 tại pixel đó.
    blur_ksize : int
        Nếu > 0 và là số lẻ, áp GaussianBlur trước khi đổi HSV.
        Hữu ích khi ảnh hơi nhiễu.

    Returns
    -------
    result : dict
        {
            "score": bản đồ độ khác nhau HSV (uint8, 0..255),
            "mask": mask nhị phân sau threshold,
            "dH": ảnh độ khác nhau Hue đã scale về 0..255,
            "dS": ảnh độ khác nhau Saturation,
            "dV": ảnh độ khác nhau Value,
            "nonzero": số pixel trắng trong mask,
            "mean_score": giá trị trung bình của score
        }
    """
    if img1 is None or img2 is None:
        raise ValueError("img1/img2 must not be None")

    if img1.shape != img2.shape:
        raise ValueError(
            f"Input images must have the same shape, got {img1.shape} vs {img2.shape}"
        )

    if img1.ndim != 3 or img1.shape[2] != 3:
        raise ValueError("Input images must be BGR color images with shape (H, W, 3)")

    # Làm mượt nhẹ nếu cần
    if blur_ksize and blur_ksize > 1:
        if blur_ksize % 2 == 0:
            raise ValueError("blur_ksize must be odd")
        img1 = cv2.GaussianBlur(img1, (blur_ksize, blur_ksize), 0)
        img2 = cv2.GaussianBlur(img2, (blur_ksize, blur_ksize), 0)

    # BGR -> HSV
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

    h1, s1, v1 = cv2.split(hsv1)
    h2, s2, v2 = cv2.split(hsv2)

    # dS, dV: khác biệt tuyệt đối thông thường
    dS = cv2.absdiff(s1, s2).astype(np.float32)
    dV = cv2.absdiff(v1, v2).astype(np.float32)

    # dH: khác biệt Hue theo khoảng cách vòng tròn
    # OpenCV HSV 8-bit dùng H trong [0, 179]
    h1_i = h1.astype(np.int16)
    h2_i = h2.astype(np.int16)

    dH_raw = np.abs(h1_i - h2_i)
    dH_circular = np.minimum(dH_raw, 180 - dH_raw).astype(np.float32)

    # Scale dH từ [0, 90] -> [0, 255] để cùng thang với dS, dV
    dH = dH_circular * (255.0 / 90.0)

    # Nếu cả hai pixel đều gần xám (S thấp), bỏ đóng góp Hue
    # vì Hue khi đó ít đáng tin về mặt thực tiễn
    low_sat_mask = (s1 < min_saturation) & (s2 < min_saturation)
    dH[low_sat_mask] = 0.0

    # Gộp thành một bản đồ sai khác duy nhất
    weight_sum = w_h + w_s + w_v
    if weight_sum <= 0:
        raise ValueError("w_h + w_s + w_v must be > 0")

    score = (w_h * dH + w_s * dS + w_v * dV) / weight_sum
    score = np.clip(score, 0, 255).astype(np.uint8)

    # Threshold thành mask nhị phân
    _, mask = cv2.threshold(score, threshold, 255, cv2.THRESH_BINARY)

    nonzero = int(np.count_nonzero(mask))
    mean_score = float(score.mean())

    return {
        "score": score,
        "mask": mask,
        "dH": np.clip(dH, 0, 255).astype(np.uint8),
        "dS": np.clip(dS, 0, 255).astype(np.uint8),
        "dV": np.clip(dV, 0, 255).astype(np.uint8),
        "nonzero": nonzero,
        "mean_score": mean_score,
    }

def main():
    img1 = cv2.imread("background.jpg")
    img2 = cv2.imread("leanbot.jpg")

    if img1 is None or img2 is None:
        print("[Error] Could not find background.jpg or leanbot.jpg in the current directory.")
        return

    result = compute_hsv_diff(
        img1,
        img2,
        w_h=5.0,
        w_s=2.0,
        w_v=1.0,
        threshold=45,
        min_saturation=40,
        blur_ksize=5,
    )

    # Tính toán Grayscale Diff tiêu chuẩn để so sánh
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    # Áp dụng cùng mức blur để so sánh công bằng
    gray1 = cv2.GaussianBlur(gray1, (5, 5), 0)
    gray2 = cv2.GaussianBlur(gray2, (5, 5), 0)
    
    gray_diff = cv2.absdiff(gray1, gray2)
    _, gray_mask = cv2.threshold(gray_diff, 45, 255, cv2.THRESH_BINARY)

    # Resize và cố định vị trí để không tràn màn hình (nhỏ đi 6 lần)
    scale = 0.166
    def show_small(name, img, x, y):
        h, w = img.shape[:2]
        small = cv2.resize(img, (int(w * scale), int(h * scale)))
        cv2.imshow(name, small)
        cv2.moveWindow(name, x, y)

    # Tính toán kích thước ảnh mẫu
    h, w = img1.shape[:2]
    sw = int(w * scale)
    sh = int(h * scale)
    gap = 10 
    title_bar = 35

    # Hàng 1: Kết quả tổng hợp HSV
    show_small("HSV score", result["score"], 50, 50)
    show_small("HSV mask", result["mask"], 50 + sw + gap, 50)
    show_small("dH (Scaled Hue)", result["dH"], 50 + (sw + gap) * 2, 50)
    
    # Hàng 2: Chi tiết thành phần HSV
    show_small("dS (Saturation)", result["dS"], 50, 50 + sh + gap + title_bar)
    show_small("dV (Value)", result["dV"], 50 + sw + gap, 50 + sh + gap + title_bar)

    # Hàng 3: So sánh với Grayscale truyền thống
    show_small("GRAY diff", gray_diff, 50, 50 + (sh + gap + title_bar) * 2)
    show_small("GRAY mask", gray_mask, 50 + sw + gap, 50 + (sh + gap + title_bar) * 2)
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print(f"{'Method':<15} | {'Nonzero Pixels':<15} | {'Mean Score':<10}")
    print("-" * 45)
    print(f"{'HSV':<15} | {result['nonzero']:<15} | {result['mean_score']:.2f}")
    print(f"{'Grayscale':<15} | {int(np.count_nonzero(gray_mask)):<15} | {float(gray_diff.mean()):.2f}")

if __name__ == "__main__":
    main()