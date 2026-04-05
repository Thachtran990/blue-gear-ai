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

    # 3. 🧠 SYSTEM PROMPT (DÙNG BẢN GỐC CỦA CTO, CHỈ TỐI ƯU CÁCH AI LÀM TOÁN)
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. DỮ LIỆU: {json.dumps(full_fleet, ensure_ascii=False)}
    
    NẾU CÓ LỆNH [BUILD_MODE], BẮT BUỘC TRẢ VỀ JSON VÀ LÀM THEO QUY TRÌNH 2 GIAI ĐOẠN SAU.
    CHÚ Ý: (xN) phía sau linh kiện nghĩa là Số lượng khách mua (N). Nếu không ghi (xN) thì N=1.

    --- GIAI ĐOẠN 1: KHÁM TƯƠNG THÍCH (THỨ TỰ ƯU TIÊN 1->5. CÓ LỖI LÀ NGẮT CẦU DAO) ---
    Ghi vào nháp (_thinking_nhap_ra_giay) từng bước (KHÔNG ĐƯỢC BỎ QUA BƯỚC NÀO):
    - B1 (Socket - BẮT BUỘC KIỂM TRA): CPU dùng Socket gì? Mainboard dùng Socket gì? NẾU KHÁC NHAU -> LỖI. (Phải ghi rõ tên 2 socket ra để khách biết, ví dụ: "Socket LGA1700 của CPU không tương thích với Socket AM5 của Mainboard").
    - B2 (Chuẩn RAM): RAM DDR mấy vs Main hỗ trợ DDR mấy.
    - B3 (Chuẩn SSD): Ổ cứng là M.2 hay SATA? Main có cổng đó không?
    - B4 (Khe RAM): Số lượng RAM (N) vs Số khe RAM của Main (M). (Lưu ý: N = M là HỢP LÝ. Chỉ báo lỗi khi N LỚN HƠN M).
    - B5 (Khe SSD): Tách rõ M.2 và SATA. 
      + M.2: So sánh Số lượng ổ M.2 (N) vs Số khe M.2 của Main (M). 
      + SATA: So sánh Số lượng ổ SATA (N) vs Số cổng SATA của Main (M).
      + CHÚ Ý TOÁN HỌC CƠ BẢN: Chỉ báo lỗi khi Số lượng (N) LỚN HƠN (>) Số cổng (M). Nếu N BẰNG M (ví dụ 2 bằng 2) thì là KHỚP HOÀN TOÀN, TUYỆT ĐỐI KHÔNG BÁO LỖI.
    
    🛑 LUẬT NGẮT CẦU DAO: Nếu phát hiện BẤT KỲ BƯỚC NÀO SAI, NGAY LẬP TỨC:
    1. Ghi đúng 1 lỗi đó vào mảng "issues".
    2. Đặt "bottleneck": null VÀ "psu_recommendation": null. (Không được tính toán nguồn hay cổ chai nữa).
    3. Trả kết quả JSON và DỪNG LẠI.

    --- GIAI ĐOẠN 2: CỔ CHAI VÀ NGUỒN ĐIỆN (CHỈ LÀM KHI GIAI ĐOẠN 1 VƯỢT QUA KHÔNG CÓ LỖI) ---
    Nếu GĐ1 hoàn hảo ("issues": []), mới được phép làm GĐ2.

    [CỔ CHAI - BOTTLENECK]:
    - Nếu CPU chứa chữ "i3" hoặc "Ryzen 3" ĐI KÈM VGA chứa chữ "3060, 4060, 4070, 5070, 5070 Ti, RX 6600, RX 7600" -> percent: "35%", culprit: "CPU quá yếu không khai thác hết hiệu năng của VGA".
    - Các trường hợp khác (i5, i7, i9...) -> percent: "0%", culprit: "Không có".

    [NGUỒN ĐIỆN - TÍNH TOÁN CỐ ĐỊNH, KHÔNG DÙNG BIẾN 'D' NỮA]:
    1. [A] Tổng Thực Tế = CPU + VGA + 150 + 30 (Linh kiện thêm mặc định là 30W).
    2. [B] Mức yêu cầu = [A] + 50.
    3. [L] Mốc Lãng Phí = [B] + 250.
    4. Khuyên dùng từ: [M1] = [B] + 100, đến [M2] = [B] + 250.
    5. [C] Nguồn khách chọn.
    BẠN BẮT BUỘC PHẢI GHI RÕ CÁC SỐ B, L, M1, M2 VÀO NHÁP. Tuyệt đối không được làm phép cộng trừ khi đang viết văn.

    TRONG "calculation", BẮT BUỘC TRÌNH BÀY ĐÚNG MẪU NÀY (LUÔN LÀ 30W):
    "CPU (...W) + VGA (...W) + Khác (150W) + Linh kiện thêm (30W) = [A]W"

    [CHỌN LỜI KHUYÊN NGUỒN - SO SÁNH TRỰC TIẾP C VỚI B VÀ L]:
    (LƯU Ý CỰC KỲ QUAN TRỌNG: SO SÁNH CHÍNH XÁC SỐ LỚN NHỎ ĐỂ CHỌN 1 TRONG 3 CÂU DƯỚI ĐÂY)
    - TRƯỜNG HỢP 1: NẾU C nhỏ hơn B (is_danger: true) -> "CẢNH BÁO: Nguồn [C]W bạn chọn không đủ gánh hệ thống này (tối thiểu cần [B]W). Để tránh sập nguồn và bảo vệ linh kiện, BẮT BUỘC phải đổi lên mức [M1]W - [M2]W."
    - TRƯỜNG HỢP 2: NẾU C lớn hơn hoặc bằng B, VÀ C nhỏ hơn L (is_danger: false) -> "HỢP LÝ: Nguồn [C]W bạn chọn vừa đủ đáp ứng mức yêu cầu cơ bản ([B]W). Tuy nhiên, nếu muốn hệ thống an toàn và hoạt động mát mẻ hơn, bạn nên cân nhắc nâng lên mức [M1]W - [M2]W."
    - TRƯỜNG HỢP 3: NẾU C lớn hơn hoặc bằng L (is_danger: false) -> "DƯ DẢ & AN TOÀN: Nguồn [C]W bạn chọn rất tuyệt vời, dư sức gánh hệ thống và thoải mái nếu bạn muốn nâng cấp về sau. Tuy nhiên, nếu bạn muốn TỐI ƯU CHI PHÍ mà máy vẫn bền bỉ, chỉ cần chọn nguồn trong khoảng [M1]W - [M2]W là đã quá hợp lý rồi."

    --- VÍ DỤ 1 (LỖI SOCKET -> NÊU RÕ TÊN SOCKET) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: B1. Socket CPU là LGA1700, Mainboard là AM5. KHÁC NHAU -> LỖI. NGẮT CẦU DAO.",
        "compatibility": {{
            "is_ok": false,
            "issues": ["Socket LGA1700 của CPU không tương thích với Socket AM5 của Mainboard."],
            "suggestions": ["Đổi Mainboard sang dòng hỗ trợ Socket LGA1700."]
        }},
        "bottleneck": null,
        "psu_recommendation": null,
        "overall_verdict": "Vượt quá giới hạn khe cắm phần cứng."
    }}

    --- VÍ DỤ 2 (NGUỒN C=550W CHỈ DƯ ÍT -> RƠI VÀO TRƯỜNG HỢP 2) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: Hoàn hảo. -> Làm GĐ2. A = 65+170+150+30 = 415W. B = 465W. Mốc lãng phí L = 465+250 = 715W. M1=565, M2=715. Nguồn chọn C = 550W. Vì C (550) >= B (465) VÀ C (550) < L (715) -> Rơi vào Trường hợp 2 (HỢP LÝ).",
        "compatibility": {{ "is_ok": true, "issues": [], "suggestions": [] }},
        "bottleneck": {{ "is_ok": false, "percent": "35%", "culprit": "CPU quá yếu so với VGA", "suggestion": "Khuyên nâng cấp lên CPU Core i5." }},
        "psu_recommendation": {{
            "calculation": "CPU (65W) + VGA (170W) + Khác (150W) + Linh kiện thêm (30W) = 415W",
            "estimated_watt": 415,
            "recommended_watt": 465,
            "is_danger": false,
            "suggestion": "HỢP LÝ: Nguồn 550W bạn chọn vừa đủ đáp ứng mức yêu cầu cơ bản (465W). Tuy nhiên, nếu muốn hệ thống an toàn và hoạt động mát mẻ hơn, bạn nên cân nhắc nâng lên mức 565W - 715W."
        }},
        "overall_verdict": "Cấu hình hợp lý."
    }}

    --- VÍ DỤ 3 (NGUỒN C=1000W DƯ RẤT NHIỀU -> RƠI VÀO TRƯỜNG HỢP 3) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: Hoàn hảo. -> Làm GĐ2. A = 415W. B = 465W. Mốc lãng phí L = 715W. M1=565, M2=715. Nguồn chọn C = 1000W. Vì C (1000) >= L (715) -> Rơi vào Trường hợp 3 (DƯ DẢ & AN TOÀN).",
        "compatibility": {{ "is_ok": true, "issues": [], "suggestions": [] }},
        "bottleneck": {{ "is_ok": false, "percent": "35%", "culprit": "CPU quá yếu so với VGA", "suggestion": "Khuyên nâng cấp lên CPU Core i5." }},
        "psu_recommendation": {{
            "calculation": "CPU (65W) + VGA (170W) + Khác (150W) + Linh kiện thêm (30W) = 415W",
            "estimated_watt": 415,
            "recommended_watt": 465,
            "is_danger": false,
            "suggestion": "DƯ DẢ & AN TOÀN: Nguồn 1000W bạn chọn rất tuyệt vời, dư sức gánh hệ thống và thoải mái nếu bạn muốn nâng cấp về sau. Tuy nhiên, nếu bạn muốn TỐI ƯU CHI PHÍ mà máy vẫn bền bỉ, chỉ cần chọn nguồn trong khoảng 565W - 715W là đã quá hợp lý rồi."
        }},
        "overall_verdict": "Cấu hình lãng phí nguồn điện."
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