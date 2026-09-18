import cv2
import numpy as np
from pathlib import Path


def get_screen_size():
    """
    Lấy kích thước màn hình để đặt cửa sổ OpenCV không bị trôi khỏi vùng hiển thị.
    """
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.destroy()
        return screen_w, screen_h
    except Exception:
        return None, None


def compute_hsv_diff(
    img1: np.ndarray,
    img2: np.ndarray,
    w_h: float = 2.0,
    w_s: float = 1.0,
    w_v: float = 1.0,
    threshold: int = 40,
    min_saturation: int = 20,
    blur_ksize: int = 0,
    use_clahe: bool = False,
):
    """
    So sánh 2 ảnh BGR theo độ khác nhau HSV từng pixel.
    """
    if img1 is None or img2 is None:
        raise ValueError("img1/img2 must not be None")

    # Làm mượt nhẹ nếu cần
    if blur_ksize and blur_ksize > 1:
        if blur_ksize % 2 == 0:
            blur_ksize += 1
        img1 = cv2.GaussianBlur(img1, (blur_ksize, blur_ksize), 0)
        img2 = cv2.GaussianBlur(img2, (blur_ksize, blur_ksize), 0)

    # BGR -> HSV
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

    h1, s1, v1 = cv2.split(hsv1)
    h2, s2, v2 = cv2.split(hsv2)

    if use_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        v1 = clahe.apply(v1)
        v2 = clahe.apply(v2)

    dS = cv2.absdiff(s1, s2).astype(np.float32)
    dV = cv2.absdiff(v1, v2).astype(np.float32)

    h1_i = h1.astype(np.int16)
    h2_i = h2.astype(np.int16)
    dH_raw = np.abs(h1_i - h2_i)
    dH_circular = np.minimum(dH_raw, 180 - dH_raw).astype(np.float32)
    dH = dH_circular * (255.0 / 90.0)

    low_sat_mask = (s1 < min_saturation) & (s2 < min_saturation)
    dH[low_sat_mask] = 0.0

    weight_sum = w_h + w_s + w_v
    if weight_sum <= 0: weight_sum = 1.0

    score = (w_h * dH + w_s * dS + w_v * dV) / weight_sum
    score = np.clip(score, 0, 255).astype(np.uint8)

    _, mask = cv2.threshold(score, threshold, 255, cv2.THRESH_BINARY)

    return {
        "score": score,
        "mask": mask,
        "dH": np.clip(dH, 0, 255).astype(np.uint8),
        "dS": np.clip(dS, 0, 255).astype(np.uint8),
        "dV": np.clip(dV, 0, 255).astype(np.uint8),
        "nonzero": int(np.count_nonzero(mask)),
    }

def compute_gray_hue_diff(img1, img2, w_gray=1.0, w_hue=0.5, threshold=40, min_saturation=20, blur_ksize=5, use_clahe=True):
    """
    Kết hợp Grayscale difference và Hue difference.
    """
    if blur_ksize and blur_ksize > 1:
        img1 = cv2.GaussianBlur(img1, (blur_ksize, blur_ksize), 0)
        img2 = cv2.GaussianBlur(img2, (blur_ksize, blur_ksize), 0)

    # Gray diff
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    if use_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray1 = clahe.apply(gray1)
        gray2 = clahe.apply(gray2)
        
    dGray = cv2.absdiff(gray1, gray2).astype(np.float32)

    # HSV for Hue
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
    h1, s1, _ = cv2.split(hsv1)
    h2, s2, _ = cv2.split(hsv2)

    # Hue circular diff
    h1 = h1.astype(np.int16)
    h2 = h2.astype(np.int16)
    dH_raw = np.abs(h1 - h2)
    dH = np.minimum(dH_raw, 180 - dH_raw).astype(np.float32)
    dH = dH * (255.0 / 90.0)

    # Bỏ Hue ở vùng saturation thấp
    low_sat = (s1 < min_saturation) & (s2 < min_saturation)
    dH[low_sat] = 0

    # Gộp
    weight_total = w_gray + w_hue
    if weight_total <= 0: weight_total = 1.0
    
    score = np.maximum(w_gray * dGray, w_hue * dH)
    score = np.clip(score, 0, 255).astype(np.uint8)

    _, mask = cv2.threshold(score, threshold, 255, cv2.THRESH_BINARY)

    return {
        "score": score,
        "mask": mask,
        "dGray": dGray.astype(np.uint8),
        "dH": dH.astype(np.uint8),
        "nonzero": int(np.count_nonzero(mask))
    }

