import json
import os
import re
from pymongo import MongoClient
from dotenv import load_dotenv

# 🚀 1. KHỞI TẠO
load_dotenv()

def slugify(text):
    if not text: return ""
    text = text.lower()
    patterns = {'[àáảãạăằắẳẵặâầấẩẫậ]': 'a', '[èéẻẽẹêềếểễệ]': 'e', '[ìíỉĩị]': 'i', '[òóỏõọôồốổỗộơờớởỡợ]': 'o', '[ùúủũụưừứửữự]': 'u', '[ỳýỷỹỵ]': 'y', 'đ': 'd'}
    for pattern, replacement in patterns.items(): text = re.sub(pattern, replacement, text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'\s+', '-', text).strip('-')

# 🛠️ CÔNG CỤ TRUY QUÉT DỮ LIỆU "LÌ LỢM"
def mine_data(specs_dict, product_name, category):
    logic = {"wattage": 0, "socket": "N/A", "ram_type": "N/A", "performance_score": 0}
    
    # Gộp tất cả text lại để quét cho nhanh
    all_text = (product_name + " " + " ".join([f"{k} {v}" for k, v in specs_dict.items()])).upper()

    # 1. TRUY TÌM SOCKET (Dành cho CPU & Main)
    if any(k in category for k in ["CPU", "Mainboard"]):
        if "LGA 1700" in all_text or "LGA1700" in all_text or "1700" in all_text: logic["socket"] = "LGA1700"
        elif "AM4" in all_text: logic["socket"] = "AM4"
        elif "AM5" in all_text: logic["socket"] = "AM5"
        elif "LGA 1200" in all_text or "1200" in all_text: logic["socket"] = "LGA1200"
        elif "1851" in all_text: logic["socket"] = "LGA1851"

    # 2. TRUY TÌM CÔNG SUẤT (TDP / WATTAGE)
    # Tìm số đứng trước chữ W, WATT, TPD
    watt_match = re.search(r'(\d+)\s*(W|WATT|TDP)', all_text)
    if watt_match:
        logic["wattage"] = int(watt_match.group(1))
    else:
        # Nếu là Nguồn, tìm số lớn nhất (thường là công suất tổng)
        if "Nguồn" in category:
            nums = re.findall(r'\d+', all_text)
            nums = [int(n) for n in nums if 300 <= int(n) <= 1600]
            if nums: logic["wattage"] = max(nums)

    # 3. TRUY TÌM LOẠI RAM (DDR4 / DDR5)
    if "DDR5" in all_text: logic["ram_type"] = "DDR5"
    elif "DDR4" in all_text: logic["ram_type"] = "DDR4"

    return logic

def export_to_json():
    print("🛰️  AI Radar: Đang truy quét và khai thác dữ liệu thô...")
    MONGO_URI = os.getenv("MONGO_URI")
    try:
        client = MongoClient(MONGO_URI)
        db = client['test'] 
        collection = db['products']
        products = list(collection.find({}))
        
        final_data = []
        for p in products:
            p_name = p.get("name", "")
            cat = p.get("category", "")
            # Biến specs thành dictionary
            specs_dict = {s.get("k"): s.get("v") for s in p.get("specs", []) if s.get("k")}
            
            # Sử dụng bộ lọc "lì lợm" để đào dữ liệu
            ai_logic = mine_data(specs_dict, p_name, cat)

            # 📸 🚀 LẤY LINK ẢNH TỪ MONGODB
            # Giả sử trong DB của mày trường ảnh tên là 'images' (dạng mảng) hoặc 'image' (dạng chuỗi)
            db_images = p.get("images", []) 
            if isinstance(db_images, list) and len(db_images) > 0:
                img_url = db_images[0] # Lấy ảnh đầu tiên trong mảng
            else:
                # Nếu không phải mảng thì lấy trường 'image', nếu không có nữa thì gán tạm link mẫu
                img_url = p.get("image", "https://res.cloudinary.com/dvcugvh5t/image/upload/v1773906360/GamingGearShop/psinu6ww53c2vucpfswu.jpg")

            item = {
                "slug": p.get("slug") or slugify(p_name),
                "name": p_name,
                "category": cat,
                "price": p.get("price", 0),
                "brand": p.get("brand"),
                "image": img_url, # 🎯 BƠM LINK ẢNH CLOUDINARY VÀO ĐÂY
                "technical_details": specs_dict,
                "ai_logic": ai_logic # 🎯 Dữ liệu vàng cho AI làm toán
            }
            final_data.append(item)

        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ THÀNH CÔNG: Đã đào được dữ liệu từ {len(final_data)} sản phẩm.")
        print("🚀 Captain không cần sửa gì trong DB cả, script đã tự 'thông não' xong!")
    except Exception as e:
        print(f"❌ LỖI TRUY QUÉT: {e}")

if __name__ == "__main__":
    export_to_json()