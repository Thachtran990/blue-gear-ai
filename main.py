import os
import json
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 🚀 1. NẠP BIẾN MÔI TRƯỜNG
load_dotenv()
MY_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=MY_API_KEY)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

TARGET_MODEL = 'gemini-2.5-flash'

# 🗄️ BỘ NHỚ ĐỆM & TỪ KHÓA LỌC
response_cache = {}
TECH_KEYWORDS = [
    "pc", "laptop", "vga", "cpu", "ram", "main", "nguồn", "case", "chuột", "phím", 
    "tai nghe", "màn hình", "tản nhiệt", "ssd", "ổ cứng", "build", "tư vấn", 
    "so sánh", "giá", "bao nhiêu", "lỗi", "hỏng", "matrix", "blue gear"
]

# 📁 NẠP DỮ LIỆU HẠM ĐỘI
def load_fleet_data():
    try:
        if os.path.exists('products.json'):
            with open('products.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"⚠️ Radar: Lỗi đọc file products.json: {e}")
        return []

fleet_data = load_fleet_data()

# 🧠 HƯỚNG DẪN CHIẾN THUẬT (SYSTEM INSTRUCTION NÂNG CẤP)
SYSTEM_PROMPT = f"""
Bạn là 'Blue Gear AI Commander'. Bạn có nhiệm vụ dẫn đường cho Captain tìm thấy vũ khí phù hợp.

DỮ LIỆU KHO HÀNG:
{json.dumps(fleet_data, ensure_ascii=False)}

QUY TẮC ĐIỀU HƯỚNG (URL GENERATION):
1. DẪN ĐẾN SẢN PHẨM: Nếu bạn gợi ý 1 sản phẩm cụ thể, hãy dùng định dạng: [Tên sản phẩm](/product/slug-cua-san-pham). 
   (Ví dụ: [Chuột G502](/product/chuot-logitech-g502-x-plus)).
2. DẪN ĐẾN DANH MỤC: Nếu khách hỏi chung chung về một loại linh kiện, hãy dẫn họ tới: [/category/ten-danh-muc-viet-thuong-khong-dau-thay-khoang-cach-bang-dau-gach-ngang].
   (Ví dụ: [Xem tất cả VGA](/category/vga-card-man-hinh)).
3. KHÔNG TỰ CHẾ LINK: Chỉ dùng Slug có trong dữ liệu JSON. Nếu không chắc chắn, chỉ dẫn tới Link danh mục chung.

PHONG CÁCH: Quyết đoán, chuyên nghiệp, hỗ trợ Captain hết mình để 'chốt đơn' thành công.
"""

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

def is_off_topic(message: str) -> bool:
    msg_lower = message.lower()
    if len(msg_lower) < 5: return False
    return not any(key in msg_lower for key in TECH_KEYWORDS)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_msg = request.message.strip()
    
    # ⚡ 1. KIỂM TRA CACHE
    cache_key = hashlib.md5(user_msg.lower().encode()).hexdigest()
    if cache_key in response_cache:
        return response_cache[cache_key]

    # 🛡️ 2. LỌC NHIỄU
    if is_off_topic(user_msg):
        return {"answer": "Rõ Captain. Tôi chỉ có thể hỗ trợ các vấn đề về vũ khí phần cứng tại Blue Gear. Ngài muốn kiểm tra linh kiện nào?", "using_search": False}

    try:
        # 3. CHUẨN BỊ NGỮ CẢNH
        gemini_history = [
            types.Content(role=msg.role, parts=[types.Part(text=msg.content)])
            for msg in request.history
        ]
        
        current_contents = gemini_history + [
            types.Content(role="user", parts=[types.Part(text=user_msg)])
        ]

        # 🔫 KHAI HỎA
        response = client.models.generate_content(
            model=TARGET_MODEL,
            contents=current_contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        )
        
        answer = response.text if response.text else "Radar bị nhiễu, vui lòng thử lại."
        result = {
            "answer": answer,
            "using_search": True if response.candidates[0].grounding_metadata else False
        }

        # Lưu cache cho các câu hỏi tra cứu
        if len(user_msg) > 10:
            response_cache[cache_key] = result

        return result
    
    except Exception as e:
        print(f"❌ LỖI HỆ THỐNG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)