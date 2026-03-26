import json
from pymongo import MongoClient
from bson import json_util

# 1. KẾT NỐI TỚI TRẠM DỮ LIỆU MONGODB
# Nếu ngài dùng MongoDB Local, giữ nguyên đường dẫn này
# Nếu dùng Atlas, hãy thay bằng Connection String của ngài
MONGO_URI = "mongodb://thachtran990_db_user:xIPePwXnCxMeY6gO@ac-5hloagw-shard-00-00.uwjnyap.mongodb.net:27017/?ssl=true&authSource=admin" 
client = MongoClient(MONGO_URI)

# Thay 'bluegear' bằng tên DATABASE thật của ngài
db = client['test'] 
# Thay 'products' bằng tên COLLECTION thật của ngài
collection = db['products']

def export_to_json():
    print("🛰️ Radar: Đang bắt đầu truy quét dữ liệu từ MongoDB...")
    
    try:
        # Lấy toàn bộ sản phẩm ra
        products = list(collection.find({}))
        
        # 🎯 CHỈNH SỬA CẤU TRÚC CHO AI DỄ HIỂU
        # AI cần các trường như: name, price, category, specs (socket, tdp...)
        ai_friendly_data = []
        
        for p in products:
            # Map dữ liệu từ MongoDB sang cấu trúc mà ta đã thảo luận ở file product_data_strategy.md
            item = {
                "id": str(p.get("_id")),
                "name": p.get("name"),
                "category": p.get("category"),
                "price": p.get("price"),
                "brand": p.get("brand"),
                # Nếu ngài có trường specs chi tiết, hãy lấy nó ra
                "specs": p.get("performance", {}), # Hoặc p.get("specs") tùy cấu trúc ngài đặt
                "description": p.get("shortDescription", p.get("description", ""))[:200] # Lấy 200 ký tự cho nhẹ
            }
            ai_friendly_data.append(item)

        # 2. XUẤT RA FILE JSON
        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(ai_friendly_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ THÀNH CÔNG: Đã cấy ghép {len(ai_friendly_data)} sản phẩm vào file products.json")
        print("📍 Bây giờ Captain có thể dùng file này để 'mồi' cho AI rồi!")

    except Exception as e:
        print(f"❌ LỖI: Không thể kết nối hoặc truy xuất. Chi tiết: {e}")

if __name__ == "__main__":
    export_to_json()