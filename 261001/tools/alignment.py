import time
import cv2
import numpy as np
from pathlib import Path
import argparse

class ImageAligner:
    """
    A tool for aligning images using OpenCV's ECC (Enhanced Correlation Coefficient) algorithm.
    Can be used as a library or via Command Line Interface.
    """
    def __init__(self, template_img=None, motion_type=cv2.MOTION_AFFINE):
        self.motion_type = motion_type
        self.template_gray = None
        self.template_preprocessed = None
        self.warp_matrix = None
        self.criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-6)

        if template_img is not None:
            self.set_template(template_img)

    def set_template(self, img):
        """Sets and preprocesses the reference template image."""
        start = time.perf_counter()
        if len(img.shape) == 3:
            self.template_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            self.template_gray = img.copy()
        
        self.template_preprocessed = self.preprocess(self.template_gray)
        
        # Reset warp matrix for new template
        if self.motion_type == cv2.MOTION_HOMOGRAPHY:
            self.warp_matrix = np.eye(3, 3, dtype=np.float32)
        else:
            self.warp_matrix = np.eye(2, 3, dtype=np.float32)
        
        end = time.perf_counter()
        print(f"set_template: {(end - start)*1000:.2f} ms")

    @staticmethod
    def preprocess(gray):
        """Standard preprocessing: CLAHE and Gaussian Blur."""
        start = time.perf_counter()
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        end = time.perf_counter()
        print(f"preprocess: {(end - start)*1000:.2f} ms") # Có thể bỏ comment nếu muốn log sâu
        return gray

    def align(self, target_img):
        """Aligns target_img to the stored template."""
        if self.template_preprocessed is None:
            raise ValueError("Template image not set. Call set_template() first.")

        if len(target_img.shape) == 3:
            target_gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        else:
            target_gray = target_img.copy()

        # Resize if needed
        if target_gray.shape != self.template_gray.shape:
            target_gray = cv2.resize(target_gray, (self.template_gray.shape[1], self.template_gray.shape[0]))

        target_p = self.preprocess(target_gray)

        try:
            start = time.perf_counter()
            (cc, warp) = cv2.findTransformECC(
                self.template_preprocessed,
                target_p,
                self.warp_matrix.copy(),
                self.motion_type,
                self.criteria
            )
            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000
            print(f"align (ECC calculation): {elapsed_ms:.2f} ms")
            
            # Apply warp
            h, w = self.template_gray.shape
            if self.motion_type == cv2.MOTION_HOMOGRAPHY:
                aligned = cv2.warpPerspective(target_gray, warp, (w, h), 
                                            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                            borderMode=cv2.BORDER_REPLICATE)
            else:
                aligned = cv2.warpAffine(target_gray, warp, (w, h), 
                                       flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                       borderMode=cv2.BORDER_REPLICATE)
            
            return {
                "aligned": aligned,
                "warp": warp,
                "cc": cc,
                "time_ms": (end - start) * 1000
            }
        except cv2.error as e:
            raise RuntimeError(f"ECC Alignment failed: {e}")

    @staticmethod
    def compute_diff(ref_gray, test_gray, threshold=25):
        """Computes absolute difference and binary mask."""
        start = time.perf_counter()
        diff = cv2.absdiff(ref_gray, test_gray)
        _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        
        nonzero = int(np.count_nonzero(mask))
        mean_val = float(diff.mean())
        end = time.perf_counter()
        print(f"compute_diff: {(end - start)*1000:.2f} ms")
        
        return diff, mask, nonzero, mean_val

def main():
    parser = argparse.ArgumentParser(description="Image Alignment Tool (ECC)")
    parser.add_argument("--template", help="Path to reference background image")
    parser.add_argument("--target", help="Path to image to align")
    parser.add_argument("--outdir", default="output", help="Output directory")
    parser.add_argument("--mode", choices=["single", "batch"], default="single")
    args = parser.parse_args()

    aligner = ImageAligner()

    if args.mode == "single":
        if not args.template or not args.target:
            print("[ERROR] Single mode requires both --template and --target")
            return
        
        # Load images
        ref = cv2.imread(args.template)
        tgt = cv2.imread(args.target)
        if ref is None or tgt is None:
            print("[ERROR] Could not read images")
            return

        aligner.set_template(ref)
        
        try:
            result = aligner.align(tgt)
            print(f"[INFO] Aligned in {result['time_ms']:.2f} ms with correlation {result['cc']:.4f}")
            
            # Save results
            out_path = Path(args.outdir)
            out_path.mkdir(parents=True, exist_ok=True)
            
            cv2.imwrite(str(out_path / "aligned.jpg"), result["aligned"])
            
            # Save metrics
            diff, mask, nz, mean = aligner.compute_diff(aligner.template_gray, result["aligned"])
            cv2.imwrite(str(out_path / "diff.jpg"), diff)
            cv2.imwrite(str(out_path / "mask.jpg"), mask)
            
            with open(out_path / "metrics.txt", "w") as f:
                f.write(f"Correlation: {result['cc']:.8f}\n")
                f.write(f"Non-zero pixels: {nz}\n")
                f.write(f"Mean Diff: {mean:.6f}\n")
                f.write(f"Warp Matrix:\n{result['warp']}\n")
                
            print(f"[INFO] Results saved to {args.outdir}")
            
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
