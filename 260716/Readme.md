# Báo cáo công việc ngày 14/07/2026

## A. Công việc đã làm
- Bật param remove NMS khi export model OpenVINO và đánh giá các thôgn số so với none NMS 
- Chỉnh sửa code test ROI tracking tính góc từ tổng vector các anchors overlap. 

### 1. Bật rapam remove NMS khi export model OpenVINO 
- Code sử dụng : [tools\export_openvino_fp16.py](tools\export_openvino_fp16.py)

```python
from ultralytics import YOLO

pt_model_path = os.path.join(quantized_dir, 'Soft_Angular_BCE_yolo11n.pt')
model_pt = YOLO(pt_model_path)
openvino_fp16_path = model_pt.export(
  format="openvino", 
  imgsz=640, 
  half=True, 
  nms=True)
    
```
- Lệnh chạy 
```bash 

```