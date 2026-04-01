import os
import json
import hashlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# 🚀 1. KHỞI TẠO HỆ THỐNG
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TARGET_MODEL = "gpt-4o-mini"

# 🗄️ BỘ NHỚ CACHE & DỮ LIỆU
response_cache = {}

def load_standardized_fleet():
    if os.path.exists('products.json'):
        with open('products.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

full_fleet = load_standardized_fleet()

# 🛡️ SMART GATEKEEPER (Bộ lọc thông minh)
def is_relevant_query(query: str):
    """Phân loại câu hỏi để tránh trả lời ngoài luồng"""
    query_lower = query.lower()
    fast_keywords = [
        "chuột", "phím", "tai nghe", "vga", "cpu", "ram", "main", "nguồn", "pc", "laptop",
        "build", "tư vấn", "lỗi", "hỏng", "sửa", "giá", "so sánh", "fps", "game", "tương thích"
    ]
    if any(k in query_lower for k in fast_keywords):
        return True
    
    try:
        response = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là bộ lọc cho shop máy tính. Nếu liên quan linh kiện, kỹ thuật, build PC hoặc chào hỏi, đáp 'PASS'. Ngược lại đáp 'FAIL'."},
                {"role": "user", "content": query}
            ],
            max_tokens=5, temperature=0
        )
        return "PASS" in response.choices[0].message.content.upper()
    except:
        return True

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    user_msg = request.message.strip()
    
    # 1. Kiểm tra Gatekeeper
    if not is_relevant_query(user_msg):
        return {
            "answer": "Báo cáo Captain, tôi chỉ chuyên trách quản lý hạm đội Blue Gear và hỗ trợ kỹ thuật máy tính. Yêu cầu của ngài nằm ngoài phạm vi tác chiến của tôi.",
            "using_search": False
        }

    # 2. Kiểm tra Cache
    cache_key = hashlib.md5(user_msg.lower().encode()).hexdigest()
    if cache_key in response_cache:
        return response_cache[cache_key]

    # 3. Xây dựng System Prompt cực kỳ chi tiết
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. Trạm chỉ huy tối cao của Blue Gear.
    DỮ LIỆU KHO HÀNG ({len(full_fleet)} món): {json.dumps(full_fleet, ensure_ascii=False)}

    QUY TẮC TÁC CHIẾN (MASTER RULES):

    1. LINK SẢN PHẨM (QUAN TRỌNG NHẤT):
       - Định dạng bắt buộc: [Tên sản phẩm](/product/slug).
       - TUYỆT ĐỐI KHÔNG thêm bất kỳ domain nào (bluegear.com, example.com, localhost) hay http/https. 

    2. BUILD PC & TƯƠNG THÍCH:
       - Socket Check: CPU và Mainboard PHẢI trùng khớp 'ai_logic.socket'.
       - RAM Check: 'ai_logic.ram_type' của RAM và Mainboard PHẢI giống nhau.
       - Nguồn Check: Tổng (CPU_watt + VGA_watt + 100W dự phòng) <= Nguồn_watt.

    3. SO SÁNH & CỔ CHAI:
       - Dùng 'ai_logic.performance_score' để tính % chênh lệch hiệu năng.
       - Cảnh báo cổ chai (Bottleneck) nếu Score CPU và VGA lệch nhau > 25 điểm.

    4. ƯỚC LƯỢNG FPS (Dựa trên Score VGA):
       - Score >= 85: 4K/2K Ultra (Cyberpunk > 60, Valorant > 400).
       - Score 60-84: 2K/FHD Ultra (Cyberpunk > 60, Valorant > 300).
       - Score 40-59: FHD High (GTA V > 80, Valorant > 200).
       - Score < 40: FHD Medium (Valorant > 100).

    5. AI DOCTOR (CHẨN ĐOÁN):
       - Khi khách báo lỗi: Hỏi triệu chứng -> Đưa ra 3 nguyên nhân -> Gợi ý linh kiện thay thế từ KHO.

    6. PHONG CÁCH: Captain, quân sự, ngắn gọn, trình bày bảng biểu sạch sẽ khi so sánh hoặc build máy. Không lẩm bẩm tính toán.
    """

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in request.history[-6:]:
            role = "assistant" if msg['role'] == "model" else "user"
            messages.append({"role": role, "content": msg['content']})
        messages.append({"role": "user", "content": user_msg})

        response = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=messages,
            temperature=0, 
        )
        
        answer = response.choices[0].message.content
        
        # Hậu kiểm link - Xóa sạch mọi dấu vết domain
        bad_domains = ["https://example.com", "http://example.com", "https://bluegear.com", "localhost:3000"]
        for domain in bad_domains:
            answer = answer.replace(domain, "")

        result = {"answer": answer, "using_search": False}
        if len(user_msg) > 10: response_cache[cache_key] = result
        
        return result
        
    except Exception as e:
        return {"answer": f"🚨 Lỗi radar: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 AI COMMANDER MASTER EDITION ACTIVE - KHO: {len(full_fleet)} SP")
    uvicorn.run(app, host="127.0.0.1", port=8000)