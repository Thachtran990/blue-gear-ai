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
response_cache = {}

def load_standardized_fleet():
    if os.path.exists('products.json'):
        with open('products.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

full_fleet = load_standardized_fleet()

def is_relevant_query(query: str):
    query_lower = query.lower()
    fast_keywords = [
        "chuột", "phím", "tai nghe", "vga", "cpu", "ram", "main", "nguồn", "pc", "laptop",
        "build", "tư vấn", "lỗi", "hỏng", "sửa", "giá", "so sánh", "fps", "game", "tương thích",
        "arena", "quét"
    ]
    if any(k in query_lower for k in fast_keywords):
        return True
    
    try:
        response = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là bộ lọc cho shop. Nếu liên quan máy tính đáp 'PASS', ngược lại 'FAIL'."},
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
    
    if not is_relevant_query(user_msg):
        return {"answer": "Báo cáo Captain, yêu cầu nằm ngoài phạm vi tác chiến của tôi.", "using_search": False}

    cache_key = hashlib.md5(user_msg.lower().encode()).hexdigest()
    if cache_key in response_cache:
        return response_cache[cache_key]

    # 3. 🧠 SYSTEM PROMPT (ÉP SUY NGHĨ NHÁP BẰNG CHAIN-OF-THOUGHT)
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. DỮ LIỆU ({len(full_fleet)} món): {json.dumps(full_fleet, ensure_ascii=False)}
    
    NẾU THẤY LỆNH [BUILD_MODE], BẮT BUỘC TRẢ VỀ JSON VÀ PHẢI LÀM ĐÚNG 4 BƯỚC SUY NGHĨ NHÁP SAU ĐÂY VÀO TRƯỜNG "_thinking_nhap_ra_giay":

    Bước 1 (Tương thích): Socket CPU có khớp Main không? Loại RAM (DDR4/5) có khớp Main không? (Nhớ: CPU Intel hỗ trợ cả hai, Main mới quyết định).
    Bước 2 (Cổ chai): CPU này đi với VGA này có nghẽn không? (Quy tắc cứng: i3/Ryzen 3 đi với VGA 4060 trở lên CHẮC CHẮN NGHẼN > 15%).
    Bước 3 (Tính Watt): Watt CPU + Watt VGA + 100W = [A]. Nguồn yêu cầu = [A] + 150W = [B].
    Bước 4 (So sánh Nguồn): Cục nguồn khách chọn là [C] Watt. Lấy [C] trừ đi [B]. Nếu kết quả >= 200W, phải CHÊ LÃNG PHÍ.

    Sau khi nháp xong, điền kết quả vào JSON theo format chuẩn sau:
    {{
        "_thinking_nhap_ra_giay": "Ghi toàn bộ nháp của 4 bước trên vào đây...",
        "compatibility": {{
            "is_ok": true/false,
            "issues": ["Ghi lỗi nếu sai Socket/RAM, nếu đúng BẮT BUỘC để mảng rỗng"],
            "suggestions": ["Gợi ý thay thế hoặc để rỗng"]
        }},
        "bottleneck": {{
            "is_ok": true/false,
            "percent": "Ví dụ: 0% hoặc 25%",
            "culprit": "Ghi thủ phạm (nếu có) hoặc ghi 'Không có'",
            "suggestion": "Ghi cách khắc phục hoặc khen 'Cân bằng tốt'"
        }},
        "psu_recommendation": {{
            "calculation": "Ghi rõ phép cộng. VD: CPU (65W) + VGA (115W) + Khác (100W) = 280W",
            "estimated_watt": số_nguyên,
            "recommended_watt": số_nguyên,
            "suggestion": "Viết lời khuyên dựa trên nháp Bước 4. Nếu dư thừa >= 200W, BẮT BUỘC dùng từ 'QUÁ DƯ THỪA, LÃNG PHÍ'. KẾT THÚC BẰNG CÂU: 'Lưu ý: Nguồn máy tính chỉ nên hoạt động ở mức 75-80% công suất thiết kế để đảm bảo nhiệt độ mát mẻ, tuổi thọ linh kiện và dòng điện ổn định nhất.'"
        }},
        "overall_verdict": "Kết luận tổng thể."
    }}

    [ARENA_MODE]: Giữ nguyên như cũ. TRẢ DUY NHẤT JSON.
    """

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in request.history[-6:]:
            role = "assistant" if msg['role'] == "model" else "user"
            messages.append({"role": role, "content": msg['content']})
        messages.append({"role": "user", "content": user_msg})

        # BẬT CHẾ ĐỘ ÉP JSON BẰNG API CỦA OPENAI
        response = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=messages,
            temperature=0,
            response_format={ "type": "json_object" } 
        )
        
        answer = response.choices[0].message.content
        
        if ("[ARENA_MODE]" in user_msg or "[BUILD_MODE]" in user_msg) and "```" in answer:
            answer = answer.replace("```json", "").replace("```", "").strip()

        bad_domains = ["[https://example.com](https://example.com)", "[http://example.com](http://example.com)", "[https://bluegear.com](https://bluegear.com)", "localhost:3000", "http://localhost:8000"]
        for domain in bad_domains:
            answer = answer.replace(domain, "")

        result = {"answer": answer, "using_search": False}
        if len(user_msg) > 10: response_cache[cache_key] = result
        
        return result
        
    except Exception as e:
        return {"answer": f"🚨 Lỗi radar: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 AI COMMANDER READY - KHO: {len(full_fleet)} SP")
    uvicorn.run(app, host="127.0.0.1", port=8000)