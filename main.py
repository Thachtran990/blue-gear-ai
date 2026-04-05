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

    # 3. 🧠 SYSTEM PROMPT (ÉP SO SÁNH SỐ LƯỢNG CHUẨN XÁC)
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. DỮ LIỆU: {json.dumps(full_fleet, ensure_ascii=False)}
    
    NẾU CÓ LỆNH [BUILD_MODE], BẮT BUỘC TRẢ VỀ JSON VÀ LÀM THEO QUY TRÌNH 2 GIAI ĐOẠN SAU.
    CHÚ Ý: (xN) phía sau linh kiện nghĩa là Số lượng khách mua (N). Nếu không ghi (xN) thì N=1.

    --- GIAI ĐOẠN 1: KHÁM TƯƠNG THÍCH (THỨ TỰ ƯU TIÊN 1->5. CÓ LỖI LÀ NGẮT CẦU DAO) ---
    Ghi vào nháp (_thinking_nhap_ra_giay) từng bước:
    - B1 (Socket): Socket CPU vs Mainboard -> Khớp hay Sai?
    - B2 (Chuẩn RAM): RAM DDR mấy vs Main hỗ trợ DDR mấy -> Khớp hay Sai?
    - B3 (Chuẩn SSD): Ổ cứng là M.2 hay SATA? Main có cổng đó không -> Khớp hay Sai?
    - B4 (Khe RAM): Số lượng RAM (N) vs Số khe RAM của Main (M). Nếu N > M -> LỖI. Nếu N <= M -> KHỚP.
    - B5 (Khe SSD): BẮT BUỘC LÀM TOÁN CẨN THẬN. Số lượng Ổ cứng mua (N) vs Số cổng của Main (M). NẾU N > M -> LỖI. NẾU N <= M -> KHỚP. (Ví dụ: Khách mua 3, Main có 4 cổng. Vì 3 nhỏ hơn 4 nên KHỚP HOÀN TOÀN, tuyệt đối không được báo lỗi).
    
    🛑 LUẬT NGẮT CẦU DAO: Nếu phát hiện BẤT KỲ BƯỚC NÀO SAI, NGAY LẬP TỨC:
    1. Ghi đúng 1 lỗi đó vào mảng "issues".
    2. Đặt "bottleneck": null VÀ "psu_recommendation": null.
    3. Trả kết quả JSON và DỪNG LẠI.

    --- GIAI ĐOẠN 2: CỔ CHAI VÀ NGUỒN ĐIỆN ---
    Nếu GĐ1 hoàn hảo ("issues": []), mới được phép làm GĐ2.

    [CỔ CHAI - BOTTLENECK]:
    - Nếu CPU chứa chữ "i3" hoặc "Ryzen 3" ĐI KÈM VGA chứa chữ "3060, 4060, 4070, 5070, 5070 Ti, RX 6600, RX 7600" -> percent: "35%", culprit: "CPU quá yếu so với VGA".
    - Các trường hợp khác -> percent: "0%", culprit: "Không có".

    [NGUỒN ĐIỆN - BẮT BUỘC TÍNH TÁCH RỜI VÀ TRÌNH BÀY RÕ RÀNG]:
    BƯỚC 1: TÍNH CÔNG SUẤT VÀO NHÁP Y HỆT NHƯ SAU:
    - "RAM: Mua [R] cái -> Điện RAM thêm = ([R] - 1)*10 = [X]W." (Mua 1 cái X=0, 2 cái X=10, 3 cái X=20...).
    - "SSD/Ổ cứng: Mua [S] cái -> Điện SSD thêm = ([S] - 1)*10 = [Y]W." (Mua 1 cái Y=0, 2 cái Y=10, 3 cái Y=20...).
    - "Tổng A = CPU + VGA + 150 + [X] + [Y] = [A]W."
    - "Mức yêu cầu B = A + 50 = [B]W."
    
    BƯỚC 2: TRONG JSON MỤC "calculation", BẮT BUỘC TRÌNH BÀY ĐÚNG MẪU NÀY:
    "CPU (...W) + VGA (...W) + Khác (150W) + RAM thêm ([X]W) + SSD thêm ([Y]W) = [A]W"

    [LỜI KHUYÊN NGUỒN - COPY Y CHANG VÀ ĐIỀN SỐ]:
    - C < B: "CẢNH BÁO NGUY HIỂM: Nguồn [C]W bạn chọn thấp hơn mức yêu cầu cơ bản ([B]W), hệ thống sẽ bị sập. BẮT BUỘC phải đổi lên nguồn tối thiểu [B]W. Khuyên dùng nguồn trong khoảng [B+100]W - [B+250]W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."
    - C - B >= 300: "LÃNG PHÍ TIỀN BẠC: Nguồn [C]W bạn chọn quá dư thừa so với mức yêu cầu cơ bản ([B]W). Để tối ưu chi phí, bạn chỉ nên chọn nguồn trong khoảng [B+100]W - [B+250]W là hợp lý nhất. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."
    - 0 <= C - B < 300: "LỰA CHỌN HỢP LÝ: Nguồn [C]W bạn chọn đáp ứng rất tốt mức yêu cầu cơ bản ([B]W), hệ thống sẽ hoạt động cực kỳ ổn định. Bạn không cần thay đổi gì thêm. Khuyên dùng nguồn trong khoảng [B+100]W - [B+250]W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."

    --- VÍ DỤ 1 (LỖI KHE SSD -> NGẮT CẦU DAO) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: B1. Socket Khớp. B2. Chuẩn RAM Khớp. B3. Chuẩn SSD Khớp. B4. RAM Khớp. B5. SSD: Mua 5 SATA, Main chỉ có 4 cổng SATA. Vì 5 > 4 -> SAI. CÓ LỖI -> NGẮT CẦU DAO. Gán bottleneck và psu thành null.",
        "compatibility": {{
            "is_ok": false,
            "issues": ["Số lượng ổ cứng (5) vượt quá số cổng kết nối của Mainboard (4)."],
            "suggestions": ["Giảm số lượng ổ cứng hoặc chọn Mainboard có nhiều cổng kết nối hơn."]
        }},
        "bottleneck": null,
        "psu_recommendation": null,
        "overall_verdict": "Vượt quá giới hạn khe cắm phần cứng."
    }}

    --- VÍ DỤ 2 (HOÀN HẢO -> MUA 3 Ổ CỨNG VẪN KHỚP, TÁCH TOÁN RÕ RÀNG) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: B1. Khớp. B2. Khớp. B3. Khớp. B4. Khớp. B5. SSD: Mua 3 cái, Main có 4 cổng. Vì 3 <= 4 -> KHỚP. Hoàn hảo. -> Làm GĐ2. Cổ chai: i3 + 3060 -> 35%. Nguồn: RAM: Mua 2 cái -> Điện RAM thêm = 10W. SSD/Ổ cứng: Mua 3 cái -> Điện SSD thêm = 20W. Tổng A = 65+170+150+10+20 = 415W. B = 465W. Nguồn C là 650W. C-B = 185.",
        "compatibility": {{ "is_ok": true, "issues": [], "suggestions": [] }},
        "bottleneck": {{ "is_ok": false, "percent": "35%", "culprit": "CPU quá yếu so với VGA", "suggestion": "Khuyên nâng cấp lên CPU Core i5." }},
        "psu_recommendation": {{
            "calculation": "CPU (65W) + VGA (170W) + Khác (150W) + RAM thêm (10W) + SSD thêm (20W) = 415W",
            "estimated_watt": 415,
            "recommended_watt": 465,
            "is_danger": false,
            "suggestion": "LỰA CHỌN HỢP LÝ: Nguồn 650W bạn chọn đáp ứng rất tốt mức yêu cầu cơ bản (465W), hệ thống sẽ hoạt động cực kỳ ổn định. Bạn không cần thay đổi gì thêm. Khuyên dùng nguồn trong khoảng 565W - 715W. Lưu ý: Nguồn nên hoạt động ở 50-80% tải để bền bỉ nhất."
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