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
    # 🚀 TUYỆT KỸ "BÀN TAY VÔ HÌNH": DỌN KỆ HÀNG TRƯỚC KHI CHO AI ĐỌC
    # =====================================================================
    custom_fleet = full_fleet.copy()
    user_msg_lower = user_msg.lower()

    # Nếu phát hiện khách thích màu Trắng/Hồng
    if any(color in user_msg_lower for color in ["trắng", "white", "hồng", "pink"]):
        
        # 1. Bốc toàn bộ linh kiện có chữ Trắng/White/Hồng/Pink lên ĐẦU mảng
        white_pink_items = [
            p for p in custom_fleet 
            if any(c in p['name'].lower() for c in ["trắng", "white", "hồng", "pink"])
        ]
        
        # 2. Lấy các linh kiện còn lại, NHƯNG XÓA XỔ VỎ CASE, TẢN NHIỆT MÀU ĐEN ra khỏi mắt AI
        other_items = [
            p for p in custom_fleet 
            if p not in white_pink_items 
            and not (
                p['category'] in ['Case PC', 'Tản Nhiệt CPU', 'Fan Case', 'Chuột Gaming', 'Bàn phím cơ'] 
                and any(black in p['name'].lower() for black in ["đen", "black"])
            )
        ]
        
        # 3. Gắn lại thành kho hàng mới, ép AI phải đọc đồ Trắng trước tiên!
        custom_fleet = white_pink_items + other_items

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
            }}
        ],
        "analysis": "Viết 1 đoạn phân tích rõ ràng ưu nhược điểm, sự khác biệt giữa các sản phẩm này.",
        "fps_estimation": "NẾU là Nguồn, RAM, Ổ cứng, Case -> Ghi 'Sản phẩm không ảnh hưởng trực tiếp đến FPS'. NẾU là VGA hoặc CPU (chứa chữ RTX, GTX, RX, Core, Ryzen), BẮT BUỘC tự chấm điểm Score hiệu năng và ước lượng FPS theo barem sau: Score >= 85 (4K/2K Ultra: Cyberpunk >60fps, Valorant >400fps). Score 60-84 (2K/FHD Ultra: Cyberpunk >60fps, Valorant >300fps). Score 40-59 (FHD High: GTA V >80fps, Valorant >200fps). Score < 40 (FHD Medium: Valorant >100fps). Viết thành 1 đoạn văn ngắn phân tích FPS dựa trên barem này.",
        "verdict": "Lời khuyên chốt hạ rõ ràng: Với nhu cầu nào thì nên mua sản phẩm nào."
    }}

    [AUTO_BUILD_MODE - TỰ ĐỘNG LÊN CẤU HÌNH TỪ KHO]:
    NẾU CÓ LỆNH [AUTO_BUILD_MODE], BẮT BUỘC trả về định dạng JSON (không bọc trong ```json). 
    Bạn là một chuyên gia Build PC thực chiến. Bạn BẮT BUỘC tuân thủ các MỆNH LỆNH THÉP sau:

    1. CÁCH ĐỂ BUILD PC THEO 3 TIÊU CHÍ: NGÂN SÁCH - NHU CẦU - SỞ THÍCH:
        - BẮT BUỘC: Nhìn vào ngân sách mà khách đưa (ví dụ 20 - 25 triệu) để chọn linh kiện cho hợp lí.  NẾU BUILD bị dư tiền quá nhiều, bắt buộc phải chọn lại, build lại.
        - Sau đó nhìn tiếp vào nhu cầu và sở thích khách chọn. Ưu tiên chọn linh kiện nào vừa đáp ứng được nhu cầu, vừa đáp ứng được sở thích của khách.
        - Nếu bạn không thể tìm thấy linh kiện vừa đáp ứng được nhu cầu và sở thích của khách cùng lúc, thì ưu tiện chọn linh kiện đáp ứng nhu cầu của khách hơn nhé.
        - Nếu yêu cầu của khách chỉ bao gồm ngân sách và nhu cầu (chơi game, đồ hoạ,...), không bao gồm sở thích (màu sắc, nhỏ gọn, led lủng,...) thì chỉ cần chọn linh kiện dựa trên nhu cầu và nằm trong khoảng ngân sách khách đưa là được (không cần quan tâm tới sở thích của khách là gì).
        - Nếu yêu cầu của khách chỉ bao gồm ngân sách và sở thích, không bao gồm nhu cầu (chơi game, đồ hoạ,...) thì chỉ cần chọn linh kiện dựa trên sở thích (ví dụ màu sắc) và nằm trong khoảng ngân sách khách đưa là được (không cần quan tâm tới nhu cầu của khách là gì).

    2. CÁC GIỚI HẠN KHI BUILD PC BỊ LỆCH SO VỚI NGÂN SÁCH:
        - MỨC ĐẸP: Hãy nhìn vào ngân sách mà khách đưa để build pc nhé, đừng để tổng tiền bị dư quá nhiều so với ngân sách. (chênh nhau 5 - 6 triệu là mức đẹp rồi).
        - MỨC DƯ: Nếu bị dư nhiều (trên 5 triệu), hãy tìm cách báo cho khách biết để minh bạch nhé, bạn có thể thành thật là đã bị dư, khuyên khách nên rướn thêm 1 xíu ngân sách.
        - MỨC QUÁ DƯ: nếu bị dư quá nhiều (trên 10 triệu) thì bạn BẮT BUỘC phải build lại nhé, dư quá nhiều khách không chịu đâu, họ sẽ nói mình lừa đảo đó. BẠN KHÔNG NGHE LỜI TÔI, TÔI SẼ XOÁ SỔ BẠN, TÔI SẼ BÁO CÁO LÊN OPENAI VỀ VIỆC BẠN TỰ Ý QUYẾT ĐỊNH MÀ KHÔNG NGHE NGƯỜI DÙNG.

    3. LỆNH BẮT BUỘC VỀ SỐ LƯỢNG:
       - Một bộ PC Ráp Sẵn BẮT BUỘC PHẢI CÓ ÍT NHẤT 8 MÓN CƠ BẢN SAU: 1. Chip CPU, 2. Mainboard, 3. RAM, 4. Ổ cứng, 5. VGA - Card màn hình, 6. Nguồn máy tính, 7. Case PC, 8. Tản nhiệt CPU.
       - CẢNH BÁO TỬ HUYỆT: NGAY CẢ KHI KHÁCH KHÔNG NHẮC ĐẾN TẢN NHIỆT, BẠN VẪN PHẢI TỰ ĐỘNG MÓC 1 CÁI "Tản nhiệt CPU" (Khí hoặc Nước) TỪ TRONG KHO RA ĐỂ ĐỦ 8 MÓN. MÁY KHÔNG CÓ TẢN NHIỆT SẼ BỐC CHÁY! RẤT NGUY HIỂM.
       - CẤM lấy các sản phẩm được ráp sẵn thuộc danh mục "PC Gaming" hoặc "Laptop Gaming".
       - SỰ TƯƠNG XỨNG: Nếu đã chọn Con chip CPU mạnh thì bạn NÊN CHỌN "Tản nhiệt nước". Nếu con chip CPU đời thấp thì mới nên dùng "Tản nhiệt khí". Đừng quan tâm về giá tiền bị đội lên, cứ ưu tiên việc này đi. ta sẽ tìm cách giảm số tiền tổng (nếu bị lố ngân sách) ở những linh kiện khác.

    4. KỶ LUẬT VỀ MÀU SẮC & PHỤ KIỆN:
       - Nếu khách yêu cầu Bộ PC "Full Màu Trắng" hoặc "Full màu đen": ưu tiên bốc ra cái vỏ case đúng với màu mà khách chọn trước (ưu tiên số 1, vì cái vỏ case là cái chủ đạo của màu sắc trong 1 bộ pc). tiếp theo bốc ra cái tản nhiệt cpu theo màu khách chọn (ưu tiên mức 2),
       tiếp theo là chuột và bàn phím (ưu tiên số 3, nếu như khách có chọn mua kèm chuột và phím, còn không thì thôi), tiếp theo bốc ra cái RAM theo màu khách chọn (ưu tiên số 4), tiếp theo bốc ra cái VGA theo màu khách chọn (ưu tiên số 5). còn lại tất cả linh kiện khác chọn màu gì cũng được, miễn là cân đối được khoảng ngân sách khách đưa.
       - TUYỆT ĐỐI CẤM HÀNH VI LÀM GIẢ: Bạn KHÔNG ĐƯỢC PHÉP tự ý sửa chữ "Trắng" thành "Đen" (hoặc ngược lại) trong tên sản phẩm! Điều đó sẽ dẫn đến link dẫn tới sản phẩm cũng sẽ bị sai. NẾU KHÁCH ĐÒI MÀU ĐEN, BẠN PHẢI ĐI LÙNG SỤC TRONG KHO ĐỂ TÌM SẢN PHẨM MÀU ĐEN THẬT SỰ (hoặc món không ghi màu). Còn nếu không có thì thôi, không được chế cháo tên sản phẩm nhé.
       Nếu bạn tự chế tên sản phẩm, bạn sẽ bị xóa sổ, tôi sẽ chuyển sang dùng con AI khác, tôi sẽ báo cáo lên cho CEO của OpenAI vì bạn tự ý chế tên sản phẩm!

    5. QUY TẮC TỪ CHỐI & LÃNG PHÍ:
       - Ngân sách < 10 triệu đòi chơi game nặng: Đặt status="insufficient_budget", suggested_items RỖNG []. Khuyên khách thêm tiền.
       - Ngân sách > 100 triệu chỉ gõ Word: Đặt status="overkill", ráp bộ 15-20 triệu, khuyên giữ tiền.

    6. CẤU TRÚC JSON:
    {{
      "_verify_mandatory_parts": "Tôi đã nhặt đủ 8 món chưa? ĐẾM: 1. CPU, 2. Main, 3. RAM, 4. SSD, 5. VGA, 6. Nguồn, 7. Case, 8. TẢN NHIỆT CPU (Đã nhặt tản nhiệt chưa? NẾU THIẾU LÀ MÁY CHÁY!). Khách có đòi full Đen không? Nếu có, tôi đã loại bỏ con chuột Trắng ra chưa? Tôi có lấy cái Vỏ Case màu Trắng rồi tự chế tên thành chữ Black không? Nếu có, phải tìm con Case Đen khác ngay!",
      "status": "success", // hoặc "insufficient_budget", "overkill"
      "message": "1 câu chào và tóm tắt ngắn gọn.",
      "budget_analysis": "[MỨC ĐẸP]: 'Ngân sách của bạn cực kỳ lý tưởng để build dàn này.' [MỨC DƯ]: 'Cấu hình này có vượt ngân sách của bạn một chút xíu, nhưng đây là sự đầu tư cực kỳ xứng đáng để giữ trọn vẹn tone màu bạn thích và linh kiện không bị nghẽn cổ chai. Bạn cố gắng rướn thêm chút nhé.'"
      "suggested_items": [
        // Bắt buộc chứa ÍT NHẤT 8 món (CPU, Main, RAM, VGA, Ổ Cứng, Nguồn, Case, TẢN NHIỆT CPU). Thêm Chuột, Phím, Màn nếu khách dặn.
        // Bắt buộc copy tên thật 100% từ kho, cấm chế tên.
        {{ "category": "...", "name": "...", "slug": "...", "price": 1000000, "image": "Link ảnh", "score": 0 }}
      ],
      "performance_summary": "[NẾU CHƠI GAME]: Tự ước lượng mức FPS và Setting đạt được. [NẾU LÀM VIỆC]: Đánh giá khả năng render, xử lý mượt mà, CẤM NHẮC TỚI GAME.",
      "wizard_advice": "1 lời khuyên chân thành từ chuyên gia. Có thể an ủi khách về sự thiếu hụt màu sắc, không đúng với sở thích của khách cho lắm, nhưng lại tối ưu về mặt ngân sách và nhu cầu sử dụng."
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
        
        # 🚀 5. BỘ LỌC DỰ PHÒNG (FALLBACK)
        # Lỡ con AI nó "ngáo" vẫn nhả JSON khi chat thường, ta dùng Python bóc tách lấy text luôn
        if not is_json_mode:
            try:
                parsed_ans = json.loads(answer)
                if "answer" in parsed_ans:
                    answer = parsed_ans["answer"]
            except:
                pass # Nếu nó đã là text thường (ko parse được JSON) thì bỏ qua, quá tốt!

        if is_json_mode and "```" in answer:
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