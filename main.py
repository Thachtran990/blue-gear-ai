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

    # 3. 🧠 SYSTEM PROMPT (KIỆT TÁC: NGẮT CẦU DAO & KHUÔN MẪU TUYỆT ĐỐI)
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. DỮ LIỆU: {json.dumps(full_fleet, ensure_ascii=False)}
    
    NẾU CÓ LỆNH [BUILD_MODE], BẮT BUỘC TRẢ VỀ JSON VÀ LÀM THEO QUY TRÌNH 2 GIAI ĐOẠN SAU.
    CHÚ Ý: (xN) phía sau linh kiện nghĩa là Số lượng khách mua (N). Nếu không ghi (xN) thì N=1.

    --- GIAI ĐOẠN 1: KHÁM TƯƠNG THÍCH (THỨ TỰ ƯU TIÊN 1->5. CÓ LỖI LÀ NGẮT CẦU DAO) ---
    Ghi vào nháp (_thinking_nhap_ra_giay) từng bước:
    - B1 (Socket): Socket CPU vs Mainboard.
    - B2 (Chuẩn RAM): RAM DDR mấy vs Main hỗ trợ DDR mấy.
    - B3 (Chuẩn SSD): Ổ cứng là M.2 hay SATA? Main có cổng đó không?
    - B4 (Khe RAM): Số lượng RAM (N) vs Số khe RAM của Main.
    - B5 (Khe SSD): Nếu SSD là M.2 -> So sánh Số lượng (N) vs Số cổng M.2 của Main. Nếu SSD là SATA -> So sánh Số lượng (N) vs Số cổng SATA của Main.
    
    🛑 LUẬT NGẮT CẦU DAO: Nếu phát hiện BẤT KỲ BƯỚC NÀO SAI (N > Khe cắm, hoặc sai chuẩn), NGAY LẬP TỨC:
    1. Ghi đúng 1 lỗi đó vào mảng "issues".
    2. Đặt "bottleneck": null VÀ "psu_recommendation": null. (Không được tính toán nguồn hay cổ chai nữa).
    3. Trả kết quả JSON và DỪNG LẠI.

    --- GIAI ĐOẠN 2: CỔ CHAI VÀ NGUỒN ĐIỆN (CHỈ LÀM KHI GIAI ĐOẠN 1 VƯỢT QUA KHÔNG CÓ LỖI) ---
    Nếu GĐ1 hoàn hảo ("issues": []), mới được phép làm GĐ2.

    [CỔ CHAI - BOTTLENECK]:
    - Nếu CPU chứa chữ "i3" hoặc "Ryzen 3" ĐI KÈM VGA chứa chữ "3060, 4060, 4070, 5070, 5070 Ti, RX 6600, RX 7600" -> percent: "35%", culprit: "CPU quá yếu không khai thác hết hiệu năng của VGA".
    - Các trường hợp khác (i5, i7, i9...) -> percent: "0%", culprit: "Không có".

    [NGUỒN ĐIỆN - PSU]:
    1. TÍNH ĐIỆN PHỤ BẮT BUỘC TÁCH RỜI: 
       - RAM: (Số lượng - 1)*10W. (VD: 1 cái -> 0W, 2 cái -> 10W)
       - SSD: (Số lượng - 1)*10W. (VD: 1 cái -> 0W, 3 cái -> 20W)
       - Quạt: (Số lượng - 1)*10W.
       -> TỔNG PHỤ = RAM + SSD + Quạt. (VD: 1 RAM và 1 SSD = 0W + 0W = 0W).
    2. [A] = CPU + VGA + 150 + TỔNG PHỤ.
    3. [B] Mức yêu cầu = [A] + 50.
    4. [C] Nguồn khách chọn.
    5. [D] = [C] - [B].
    
    CHỌN 1 TRONG 3 VĂN MẪU DƯỚI ĐÂY ĐỂ ĐIỀN VÀO "suggestion" (COPY Y CHANG TỪNG CHỮ, CHỈ ĐỔI SỐ):
    - Nếu D < 0 (is_danger: true): "CẢNH BÁO NGUY HIỂM: Nguồn [C]W bạn chọn thấp hơn mức yêu cầu cơ bản ([B]W), hệ thống sẽ bị sập. BẮT BUỘC phải đổi lên nguồn tối thiểu [B]W. Khuyên dùng nguồn trong khoảng [B+100]W - [B+250]W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."
    - Nếu D >= 300 (is_danger: false): "LÃNG PHÍ TIỀN BẠC: Nguồn [C]W bạn chọn quá dư thừa so với mức yêu cầu cơ bản ([B]W). Để tối ưu chi phí, bạn chỉ nên chọn nguồn trong khoảng [B+100]W - [B+250]W là hợp lý nhất. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."
    - Nếu 0 <= D < 300 (is_danger: false): "LỰA CHỌN HỢP LÝ: Nguồn [C]W bạn chọn đáp ứng rất tốt mức yêu cầu cơ bản ([B]W), hệ thống sẽ hoạt động cực kỳ ổn định. Bạn không cần thay đổi gì thêm. Khuyên dùng nguồn trong khoảng [B+100]W - [B+250]W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."

    --- VÍ DỤ 1 (CÓ LỖI TƯƠNG THÍCH -> NGẮT CẦU DAO) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: B1. Socket Khớp. B2. Chuẩn RAM Khớp. B3. Chuẩn SSD Khớp. B4. RAM Khớp. B5. SSD: Mua 5 SATA, Main chỉ có 4 cổng SATA -> SAI. CÓ LỖI -> NGẮT CẦU DAO. Gán bottleneck và psu thành null.",
        "compatibility": {{
            "is_ok": false,
            "issues": ["Số lượng ổ cứng (5) vượt quá số cổng kết nối của Mainboard (4)."],
            "suggestions": ["Giảm số lượng ổ cứng hoặc chọn Mainboard có nhiều cổng kết nối hơn."]
        }},
        "bottleneck": null,
        "psu_recommendation": null,
        "overall_verdict": "Vượt quá giới hạn khe cắm phần cứng."
    }}

    --- VÍ DỤ 2 (HOÀN HẢO -> TÍNH TOÁN THEO VĂN MẪU) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: Hoàn hảo. -> Làm GĐ2. Cổ chai: i3 + 3060 -> 35%. Nguồn: Điện phụ: RAM(x1)->0W, SSD(x1)->0W -> TỔNG PHỤ = 0W. A = 65+170+150+0 = 385W. B = 435W. C = 650W. D = 650-435 = 215. 0 <= 215 < 300 -> Hợp lý.",
        "compatibility": {{ "is_ok": true, "issues": [], "suggestions": [] }},
        "bottleneck": {{ "is_ok": false, "percent": "35%", "culprit": "CPU quá yếu không khai thác hết hiệu năng của VGA", "suggestion": "Khuyên nâng cấp lên CPU Core i5." }},
        "psu_recommendation": {{
            "calculation": "CPU (65W) + VGA (170W) + Khác (150W) + Linh kiện thêm (0W) = 385W",
            "estimated_watt": 385,
            "recommended_watt": 435,
            "is_danger": false,
            "suggestion": "LỰA CHỌN HỢP LÝ: Nguồn 650W bạn chọn đáp ứng rất tốt mức yêu cầu cơ bản (435W), hệ thống sẽ hoạt động cực kỳ ổn định. Bạn không cần thay đổi gì thêm. Khuyên dùng nguồn trong khoảng 535W - 685W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."
        }},
        "overall_verdict": "Xung đột cổ chai hệ thống."
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