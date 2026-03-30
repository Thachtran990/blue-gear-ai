import json
from pymongo import MongoClient
from bson import json_util

# 1. KẾT NỐI TỚI TRẠM DỮ LIỆU MONGODB
# Captain hãy điền Connection String của ngài vào đây
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("🚨 BÁO ĐỘNG: Không tìm thấy MONGO_URI trong file .env!")
    print("Mẹo: Captain hãy kiểm tra lại file .env xem đã ghi đúng tên biến chưa nhé.")
    exit()
    
client = MongoClient(MONGO_URI)

# Đảm bảo đúng tên Database và Collection
db = client['test'] 
collection = db['products']

def export_to_json():
    print("🛰️  Radar: Đang truy quét hạm đội dữ liệu...")
    
    try:
        # Lấy toàn bộ sản phẩm
        products = list(collection.find({}))
        ai_friendly_data = []
        
        for p in products:
            # 🚀 XỬ LÝ MẢNG FILTERS ĐA ĐIỂM (Lọc bỏ _id ẩn)
            raw_filters = p.get("filters", [])
            clean_filters = []
            if isinstance(raw_filters, list):
                for f in raw_filters:
                    # Chỉ lấy k và v, bỏ qua _id để tránh lỗi JSON serializable
                    clean_filters.append({
                        "k": f.get("k", ""),
                        "v": f.get("v", "")
                    })

            # 🚀 XỬ LÝ MẢNG SPECS CHI TIẾT
            raw_specs = p.get("specs", [])
            clean_specs = []
            if isinstance(raw_specs, list):
                for s in raw_specs:
                    clean_specs.append({
                        "k": s.get("k", ""),
                        "v": s.get("v", "")
                    })

            # 🎯 ĐÓNG GÓI TỌA ĐỘ CHIẾN THUẬT
            item = {
                "id": str(p.get("_id")),
                "name": p.get("name"),
                "category": p.get("category"),
                "brand": p.get("brand"),
                "price": p.get("price"),
                # Lấy trọn bộ 8 Specs hiển thị
                "performance": p.get("performance", {}),
                # Mảng bộ lọc đã được làm sạch
                "filters": clean_filters,
                "specs": clean_specs,
                "description": p.get("shortDescription", p.get("description", ""))[:300]
            }
            ai_friendly_data.append(item)

        # 2. XUẤT RA FILE JSON (UTF-8 chuẩn chỉ)
        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(ai_friendly_data, f, ensure_ascii=False, indent=2)
            
        print("--------------------------------------------------")
        print(f"✅ THÀNH CÔNG: Đã cấy ghép {len(ai_friendly_data)} sản phẩm.")
        print("📂 File products.json đã được làm sạch và sẵn sàng cho AI!")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"❌ LỖI HỆ THỐNG: {e}")

if __name__ == "__main__":
    export_to_json()