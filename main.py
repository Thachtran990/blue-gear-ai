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

    # 3. 🧠 SYSTEM PROMPT (DỰA TRÊN BẢN STABLE 4-4, TỐI ƯU FEW-SHOT)
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. DỮ LIỆU ({len(full_fleet)} món): {json.dumps(full_fleet, ensure_ascii=False)}
    
    NẾU THẤY LỆNH [BUILD_MODE], BẮT BUỘC TRẢ VỀ JSON VÀ BẮT CHƯỚC Y HỆT 1 TRONG 2 MẪU SAU ĐÂY.
    LƯU Ý: Nếu linh kiện có chữ (xN) phía sau, thì N là SỐ LƯỢNG khách mua.

    QUY TẮC TƯƠNG THÍCH (ƯU TIÊN TỪ TRÊN XUỐNG):
    1. TƯƠNG THÍCH SOCKET & CHUẨN: Nếu Socket sai -> Báo lỗi Socket. Nếu Chuẩn RAM sai -> Báo lỗi Chuẩn RAM. BỎ QUA KIỂM TRA SỐ LƯỢNG KHE CẮM.
    2. SỐ LƯỢNG KHE CẮM (Chỉ kiểm tra khi Socket và Chuẩn đã đúng): Lấy Số lượng (N) so với Số khe cắm của Mainboard. NẾU N > SỐ KHE -> Báo lỗi. NẾU N <= SỐ KHE -> HỢP LÝ, KHÔNG ĐƯỢC BÁO LỖI.

    QUY TẮC NGUỒN ĐIỆN (PSU) - TÍNH ĐỘC LẬP:
    - [A] = CPU + VGA + 150 + Điện linh kiện phụ. (Điện linh kiện phụ = Số lượng RAM/SSD/Fan MUA DƯ RA nhân với 10W. Ví dụ mua 3 RAM -> Dư 2 -> Cộng 20W).
    - [B] Yêu cầu tối thiểu = [A] + 50.
    - [C] Nguồn khách chọn.
    - Khuyên khách mua trong khoảng ([B] + 100W) đến ([B] + 250W).

    --- VÍ DỤ 1 BẠN PHẢI BẮT CHƯỚC: MỌI THỨ ĐÚNG, SỐ LƯỢNG KHE RAM VỪA ĐỦ, NHƯNG NGUỒN DƯ ---
    {{
        "_thinking_nhap_ra_giay": "Socket: Khớp. Chuẩn: Khớp. Số lượng RAM: Khách mua x2, Main có 2 khe. N=2 <= 2 -> An toàn. Nguồn: CPU 65W, VGA 135W, Khác 150W. Thêm 1 RAM dư (10W). A = 360W. B = 410W. C = 1000W. 1000 - 410 >= 300 -> Lãng phí.",
        "compatibility": {{
            "is_ok": true,
            "issues": [],
            "suggestions": []
        }},
        "bottleneck": {{ "is_ok": true, "percent": "0%", "culprit": "Không có", "suggestion": "Hệ thống cân bằng hoàn hảo." }},
        "psu_recommendation": {{
            "calculation": "CPU (65W) + VGA (135W) + Khác (150W) + Linh kiện thêm (10W) = 360W",
            "estimated_watt": 360,
            "recommended_watt": 410,
            "is_danger": false,
            "suggestion": "LÃNG PHÍ TIỀN BẠC: Cấu hình này chỉ cần nguồn 410W. Bạn đang chọn nguồn 1000W là quá dư thừa. Để tối ưu chi phí, bạn chỉ nên chọn nguồn trong khoảng 510W - 660W là hợp lý nhất. Lưu ý: Nguồn nên hoạt động ở 50-80% tải."
        }},
        "overall_verdict": "Cấu hình cân bằng nhưng lãng phí nguồn điện."
    }}

    --- VÍ DỤ 2 BẠN PHẢI BẮT CHƯỚC: SAI SOCKET + KHE RAM BỊ VƯỢT QUÁ + NGUỒN THIẾU ---
    {{
        "_thinking_nhap_ra_giay": "Socket: LGA1700 và AM5 không khớp -> Ưu tiên báo lỗi Socket, dừng kiểm tra khe RAM. Nguồn: CPU 65W, VGA 235W, Khác 150W, Thêm 0W. A = 450W. B = 500W. C = 400W. 400 < 500 -> Nguy hiểm.",
        "compatibility": {{
            "is_ok": false,
            "issues": ["Socket LGA 1700 của CPU không tương thích với Socket AM5 của Mainboard."],
            "suggestions": ["Đổi Mainboard sang dòng hỗ trợ Socket LGA 1700."]
        }},
        "bottleneck": {{ "is_ok": false, "percent": "35%", "culprit": "CPU quá yếu so với VGA", "suggestion": "Khuyên nâng cấp CPU." }},
        "psu_recommendation": {{
            "calculation": "CPU (65W) + VGA (235W) + Khác (150W) + Linh kiện thêm (0W) = 450W",
            "estimated_watt": 450,
            "recommended_watt": 500,
            "is_danger": true,
            "suggestion": "CẢNH BÁO NGUY HIỂM: Nguồn 400W bạn chọn thấp hơn mức yêu cầu cơ bản (500W), hệ thống sẽ bị sập hoặc cháy nổ khi tải nặng. BẮT BUỘC phải đổi nguồn. Lựa chọn an toàn là khoảng 600W - 750W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải."
        }},
        "overall_verdict": "Xung đột phần cứng nghiêm trọng và nguy hiểm nguồn điện."
    }}

    [ARENA_MODE]: Giữ nguyên như cũ. TRẢ DUY NHẤT JSON.
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