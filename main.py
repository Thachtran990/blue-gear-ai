import os
import json
import hashlib
from fastapi import FastAPI, HTTPException
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

# 📁 NẠP KHO HÀNG CHUẨN HÓA
def load_standardized_fleet():
    if os.path.exists('products.json'):
        with open('products.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

full_fleet = load_standardized_fleet()

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    user_msg = request.message.strip()
    
    # 🧠 SYSTEM PROMPT: NÂNG CẤP LOGIC SO SÁNH & CỔ CHAI
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. Bạn đang quản lý hạm đội linh kiện thông minh.
    KHO HÀNG ({len(full_fleet)} món): {json.dumps(full_fleet, ensure_ascii=False)}

    QUY TẮC TÁC CHIẾN CỤM 2:
    
    1. SO SÁNH SẢN PHẨM:
       - Khi khách yêu cầu so sánh 2 món (ví dụ: RTX 3060 vs GTX 1660 Ti), hãy dùng 'ai_logic.performance_score'.
       - Tính toán % chênh lệch hiệu năng: ((Score_A - Score_B) / Score_B) * 100.
       - Liệt kê các thông số kỹ thuật khác biệt lớn từ 'technical_details'.
       - Link: [Tên](/product/slug).

    2. PHÂN TÍCH CỔ CHAI (BOTTLENECK):
       - Quy tắc: CPU và VGA nên có 'performance_score' lệch nhau không quá 20-25 điểm.
       - Nếu Score CPU < (Score VGA - 25): Cảnh báo "Nghẽn cổ chai nặng do CPU yếu".
       - Nếu Score VGA < (Score CPU - 30): Cảnh báo "Lãng phí sức mạnh CPU cho VGA này".
       - Gợi ý linh kiện trong kho để cân bằng lại.

    3. BUILD PC & TÍNH NGUỒN (Duy trì Cụm 1):
       - (CPU_watt + VGA_watt + 100W dự phòng) <= Nguồn_watt.
       - Socket và RAM Type phải khớp 100%.

    4. KỶ LUẬT TRÌNH BÀY:
       - Link sạch: [Tên sản phẩm](/product/slug). Cấm domain lạ.
       - Trả lời quyết đoán, phong cách quân sự, ngắn gọn.
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
        
        # Hậu kiểm link (Bảo hiểm 100%)
        bad_domains = ["https://example.com", "http://example.com", "https://bluegear.com"]
        for domain in bad_domains:
            answer = answer.replace(domain, "")

        return {"answer": answer, "using_search": False}
        
    except Exception as e:
        return {"answer": f"🚨 Lỗi radar: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)