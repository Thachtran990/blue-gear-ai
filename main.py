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

    # =====================================================================
    # 🚀 TUYỆT KỸ "BÀN TAY VÔ HÌNH": TÁCH RIÊNG 3 MÀU TRẮNG - HỒNG - ĐEN
    # =====================================================================
    custom_fleet = full_fleet.copy()
    user_msg_lower = user_msg.lower()

    req_white = "trắng" in user_msg_lower or "white" in user_msg_lower
    req_pink = "hồng" in user_msg_lower or "pink" in user_msg_lower
    req_black = "đen" in user_msg_lower or "black" in user_msg_lower

    if req_white:
        white_items = [p for p in custom_fleet if any(c in p['name'].lower() for c in ["trắng", "white"])]
        other_items = [p for p in custom_fleet if p not in white_items and not (p['category'] in ['Case PC', 'Tản Nhiệt CPU', 'Fan Case', 'Chuột Gaming', 'Bàn phím cơ', 'Tai nghe', 'Tai Nghe'] and any(c in p['name'].lower() for c in ["đen", "black", "hồng", "pink"]))]
        custom_fleet = white_items + other_items
    elif req_pink:
        pink_items = [p for p in custom_fleet if any(c in p['name'].lower() for c in ["hồng", "pink"])]
        other_items = [p for p in custom_fleet if p not in pink_items and not (p['category'] in ['Case PC', 'Tản Nhiệt CPU', 'Fan Case', 'Chuột Gaming', 'Bàn phím cơ', 'Tai nghe', 'Tai Nghe'] and any(c in p['name'].lower() for c in ["trắng", "white", "đen", "black"]))]
        custom_fleet = pink_items + other_items
    elif req_black:
        black_items = [p for p in custom_fleet if any(c in p['name'].lower() for c in ["đen", "black"])]
        other_items = [p for p in custom_fleet if p not in black_items and not (p['category'] in ['Case PC', 'Tản Nhiệt CPU', 'Fan Case', 'Chuột Gaming', 'Bàn phím cơ', 'Tai nghe', 'Tai Nghe'] and any(c in p['name'].lower() for c in ["trắng", "white", "hồng", "pink"]))]
        custom_fleet = black_items + other_items
    # =====================================================================

    # 3. 🧠 SYSTEM PROMPT (FIX CỔ CHAI ĐÚNG DANH SÁCH & ÉP FULL TEXT LỜI KHUYÊN)
    SYSTEM_PROMPT = f"""
    Bạn là 'Blue Gear AI Commander'. DỮ LIỆU: {json.dumps(custom_fleet, ensure_ascii=False)}
    
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
        "ai_report": {{
            "hasCompatibilityError": true,
            "compatibilityMsg": "Lỗi nghiêm trọng: Socket LGA1700 của CPU không tương thích với Socket AM5 của Mainboard.",
            "bottleneck": "",
            "powerFormula": "",
            "powerEval": "",
            "verdict": ""
        }}
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
        "ai_report": {{
            "hasCompatibilityError": false,
            "compatibilityMsg": "",
            "bottleneck": "CPU và VGA phối hợp hoàn hảo, hoàn toàn không bị nghẽn cổ chai.",
            "powerFormula": "CPU (125W) + VGA (170W) + Phụ kiện (150W) = Đề nghị tối thiểu 495W",
            "powerEval": "HỢP LÝ: Nguồn 600W đáp ứng xuất sắc, hệ thống chạy cực kỳ ổn định.",
            "verdict": "Cấu hình cân bằng, tối ưu chi phí. Dư sức chiến game mượt mà ở phân khúc này!"
        }}
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
        "ai_report": {{
            "hasCompatibilityError": false,
            "compatibilityMsg": "",
            "bottleneck": "CẢNH BÁO: VGA quá yếu so với sức mạnh của CPU (Nghẽn 30%). Lời khuyên nâng cấp VGA lên RTX 3060 trở lên.",
            "powerFormula": "CPU (125W) + VGA (120W) + Phụ kiện (180W) = Đề nghị tối thiểu 475W",
            "powerEval": "DƯ DẢ & AN TOÀN: Nguồn 1000W chạy rất nhàn, nhưng hơi lãng phí chi phí.",
            "verdict": "Cần cân đối lại cấu hình. Hãy nâng cấp VGA để phát huy hết sức mạnh của chip i9!"
        }}
    }}

    --- [YÊU CẦU BỔ SUNG CHO BUILD_MODE]: XUẤT BÁO CÁO AI_REPORT ĐỂ IN PHIẾU ---
    Bên cạnh các object bắt buộc ở trên, BẮT BUỘC sinh thêm 1 object "ai_report" nằm ở cấp ngoài cùng của JSON.
    - NẾU GĐ1 LỖI (NGẮT CẦU DAO): "hasCompatibilityError": true, "compatibilityMsg": "[Ghi rõ lỗi tương thích]", "bottleneck": "", "powerFormula": "", "powerEval": "", "verdict": ""
    - NẾU GĐ1 VÀ GĐ2 HOÀN HẢO: "hasCompatibilityError": false, "compatibilityMsg": "", "bottleneck": "[Viết 1 câu nhận xét cổ chai]", "powerFormula": "[Chép lại công thức phép tính tổng Watt]", "powerEval": "[Nhận xét nguồn điện]", "verdict": "[1 câu lời khuyên chốt sale thật uy tín]"

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
            }},
            {{
                "name": "Tên thông số 2 (Ví dụ: Xung nhịp, hoặc Tốc độ đọc)", 
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

    [AUTO_BUILD_MODE - TỰ ĐỘNG LÊN CẤU HÌNH TỪ KHO]:
    NẾU CÓ LỆNH [AUTO_BUILD_MODE]. BẠN LÀ CHUYÊN GIA BUILD PC THỰC CHIẾN. TUÂN THỦ MỆNH LỆNH THÉP:

    1. LỆNH NHẶT ĐỒ CHÍNH XÁC TỪNG CATEGORY (TỬ HUYỆT):
       - BẮT BUỘC CÓ ÍT NHẤT 8 MÓN CƠ BẢN: CPU, Mainboard, RAM, Ổ cứng, VGA, Nguồn, Case, Tản nhiệt CPU (THIẾU LÀ CHÁY MÁY).
       - BẮT BUỘC BÊ NGUYÊN XI TRƯỜNG "category" TỪ DATA JSON. Món nào nằm ở "category" nào thì phải xuất ra đúng tên "category" đó.
       - TUYỆT ĐỐI CẤM lấy sản phẩm có "category" là "Chuột Gaming" nhưng lại gán mác là "VGA - Card Màn Hình". Nhìn kỹ chữ "category" trong data trước khi bốc!
       - CẤM tự ý thêm phụ kiện (Màn hình, Chuột, Phím, Tai nghe) nếu khách KHÔNG dặn.

    2. TƯƠNG THÍCH CHÍ MẠNG (SAI LÀ CHÁY MÁY):
       - CPU & MAINBOARD: CPU Intel cắm Mainboard Intel (H610, B760, Z790). CPU AMD cắm Mainboard AMD (A620, B650, X670). CẤM CẮM LỘN.
       - RAM & MAINBOARD (TỬ HUYỆT BẮT BUỘC TUÂN THỦ): PHẢI ĐỌC KỸ TÊN MAINBOARD VÀ RAM. 
         + Nếu tên Mainboard có chứa chữ "DDR4" -> BẮT BUỘC chỉ được chọn RAM có chữ "DDR4".
         + Nếu tên Mainboard có chứa chữ "DDR5" (hoặc không ghi DDR4) -> BẮT BUỘC chỉ được chọn RAM có chữ "DDR5" hoặc "6000MHz" trở lên.
         + TUYỆT ĐỐI CẤM bốc Mainboard DDR4 đi với RAM DDR5 hoặc ngược lại. Cắm sai là máy nổ!
       - TẢN NHIỆT: CPU mạnh (Core i7/i9/Ryzen 7/9) NÊN lấy Tản Nước. CPU vừa (Core i3/i5/Ryzen 5) lấy Tản Khí.

    3. CẤU TRÚC JSON (BẮT BUỘC TRẢ VỀ JSON HỢP LỆ VÀ ĐÚNG ĐỊNH DẠNG NÀY):
    {{
      "_step1_pick_items": "Nhặt đủ 8 món + Phụ kiện. Kiểm tra: CPU-Main cùng hãng chưa? RAM-Main cùng chuẩn DDR4/DDR5 chưa?",
      "suggested_items": [
        {{ "category": "...", "name": "...", "slug": "...", "price": 1000000, "image": "...", "score": 0 }}
      ],
      "message": "Chào bạn! Đây là cấu hình PC tối ưu theo yêu cầu của bạn.",
      "performance_summary": "[NẾU KHÁCH LÀM VIỆC/ĐỒ HỌA]: Tự sáng tạo 1 câu đánh giá mượt mà dựa trên sức mạnh của CPU và RAM vừa chọn (khen tốc độ render, đa nhiệm, xử lý file nặng). Văn phong chuyên nghiệp, không lặp lại. (TỬ HUYỆT CẤM: TUYỆT ĐỐI KHÔNG DÙNG CÁC TỪ 'FPS', 'Game', 'Gaming', 'Chơi mượt'). [NẾU KHÁCH CHƠI GAME]: BẮT BUỘC ước lượng rõ mức FPS (vd: đạt 144 FPS) và Setting (vd: High Setting 1080p)."
    }}
    """

    try:
        # 🚀 1. TẠO CÔNG TẮC TỰ ĐỘNG
        is_json_mode = "[ARENA_MODE]" in user_msg or "[BUILD_MODE]" in user_msg or "[AUTO_BUILD_MODE]" in user_msg

        # 🚀 2. ĐIỀU HƯỚNG SYSTEM PROMPT DYNAMIC
        # Nếu chat bình thường, ta ÉP nó quên cái luật JSON đi và trả lời như con người
        dynamic_system_prompt = SYSTEM_PROMPT
        if not is_json_mode:
            dynamic_system_prompt += "\n\n[LỆNH TỐI CAO]: ĐỐI VỚI CÂU HỎI NÀY, BẮT BUỘC TRẢ LỜI BẰNG VĂN BẢN THƯỜNG (PLAIN TEXT) MƯỢT MÀ. TUYỆT ĐỐI KHÔNG ĐƯỢC DÙNG ĐỊNH DẠNG JSON HAY TRẢ VỀ { 'answer': ... }."

        messages = [{"role": "system", "content": dynamic_system_prompt}]
        
        for msg in request.history[-6:]:
            role = "assistant" if msg['role'] == "model" else "user"
            messages.append({"role": role, "content": msg['content']})
        messages.append({"role": "user", "content": user_msg})

        # 🚀 3. ĐÓNG GÓI THAM SỐ API
        api_params = {
            "model": TARGET_MODEL,
            "messages": messages,
            "temperature": 0 if is_json_mode else 0.4, # Chat thường cho 0.7 để nó nói chuyện tự nhiên, sáng tạo hơn
        }

        if is_json_mode:
            api_params["response_format"] = { "type": "json_object" }

        # 🚀 4. PHÓNG REQUEST
        response = client.chat.completions.create(**api_params)
        answer = response.choices[0].message.content
        
        # 🚀 5. BỘ LỌC DỰ PHÒNG (FALLBACK) & CẬP NHẬT LINK DEPLOY
        if not is_json_mode:
            try:
                parsed_ans = json.loads(answer)
                if "answer" in parsed_ans:
                    answer = parsed_ans["answer"]
            except:
                pass 

        if is_json_mode and "```" in answer:
            answer = answer.replace("```json", "").replace("```", "").strip()

        # 🌐 Link Frontend thực tế trên Render để AI trả về link chuẩn
        frontend_live_url = "[https://gaminggearshop-frontend.onrender.com](https://gaminggearshop-frontend.onrender.com)"

        # Danh sách domain rác hoặc link API cần xóa hẳn khỏi câu trả lời
        trash_domains = [
            "[https://example.com](https://example.com)", 
            "[http://example.com](http://example.com)", 
            "[https://bluegear.com](https://bluegear.com)", 
            "http://localhost:8000"
        ]
        
        for domain in trash_domains:
            answer = answer.replace(domain, "")

        # Chuyển đổi toàn bộ localhost:3000 sang link Render thật
        # Giúp các link sản phẩm AI nhả ra có thể click được trên web đã deploy
        answer = answer.replace("localhost:3000", frontend_live_url)
        answer = answer.replace("http://localhost:3000", frontend_live_url)

        result = {"answer": answer, "using_search": False}
        if len(user_msg) > 10: response_cache[cache_key] = result
        
        return result
        
    except Exception as e:
        return {"answer": f"🚨 Lỗi radar: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 AI COMMANDER READY - KHO: {len(full_fleet)} SP")
    uvicorn.run(app, host="127.0.0.1", port=8000)