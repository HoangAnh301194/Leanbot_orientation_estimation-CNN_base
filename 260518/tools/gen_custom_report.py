import os
import glob
import re

CLASS_ORDER = ["Leanbot_0", "Leanbot_p45", "Leanbot_m45", "Leanbot_p90", "Leanbot_m90", "Leanbot_p135", "Leanbot_m135", "Leanbot_180"]
CLASS_HEADERS = ["0", "p45", "m45", "p90", "m90", "p135", "m135", "180"]
CLASS_ANGLES = {
    "Leanbot_0": 0, "Leanbot_p45": 45, "Leanbot_m45": -45,
    "Leanbot_p90": 90, "Leanbot_m90": -90, "Leanbot_p135": 135,
    "Leanbot_m135": -135, "Leanbot_180": 180
}

def get_calculated_angle(obj):
    scores = obj["class_scores"]
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_scores) < 2: return "N/A"
    
    cls1, c1 = sorted_scores[0]
    cls2, c2 = sorted_scores[1]
    
    if c1 + c2 == 0: return "0.0°"
    
    a1, a2 = CLASS_ANGLES[cls1], CLASS_ANGLES[cls2]
    
    # Xử lý trường hợp đối xứng ở +-180
    if abs(a1 - a2) > 180:
        if a1 > a2: a1 -= 360
        else: a2 -= 360
        
    calc = (c1 * a1 + c2 * a2) / (c1 + c2)
    if calc <= -180: calc += 360
    elif calc > 180: calc -= 360
    
    return f"{calc:.1f}°"


def parse_debug_file(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    if len(lines) < 3:
        return None

    img_name = lines[0].replace("Image:", "").strip()
    no_detection = "Không phát hiện object nào." in content

    objects = []
    current_obj = None

    for line in lines:
        m = re.match(r"Object\s+(\d+)\s+\|\s+Best:\s+(.+?)\s+\((?:Conf:\s*)?([0-9.]+)\)", line)
        if m:
            if current_obj:
                objects.append(current_obj)
            current_obj = {
                "obj_id": int(m.group(1)),
                "best_cls": m.group(2),
                "best_conf": float(m.group(3)),
                "bbox": None,
                "class_scores": {},
            }
            continue

        m = re.match(r"Bbox \(xyxy\):\s*\((.+?)\)", line)
        if m and current_obj:
            coords = tuple(int(float(x.strip())) for x in m.group(1).split(","))
            current_obj["bbox"] = coords
            continue

        m = re.match(r"\s+(?:\d+\s*-\s*)?(.+?):\s+([0-9.]+)", line)
        if m and current_obj:
            name = m.group(1).strip()
            score = float(m.group(2))
            current_obj["class_scores"][name] = score
            continue

    if current_obj:
        objects.append(current_obj)

    return {
        "img_name": img_name,
        "no_detection": no_detection,
        "objects": objects,
    }

def format_score(score, is_best):
    if is_best:
        return f"**{score:.4f}**"
    return f"{score:.4f}"

def gen_markdown_section(pf):
    img_name = pf["img_name"]
    stem = img_name.replace(".jpg", "")
    objects = pf["objects"]
    
    # Sắp xếp theo best_conf giảm dần và lấy tối đa 9 object
    objects = sorted(objects, key=lambda x: x["best_conf"], reverse=True)[:9]
    num_obj = len(objects)

    lines = []
    lines.append(f"##### `{stem}` ({num_obj} vị trí Leanbot)")
    lines.append(f"| Ảnh BBox | Ảnh Confidence |")
    lines.append(f"| :---: | :---: |")
    lines.append(f"| ![{stem} bbox](./infer_output/{stem}_bbox.jpg) | ![{stem} conf](./infer_output/{stem}_conf.jpg) |")
    lines.append("")

    if pf["no_detection"] or num_obj == 0:
        lines.append("> **Không phát hiện object nào.**\n")
        return "\n".join(lines)

    # Table Header
    header_cols = ["Vị trí", "BBox (x1, y1, x2, y2)"] + CLASS_HEADERS + ["Best Class", "Góc ước lượng"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")

    for i, obj in enumerate(objects):
        bbox = obj["bbox"]
        if bbox:
            x1, y1, x2, y2 = bbox
            bbox_str = f"({x1}, {y1}, {x2}, {y2})"
        else:
            bbox_str = "(N/A)"

        best_cls = obj["best_cls"]
        best_conf = obj["best_conf"]

        row = [f"#{i+1}", bbox_str]

        for cls_name in CLASS_ORDER:
            score = obj["class_scores"].get(cls_name, 0.0)
            is_best = (cls_name == best_cls)
            row.append(format_score(score, is_best))

        row.append(f"`{best_cls}` ({best_conf:.4f})")
        row.append(get_calculated_angle(obj))
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")

    lines.append("")

    return "\n".join(lines)

def main():
    target_dir = r"d:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260518\infer_output"
    txt_files = sorted(glob.glob(os.path.join(target_dir, "*_debug.txt")))

    STANDARD_ANGLES = ["angle_0", "angle_p45", "angle_m45", "angle_p90", "angle_m90", "angle_p135", "angle_m135", "angle_p180", "angle_m180"]

    report_lines = []
    for txt in txt_files:
        pf = parse_debug_file(txt)
        if pf is None:
            continue
            
        stem = pf["img_name"].replace(".jpg", "")
        angle_name = stem.rsplit("_", 1)[0]
        if angle_name in STANDARD_ANGLES:
            continue
            
        report_lines.append(gen_markdown_section(pf))

    out_path = r"d:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260518\full_report.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    main()
