from ultralytics import YOLO
import shutil
import os

model_path = r'D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260720\models\YOLO11n_versions\best.pt'
output_dir = r'D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260720\models\YOLO11n_versions\FP16_no_nms'
os.makedirs(output_dir, exist_ok=True)

model = YOLO(model_path)

print('Exporting 640...')
path_640 = model.export(format='openvino', half=True, dynamic=False, imgsz=640, nms=False)
shutil.move(path_640, os.path.join(output_dir, 'best_640_openvino_model'))

print('Exporting 160...')
path_160 = model.export(format='openvino', half=True, dynamic=False, imgsz=160, nms=False)
shutil.move(path_160, os.path.join(output_dir, 'best_160_openvino_model'))

print('Done!')
