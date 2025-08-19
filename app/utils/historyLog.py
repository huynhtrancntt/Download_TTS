import os
import json

def save_history_log(json_file, entry):

                # Đọc dữ liệu cũ nếu file đã tồn tại
                if os.path.exists(json_file):
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        data = []  # nếu file bị rỗng hoặc hỏng, tạo list mới
                else:
                    data = []

                # Thêm entry mới
                data.append(entry)

                # Ghi đè toàn bộ list vào file
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)