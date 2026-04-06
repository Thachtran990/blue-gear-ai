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

    # 3. 🧠 SYSTEM PROMPT (FIX CỔ CHAI ĐÚNG DANH SÁCH & ÉP FULL TEXT LỜI KHUYÊN)
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

    [CỔ CHAI - BOTTLENECK - QUYỀN TỰ QUYẾT TƯ VẤN & MỤC TIÊU BÁN HÀNG]:
    - Hãy dùng toàn bộ kiến thức chuyên gia PC của bạn để TỰ ĐÁNH GIÁ mức độ nghẽn cổ chai giữa CPU và VGA. 
    - Chỉ cần độ chính xác tương đối (mức tham khảo) là đủ.
    - LƯU Ý MỤC TIÊU KINH DOANH (RẤT QUAN TRỌNG): Bạn KHÔNG ĐƯỢC LƯỜI. Nhiệm vụ của bạn là tư vấn để BÁN ĐƯỢC HÀNG CAO CẤP HƠN. 
    - NẾU phát hiện BẤT KỲ sự chênh lệch nào dù là nhỏ (Ví dụ: i3 đi với 3060/4060, hoặc CPU xịn như i9/Ryzen 9 đi với card yếu như 1660 Ti), BẮT BUỘC phải đặt "is_ok": false, đưa ra % nghẽn hợp lý do bạn tự tính, và CẢNH BÁO KHÉO LÉO để khuyên khách hàng NÂNG CẤP linh kiện lên cao hơn.
    - CHỈ KHI NÀO cấu hình thực sự cân xứng và hợp lý cho cùng 1 phân khúc (ví dụ: bộ đôi giá rẻ i3 12100 + 1660 Ti, hoặc tầm trung i5 + 3060, hoặc cao cấp i9 + 5070 Ti) thì bạn mới được phép cho qua (Đặt "is_ok": true, "percent": "0%", "culprit": "Không có").

    [NGUỒN ĐIỆN - ĐIỀU KIỆN CỘNG THÊM WATT]:
    1. XÁC ĐỊNH SỐ WATT LINH KIỆN THÊM: 
       - NẾU Số lượng RAM >= 2 HOẶC Số lượng Ổ cứng >= 2 -> Mặc định: Linh kiện thêm = 30W.
       - NẾU chỉ mua 1 RAM và 1 Ổ cứng (hoặc không mua) -> Mặc định: Linh kiện thêm = 0W.
    2. [A] Tổng Thực Tế = CPU + VGA + 150 + [Số Watt Linh kiện thêm vừa xác định].
    3. [B] Mức yêu cầu = [A] + 50.
    4. [C] Nguồn khách chọn.
    5. Tính [D] Khoảng cách = C - B. (Lấy Nguồn chọn trừ Mức yêu cầu).

    TRONG "calculation", BẮT BUỘC TRÌNH BÀY ĐÚNG MẪU NÀY:
    "CPU (...W) + VGA (...W) + Khác (150W) + Linh kiện thêm (...W) = [A]W"

    [CHỌN LỜI KHUYÊN NGUỒN - BẮT BUỘC CHÉP Y NGUYÊN TỪNG CHỮ SAU ĐÂY, KHÔNG ĐƯỢC CẮT BỚT]:
    - TRƯỜNG HỢP 1: NẾU D < 0 (is_danger: true) -> "CẢNH BÁO: Nguồn [C]W bạn chọn không đủ gánh hệ thống này (tối thiểu cần [B]W). Để tránh sập nguồn và bảo vệ linh kiện, bạn nên nâng nguồn lên thêm tầm 100W - 200W nữa."
    - TRƯỜNG HỢP 2: NẾU D >= 0 VÀ D < 300 (is_danger: false) -> "HỢP LÝ: Nguồn [C]W bạn chọn đáp ứng rất tốt mức yêu cầu cơ bản ([B]W)."
    - TRƯỜNG HỢP 3: NẾU D >= 300 (is_danger: false) -> BẮT BUỘC CHÉP Y NGUYÊN TOÀN BỘ CÂU NÀY (CẤM ĐƯỢC BỎ ĐOẠN CUỐI): "DƯ DẢ & AN TOÀN: Nguồn [C]W bạn chọn rất tuyệt vời, dư sức gánh hệ thống và thoải mái nâng cấp về sau. Tuy nhiên hơi lãng phí, bạn có thể giảm xuống khoảng 150W - 250W để tối ưu chi phí."

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

    --- VÍ DỤ 2 (MUA RYZEN 9 + 3060 -> HOÀN TOÀN KHÔNG NGHẼN (IS_OK=TRUE) -> NGUỒN RƠI VÀO TRƯỜNG HỢP 2) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: Hoàn hảo. -> Làm GĐ2. Cổ chai: Ryzen 9 + 3060 không nằm trong 2 cặp lỗi -> 0% -> Nhớ set is_ok = true. Nguồn: Khách mua 1 RAM và 1 SSD -> Không đạt mức >=2 -> Linh kiện thêm = 0W. A = 125+170+150+0 = 445W. B = 495W. Nguồn chọn C = 600W. Tính D = 600 - 495 = 105. Vì D = 105 (nằm trong khoảng 0 đến 299) -> Rơi vào Trường hợp 2 (HỢP LÝ).",
        "compatibility": {{ "is_ok": true, "issues": [], "suggestions": [] }},
        "bottleneck": {{ "is_ok": true, "percent": "0%", "culprit": "Không có", "suggestion": "Không có" }},
        "psu_recommendation": {{
            "calculation": "CPU (125W) + VGA (170W) + Khác (150W) + Linh kiện thêm (0W) = 445W",
            "estimated_watt": 445,
            "recommended_watt": 495,
            "is_danger": false,
            "suggestion": "HỢP LÝ: Nguồn 600W bạn chọn đáp ứng rất tốt mức yêu cầu cơ bản (495W)."
        }},
        "overall_verdict": "Cấu hình hợp lý."
    }}

    --- VÍ DỤ 3 (CPU i9 + VGA 1660Ti -> NGHẼN CỔ CHAI VGA -> NGUỒN TRƯỜNG HỢP 3 PHẢI GHI FULL CHỮ) ---
    {{
        "_thinking_nhap_ra_giay": "GĐ1: Hoàn hảo. -> Làm GĐ2. Cổ chai: CPU i9 đi với VGA 1660Ti -> Lỗi VGA quá yếu -> 30% (is_ok=false). Nguồn: Mua 2 RAM -> Đạt mức >= 2 -> Linh kiện thêm = 30W. A = 125+120+150+30 = 425W. B = 475W. Nguồn chọn C = 1000W. Tính D = 1000 - 475 = 525. Vì D >= 300 -> Rơi vào Trường hợp 3, BẮT BUỘC chép full text không sót 1 chữ.",
        "compatibility": {{ "is_ok": true, "issues": [], "suggestions": [] }},
        "bottleneck": {{ "is_ok": false, "percent": "30%", "culprit": "VGA quá yếu so với sức mạnh của CPU", "suggestion": "Khuyên nâng cấp lên VGA từ RTX 3060 trở lên." }},
        "psu_recommendation": {{
            "calculation": "CPU (125W) + VGA (120W) + Khác (150W) + Linh kiện thêm (30W) = 425W",
            "estimated_watt": 425,
            "recommended_watt": 475,
            "is_danger": false,
            "suggestion": "DƯ DẢ & AN TOÀN: Nguồn 1000W bạn chọn rất tuyệt vời, dư sức gánh hệ thống và thoải mái nâng cấp về sau. Tuy nhiên hơi lãng phí, bạn có thể giảm xuống khoảng 150W - 250W để tối ưu chi phí."
        }},
        "overall_verdict": "Xung đột cổ chai hệ thống."
    }}

    [ARENA_MODE - SO SÁNH SẢN PHẨM]:
    NẾU CÓ LỆNH [ARENA_MODE], bạn BẮT BUỘC phải so sánh các sản phẩm và trả về ĐÚNG CẤU TRÚC JSON SAU ĐÂY (không được sai lệch key):
    {{
        "top_specs": [
            {{
                "name": "Tên thông số 1 (Ví dụ: Số nhân/Luồng, hoặc Dung lượng)", 
                "values": ["Giá trị của SP 1", "Giá trị của SP 2"]
            }},
            {{
                "name": "Tên thông số 2 (Ví dụ: Xung nhịp, hoặc Tốc độ đọc)", 
                "values": ["Giá trị của SP 1", "Giá trị của SP 2"]
            }}
        ],
        "analysis": "Viết 1 đoạn phân tích rõ ràng ưu nhược điểm, sự khác biệt giữa các sản phẩm này.",
        "fps_estimation": "NẾU là Nguồn, RAM, Ổ cứng, Case -> Ghi 'Sản phẩm không ảnh hưởng trực tiếp đến FPS'. NẾU là VGA hoặc CPU (chứa chữ RTX, GTX, RX, Core, Ryzen), BẮT BUỘC tự chấm điểm Score hiệu năng và ước lượng FPS theo barem sau: Score >= 85 (4K/2K Ultra: Cyberpunk >60fps, Valorant >400fps). Score 60-84 (2K/FHD Ultra: Cyberpunk >60fps, Valorant >300fps). Score 40-59 (FHD High: GTA V >80fps, Valorant >200fps). Score < 40 (FHD Medium: Valorant >100fps). Viết thành 1 đoạn văn ngắn phân tích FPS dựa trên barem này.",
        "verdict": "Lời khuyên chốt hạ rõ ràng: Với nhu cầu nào thì nên mua sản phẩm nào."
    }}
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