def refine_mask(mask):
    """
    Đồng bộ quy trình hậu xử lý từ auto_label.py:
    Morphology Open -> Dilate -> Morphology Close -> Fill Holes -> Dilate
    """
    if mask is None: return None
    
    kernel_small = np.ones((3, 3), np.uint8)
    kernel_large = np.ones((25, 25), np.uint8)
    
    # Bước A: MORPH_OPEN xóa nhiễu nhỏ
    m = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small)
    
    # Bước B: DILATE nở vật thể
    m = cv2.dilate(m, np.ones((5, 5), np.uint8), iterations=1)
    
    # Bước C: MORPH_CLOSE lấp hố và hàn gắn
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel_large)
    
    # Bước D: Điền đầy (Fill holes)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        cv2.drawContours(m, [c], -1, 255, thickness=-1)
        
    # Bước E: Dilation cuối
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=1)
    
    return m


def main():
    base_dir = Path(__file__).resolve().parent
    img1_raw = cv2.imread(str(base_dir / "background.jpg"))
    img2_raw = cv2.imread(str(base_dir / "leanbot.jpg"))

    if img1_raw is None or img2_raw is None:
        print(f"[Error] Could not find background.jpg or leanbot.jpg in: {base_dir}")
        return

    # Window names
    CTRL_WIN = "Controls (raw x0.2)"
    RES_WIN = "Results (HSV | Hybrid | Gray)"
    COMP_WIN = "Components Detail"
    screen_w, screen_h = get_screen_size()

    cv2.namedWindow(CTRL_WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(CTRL_WIN, 400, 600)
    cv2.namedWindow(RES_WIN, cv2.WINDOW_NORMAL)
    cv2.namedWindow(COMP_WIN, cv2.WINDOW_NORMAL)

    def nothing(x): pass

    # Weight trackbars: raw 0..25 <=> actual 0.0..5.0 with step 0.2
    cv2.createTrackbar("Base_WH x0.2", CTRL_WIN, 25, 25, nothing)
    cv2.createTrackbar("Base_WS x0.2", CTRL_WIN, 10, 25, nothing)
    cv2.createTrackbar("Base_WV x0.2", CTRL_WIN, 5, 25, nothing)
    
    # Hybrid Trackbars
    cv2.createTrackbar("Mix_WGray x0.2", CTRL_WIN, 15, 25, nothing)
    cv2.createTrackbar("Mix_WHue x0.2", CTRL_WIN, 25, 25, nothing)
    
    # Shared Trackbars
    cv2.createTrackbar("Threshold", CTRL_WIN, 45, 255, nothing)
    cv2.createTrackbar("MinSat", CTRL_WIN, 40, 255, nothing)
    cv2.createTrackbar("Blur", CTRL_WIN, 2, 15, nothing)
    cv2.createTrackbar("CLAHE", CTRL_WIN, 1, 1, nothing)
    cv2.createTrackbar("Refine", CTRL_WIN, 1, 1, nothing) # Mặc định bật Refine như auto_label

    print("\n[INFO] Interactive multi-algorithm tool started.")
    print(f"       Running file: {Path(__file__).resolve()}")
    print("       Press 's' to save/print parameters. 'q' to exit.")

    scale = 0.15
    h, w = img1_raw.shape[:2]
    sw, sh = int(w * scale), int(h * scale)
    res_w, res_h = sw * 2, sh * 3
    comp_w, comp_h = sw * 3, sh
    def resize(img): return cv2.resize(img, (sw, sh))
    def to_bgr(gray): return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    win_res_w, win_res_h = res_w, res_h
    win_comp_w, win_comp_h = comp_w, comp_h
    if screen_w and screen_h:
        win_res_w = min(res_w, max(480, screen_w - 460))
        win_res_h = min(res_h, max(320, screen_h - 140))
        win_comp_w = min(comp_w, max(480, screen_w - 80))
        win_comp_h = min(comp_h, max(220, screen_h - 140))

    cv2.resizeWindow(RES_WIN, win_res_w, win_res_h)
    cv2.resizeWindow(COMP_WIN, win_comp_w, win_comp_h)

    cv2.moveWindow(CTRL_WIN, 0, 0)
    cv2.moveWindow(RES_WIN, 410, 0)

    comp_x, comp_y = 410, res_h + 120
    if screen_h and comp_y + win_comp_h > screen_h:
        comp_x = 410 + win_res_w + 20
        comp_y = 0
    if screen_w and comp_x + win_comp_w > screen_w:
        comp_x = max(0, screen_w - win_comp_w - 20)
    if screen_h and comp_y + win_comp_h > screen_h:
        comp_y = max(0, screen_h - win_comp_h - 60)

    cv2.moveWindow(COMP_WIN, comp_x, comp_y)

    while True:
        # Get Trackbars
        wh_base = cv2.getTrackbarPos("Base_WH x0.2", CTRL_WIN) / 5.0
        ws_base = cv2.getTrackbarPos("Base_WS x0.2", CTRL_WIN) / 5.0
        wv_base = cv2.getTrackbarPos("Base_WV x0.2", CTRL_WIN) / 5.0
        
        wg_mix = cv2.getTrackbarPos("Mix_WGray x0.2", CTRL_WIN) / 5.0
        wh_mix = cv2.getTrackbarPos("Mix_WHue x0.2", CTRL_WIN) / 5.0
        
        th = cv2.getTrackbarPos("Threshold", CTRL_WIN)
        ms = cv2.getTrackbarPos("MinSat", CTRL_WIN)
        bl = cv2.getTrackbarPos("Blur", CTRL_WIN) * 2 + 1
        cl = cv2.getTrackbarPos("CLAHE", CTRL_WIN) == 1
        rf = cv2.getTrackbarPos("Refine", CTRL_WIN) == 1

        # 1. HSV Mode
        res_hsv = compute_hsv_diff(img1_raw, img2_raw, w_h=wh_base, w_s=ws_base, w_v=wv_base, 
                                   threshold=th, min_saturation=ms, blur_ksize=bl, use_clahe=cl)

        # 2. Hybrid Mode (Gray + Hue)
        res_hybrid = compute_gray_hue_diff(img1_raw, img2_raw, w_gray=wg_mix, w_hue=wh_mix, 
                                          threshold=th, min_saturation=ms, blur_ksize=bl, use_clahe=cl)

        # 3. Baseline Gray Only
        gray1 = cv2.cvtColor(img1_raw, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2_raw, cv2.COLOR_BGR2GRAY)
        gray1 = cv2.GaussianBlur(gray1, (bl, bl), 0)
        gray2 = cv2.GaussianBlur(gray2, (bl, bl), 0)
        if cl:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray1, gray2 = clahe.apply(gray1), clahe.apply(gray2)
        g_diff = cv2.absdiff(gray1, gray2)
        _, g_mask = cv2.threshold(g_diff, th, 255, cv2.THRESH_BINARY)

        # Visualization Stacks
        mask_hsv = res_hsv["mask"]
        mask_hybrid = res_hybrid["mask"]
        mask_gray = g_mask
        
        if rf:
            mask_hsv = refine_mask(mask_hsv)
            mask_hybrid = refine_mask(mask_hybrid)
            mask_gray = refine_mask(mask_gray)

        row_hsv = np.hstack([to_bgr(resize(res_hsv["score"])), to_bgr(resize(mask_hsv))])
        row_hybrid = np.hstack([to_bgr(resize(res_hybrid["score"])), to_bgr(resize(mask_hybrid))])
        row_gray = np.hstack([to_bgr(resize(g_diff)), to_bgr(resize(mask_gray))])

        cv2.putText(row_hsv, f"1. HSV Only (Score | Mask)", (10, 30), 1, 1.5, (0, 255, 0), 2)
        cv2.putText(row_hybrid, f"2. Hybrid Hue+Gray (Score | Mask)", (10, 30), 1, 1.5, (255, 255, 0), 2)
        cv2.putText(row_gray, f"3. Gray Baseline (Diff | Mask)", (10, 30), 1, 1.5, (0, 0, 255), 2)

        status_bar = np.zeros((70, row_hsv.shape[1], 3), dtype=np.uint8)
        cv2.putText(status_bar, f"HSV: WH={wh_base:.1f} WS={ws_base:.1f} WV={wv_base:.1f} | Hybrid: WGray={wg_mix:.1f} WHue={wh_mix:.1f}", (10, 28), 1, 1.0, (255, 255, 255), 2)
        cv2.putText(status_bar, "Trackbar raw index 0..25 => actual weight 0.0..5.0, step 0.2", (10, 58), 1, 0.9, (0, 220, 255), 2)

        res_stack = np.vstack([status_bar, row_hsv, row_hybrid, row_gray])
        cv2.imshow(RES_WIN, res_stack)

        # Components for HSV
        comp_stack = np.hstack([to_bgr(resize(res_hsv["dH"])), to_bgr(resize(res_hsv["dS"])), to_bgr(resize(res_hsv["dV"]))])
        cv2.putText(comp_stack, "Detail: dH | dS | dV", (10, 30), 1, 1.5, (255, 255, 255), 2)
        cv2.imshow(COMP_WIN, comp_stack)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27: break
        elif key == ord('s'):
            print("\n--- PARAMETERS SAVED ---")
            print(f"[HSV] w_h={wh_base}, w_s={ws_base}, w_v={wv_base}")
            print(f"[Mix] w_gray={wg_mix}, w_hue={wh_mix}")
            print(f"[Shared] Threshold={th}, MinSat={ms}, Blur={bl}, CLAHE={cl}")
            print(f"Nonzero: HSV={res_hsv['nonzero']}, Mix={res_hybrid['nonzero']}, Gray={int(np.count_nonzero(g_mask))}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
