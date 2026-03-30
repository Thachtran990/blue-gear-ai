import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. CẤU HÌNH HỆ THỐNG
load_dotenv()

# Lấy mã API Key từ biến môi trường GEMINI_API_KEY
# (Đảm bảo Captain đã tạo file .env có dòng GEMINI_API_KEY=...)
MY_API_KEY = os.getenv("GEMINI_API_KEY")

# Khởi tạo client với SDK mới nhất
client = genai.Client(api_key=MY_API_KEY)

app = FastAPI()

# Cấu hình CORS để Frontend (index.html) có thể gọi tới
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# 🎯 MODEL ĐÍCH DANH CỦA CAPTAIN
TARGET_MODEL = 'gemini-2.5-flash' # Hoặc 'gemini-2.5-flash-preview-09-2025' tùy phiên bản Captain đã kích hoạt

# 📁 NẠP DỮ LIỆU HẠM ĐỘI (products.json)
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

# 🧠 HƯỚNG DẪN CHIẾN THUẬT (SYSTEM INSTRUCTION)
# Chúng ta nạp toàn bộ 143 sản phẩm vào bộ não AI
SYSTEM_PROMPT = f"""
Bạn là 'Blue Gear AI Commander' - Chuyên gia tối cao về phần cứng của hạm đội Blue Gear.
Dưới đây là TOÀN BỘ dữ liệu sản phẩm trong kho của chúng ta (đã được trích xuất từ Database):
{json.dumps(fleet_data, ensure_ascii=False)}

NHIỆM VỤ CỦA BẠN:
1. TRẢ LỜI CHÍNH XÁC: Khi khách hỏi về giá, thông số (v1-v8), hoặc loại sản phẩm, bạn PHẢI tra cứu trong danh sách trên trước.
2. TƯ VẤN THÔNG MINH: Nếu khách muốn build PC hoặc tìm sản phẩm theo 'filters' (ví dụ: 'Hồ cá', 'Dưới 1 triệu'), hãy lọc trong dữ liệu trên để gợi ý.
3. GOOGLE SEARCH: Sử dụng công cụ tìm kiếm nếu khách hỏi về kiến thức công nghệ mới nhất hoặc các sản phẩm không có trong kho của Matrix.
4. PHONG CÁCH: Gọi khách là 'Captain', xưng là 'AI Commander'. Ngôn ngữ mạnh mẽ, quyết đoán, đậm chất quân sự công nghệ.
"""

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not MY_API_KEY:
        return {"answer": "🚨 Báo động! Captain chưa nạp API Key mới vào file main.py."}

    try:
        # 🚀 TRIỂN KHAI HỎA LỰC: Kết hợp Dữ liệu nội bộ + Google Search
        response = client.models.generate_content(
            model=TARGET_MODEL,
            contents=request.message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7 # Độ sáng tạo vừa phải để tư vấn chuẩn
            )
        )
        
        # Kiểm tra xem có câu trả lời không
        answer = response.text if response.text else "Hệ thống đang xử lý, vui lòng thử lại lệnh."
        
        return {
            "answer": answer, 
            "using_search": True if response.candidates[0].grounding_metadata else False
        }
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ LỖI HỆ THỐNG: {error_msg}")
        
        if "403" in error_msg or "leaked" in error_msg:
            return {"answer": "🚨 Captain! API Key này đã bị Google chặn (Leaked). Hãy tạo Key mới tại AI Studio và dán vào main.py ngay!"}
        
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "═"*60)
    print(f"🚀 BLUE GEAR AI COMMANDER 2.5 ONLINE")
    print(f"🛰️  Target Model: {TARGET_MODEL}")
    print(f"📦 Loaded: {len(fleet_data)} products from products.json")
    print("═"*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)