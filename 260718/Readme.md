# Báo cáo công việc ngày 17/07/2026

## A. Công việc đã làm 
- Chạy model debug confidence với ảnh test 

### 1. Chạy Model debug 
- Ảnh test : [24class_test_images/000021.jpg](24class_test_images/000021.jpg)
- Code sử dụng : [tools/check_confidence.py](tools/check_confidence.py)
- Lệnh chạy : 
```bash 
python tools/check_confidence.py --input 24class_test_images --output output_confidence --model models/best.pt 

```

- File csv kết quả : [output_confidence/000021_top200.csv](output_confidence/000021_top200.csv)
- Ảnh debug : [output_confidence/debug_000021.jpg](output_confidence/debug_000021.jpg)

> Kết quả ảnh cho thấy Model sau khi train vẫn hoạt động tốt . 

### 2. Export model sang định dạng OpenVINO FP16 quantization : 

- Code sử dụng : [tools/export_openvino_fp16.py](tools/export_openvino_fp16.py)
- Lệnh chạy : 
```bash 
python tools/export_openvino_fp16.py --model models/best.pt --no-nms
```
- Check debug với ảnh test :
```bash
python tools/check_confidence.py --input 24class_test_images --output output_confidence_openvino --model models/best_fp16_no_nms_imgsz640_openvino_model

```

- Log csv kết quả : [output_confidence_openvino/000021_top200.csv](output_confidence_openvino/000021_top200.csv)

- Ảnh debug :

 [output_confidence_openvino/debug_000021.jpg](output_confidence_openvino/debug_000021.jpg)

> Kết quả cho thấy model sau export vẫn hoạt động bình thường, confidence vẫn cao. Confidence gần như không thay đổi so với model gốc.

### 3. Thử test lại với model được export hôm qua (16/7/2026)
- Code sử dụng : [tools/check_confidence.py](tools/check_confidence.py) 

- Models chạy thử: [models/YOLO11n_versions/FP16_NO_NMS/static_640_openvino_model](models/YOLO11n_versions/FP16_NO_NMS/static_640_openvino_model)

- Lệnh chạy :
```bash
python tools/check_confidence.py --input 24class_test_images --output output_confidence_openvino_old_model --model models/YOLO11n_versions/FP16_NO_NMS/static_640_openvino_model --imgsz 640
```

- Log csv kết quả : [output_confidence_openvino_old_model/000021_top200.csv](output_confidence_openvino_old_model/000021_top200.csv)
- Ảnh debug : [output_confidence_openvino_old_model/debug_000021.jpg](output_confidence_openvino_old_model/debug_000021.jpg)

> Model cũ đã export hôm qua (17/7) vẫn hoạt động đúng . 

- Test thử model export dạng **static 160x160**: [models\YOLO11n_versions\FP16_NO_NMS\static_160_openvino_model](models\YOLO11n_versions\FP16_NO_NMS\static_160_openvino_model)

- Ảnh test : 

![24class_test_images/roi_crop_test.png](24class_test_images/roi_crop_test.png)

- Lệnh chạy:
```bash
python tools/check_confidence.py --input D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260718\24class_test_images\roi_crop_test.png --output output_confidence_roi_crop_160 --model models/YOLO11n_versions/FP16_NO_NMS/static_160_openvino_model --imgsz 160
```
- Log csv kết quả: [output_confidence_roi_crop_160/000021_top200.csv](output_confidence_roi_crop_160/000021_top200.csv)

- Ảnh debug: [output_confidence_roi_crop_160/debug_roi_crop_test.png](output_confidence_roi_crop_160/debug_roi_crop_test.png)

> Khi đưa ảnh Crop vuông vào test model thì vẫn thấy hoạt động được 
> Vấn đề là do quá trình roi tracking bị lỗi nên khi chạy Inference ROI tracking không detect được Leanbot để tracking theo ( lost tracking và ko detect lại được) 
> Em nghĩ có thể lỗi ở các bước resize ảnh có sai sót ạ .

## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
- Em xin phép nhận đề xuất tiếp theo từ Thầy ạ . 
- Em có cần báo cáo lại toàn bộ các bước tiền xử lí ảnh trước khi đưa vào 2 model **static 640x640** và **static 160x160** không ạ ? 