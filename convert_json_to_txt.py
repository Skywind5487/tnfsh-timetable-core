import os
import json

def convert_jsons_to_txt(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    class_txt = os.path.join(dst_dir, 'class.txt')
    teacher_txt = os.path.join(dst_dir, 'teacher.txt')
    with open(class_txt, 'w', encoding='utf-8') as f_class, open(teacher_txt, 'w', encoding='utf-8') as f_teacher:
        for fname in os.listdir(src_dir):
            if fname.endswith('.json'):
                src_path = os.path.join(src_dir, fname)
                with open(src_path, 'r', encoding='utf-8') as fsrc:
                    try:
                        data = json.load(fsrc)
                        role = data.get('data', {}).get('role', None)
                        if role == 'class':
                            f_class.write(json.dumps(data, ensure_ascii=False) + '\n')
                        elif role == 'teacher':
                            f_teacher.write(json.dumps(data, ensure_ascii=False) + '\n')
                    except Exception as e:
                        print(f"Error reading {fname}: {e}")
    print('分類轉換完成！')

def json_file_to_minified_str(json_path):
    """
    讀入 json 檔案，回傳無縮排的單行字串
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return json.dumps(data, ensure_ascii=False)

def json_file_to_minified_file(json_path):
    """
    讀入 json 檔案，並寫入無縮排的單行字串到同名檔案
    """
    minified_str = json_file_to_minified_str(json_path)
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(minified_str)
    print(f"已將 {json_path} 轉換為單行格式")

if __name__ == '__main__':
    INDEX_SRC_DIR = os.path.join(os.path.dirname(__file__), 'tnfsh_timetable_core', 'index', 'cache')
    TIMETABLE_SRC_DIR = os.path.join(os.path.dirname(__file__), 'tnfsh_timetable_core', 'timetable', 'cache')
    DST_DIR = os.path.join(os.path.dirname(__file__), 'to_txt', 'cache')
    convert_jsons_to_txt(TIMETABLE_SRC_DIR, DST_DIR)
    # 範例：
    # print(json_file_to_minified_str(os.path.join(SRC_DIR, 'prebuilt_102.json')))
    json_file_to_minified_file(os.path.join(DST_DIR, 'wiki_index.txt'))

    with open(os.path.join(DST_DIR, 'index.txt'), 'w', encoding='utf-8') as f:
        f.write(json_file_to_minified_str(os.path.join(INDEX_SRC_DIR, 'prebuilt_full_index.json')))

