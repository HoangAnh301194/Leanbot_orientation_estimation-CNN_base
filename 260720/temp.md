- Chạy test confidence để kiểm tra ouput của model Yolo11n fp16 static 640 no NMS và model gốc fp32 Yolo11n.
- Ảnh test : 
![24class_test_images\1.jpg ](24class_test_images\1.jpg)
- Lệnh chạy test với model fp16 static 640 no NMS: 

```bash
python tools\check_confidence.py --input 24class_test_images\1.jpg --output 24class_test_images_out --model models\YOLO11n_versions\FP16_no_nms\best_640_openvino_model
```
- Ảnh debug kết quả 

![24class_test_images_out\debug_1.jpg](24class_test_images_out\debug_1.jpg)

- File csv : [24class_test_images_out\1_top200.csv](24class_test_images_out\1_top200.csv)
 
- **10 anchor tốt nhất trong csv :**

| Anchor | Vector Mag | Max Class Confidence | Angle Estimate |
|---|---|---|---|
| 1 | 0.66 | 0.29 (Leanbot_p15) | 12.11 |
| 2 | 0.56 | 0.27 (Leanbot_p15) | 11.34 |
| 3 | 0.59 | 0.27 (Leanbot_p165) | 175.12 |
| 4 | 0.48 | 0.26 (Leanbot_p165) | 166.59 |
| 5 | 0.45 | 0.25 (Leanbot_p180) | 167.05 |
| 6 | 0.31 | 0.21 (Leanbot_m120) | -140.22 |
| 7 | 0.38 | 0.18 (Leanbot_p165) | 155.49 |
| 8 | 0.32 | 0.17 (Leanbot_p15) | 13.46 |
| 9 | 0.23 | 0.12 (Leanbot_p15) | 18.68 |
| 10 | 0.20 | 0.07 (Leanbot_p180) | -163.76 |
