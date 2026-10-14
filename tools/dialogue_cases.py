"""Multi-turn conversations, written the way Vietnamese customers actually talk.

The single-turn suite (`chat_cases.py`) asks whether one message is understood.
This one asks whether a *conversation* is: whether what the customer said in
turn two changes what the assistant believes, and whether the assistant shows
that it heard. It was written after a customer sent an air conditioner that was
not cooling, was told to clean it, said it had just been cleaned, and was told
to clean it again.

Each dialogue is a list of customer turns and what must hold after the last:

    must_not    faults the customer ruled out. None of them may appear among
                the suspected faults of the final answer. This is the hard
                rule: repeating what the customer just denied is the failure
                this suite exists for.

    expect_any  faults any one of which is a correct leader once the ruled-out
                ones are gone. Optional: some conversations rule one thing out
                without settling what is left.

    via         "diagnose" or "ask" for the final turn, matching the two routes
                the web client uses (a statement goes to diagnosis, a question to
                the advisory chat).

The voices are deliberately varied: an older northerner who writes "ạ" after
every sentence, a southern student in teencode with no diacritics, someone from
Huế writing "răng" and "rứa", a man who is angry, a woman who tells the whole
story, a technician who uses the part names, someone who types one word per
message. `persona`, `region` and `style` are labels for reading the results;
the pipeline never sees them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Dialogue:
    device: str
    turns: List[str]
    must_not: List[str] = field(default_factory=list)
    expect_any: List[str] = field(default_factory=list)
    via: str = "diagnose"
    persona: str = ""
    region: str = ""
    style: str = ""
    note: str = ""
    must_keep: List[str] = field(default_factory=list)
    """Faults that must *not* be ruled out: "chưa vệ sinh", "có nên vệ sinh
    không" and a new symptom are not exclusions, and reading them as one throws
    away the right answer."""
    deny_last: bool = False
    """The last turn rejects whatever the answer before it led with."""
    seed_device: bool = True
    """Start as if a photograph had identified the appliance; False to make the
    service find it in the text."""
    category: str = ""
    keep_top: bool = False
    """The fault leading before the last turn must still lead after it: "đúng
    rồi", "cảm ơn em", a question about price or danger change nothing."""
    expect_device: str = ""
    """The appliance the conversation must be about after the last turn."""
    expect_top3: List[str] = field(default_factory=list)
    """At least one of these must be among the three faults ranked first."""
    expect_urgent: bool = False
    """The answer must carry HIGH urgency: a safety fault was described."""
    expect_status: str = ""
    """The status the last answer must carry, e.g. "out_of_scope"."""


D = Dialogue

DIALOGUES: List[Dialogue] = [
    # =====================================================================
    # MÁY LẠNH / ĐIỀU HOÀ — the case that started this
    # =====================================================================
    D("air_conditioner",
      ["máy lạnh nhà mình không mát", "mới vệ sinh tuần trước rồi mà, không thể do bẩn được"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT", "AC_OUTDOOR_FAN_MOTOR"],
      persona="khách bình thường", region="nam", style="có dấu", note="ví dụ của PO"),
    D("air_conditioner",
      ["máy lạnh nhà mình không mát", "mới vệ sinh tuần trước rồi mà", "vậy giờ là bị gì, nên gọi dịch vụ nào"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT"], via="ask",
      persona="khách bình thường", region="nam", note="hỏi tiếp bằng câu hỏi"),
    D("air_conditioner",
      ["Chào cháu, điều hòa nhà bác mấy hôm nay chạy mà không mát ạ",
       "Bác vừa gọi thợ bảo dưỡng hôm thứ bảy rồi cháu ạ, thợ bảo lưới lọc sạch sẽ cả"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT", "AC_OUTDOOR_FAN_MOTOR"],
      persona="người lớn tuổi lễ phép", region="bac", style="có dấu"),
    D("air_conditioner",
      ["may lanh nha e k mat ad oi", "e moi ve sinh may r ma", "z la bi j v ad"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT"], via="ask",
      persona="giới trẻ", region="nam", style="không dấu teencode"),
    D("air_conditioner",
      ["mlanh nhà t hông mát gì hết trơn á", "vs rồi nha, hông phải dơ đâu", "dị là sao"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT"], via="ask",
      persona="miền nam xuề xoà", region="nam", style="phương ngữ"),
    D("air_conditioner",
      ["Điều hòa nhà tui răng mà không mát rứa", "tui mới rửa lưới lọc hôm qua rồi, sạch bong"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT"],
      persona="miền trung", region="trung", style="phương ngữ"),
    D("air_conditioner",
      ["BỰC MÌNH QUÁ, MÁY LẠNH MỚI MUA CÓ 1 NĂM MÀ GIỜ KHÔNG MÁT", "VỆ SINH RỒI, ĐỪNG BẢO VỆ SINH NỮA"],
      must_not=["AC_DIRTY_FILTER"], persona="khách nóng tính", region="chung", style="viết hoa"),
    D("air_conditioner",
      ["máy lạnh inverter 1.5HP chạy 16 độ cả tiếng phòng vẫn 30 độ, dàn lạnh gió ra yếu và không lạnh",
       "filter với dàn lạnh e đã xịt rửa sạch rồi, cục nóng quạt vẫn quay bình thường"],
      must_not=["AC_DIRTY_FILTER", "AC_OUTDOOR_FAN_MOTOR"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT", "AC_INDOOR_FAN_MOTOR"],
      persona="người rành kỹ thuật", region="chung", style="thuật ngữ"),
    D("air_conditioner",
      ["điều hoà không mát", "đã vệ sinh", "đã kiểm tra remote vẫn bật tắt được bình thường"],
      must_not=["AC_DIRTY_FILTER", "AC_REMOTE_FAULT"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT", "AC_OUTDOOR_FAN_MOTOR", "AC_DRAIN_BLOCKED"],
      persona="người ít chữ", region="bac", style="cụt lủn"),
    D("air_conditioner",
      ["máy lạnh không lạnh", "không phải đâu"],
      must_not=[], persona="khách bác thẳng", note="bác lại chẩn đoán vừa đưa mà không nói tên nguyên nhân"),
    D("air_conditioner",
      ["máy lạnh không mát, có chảy nước không em?", "dạ không có chảy nước gì hết, chỉ không mát thôi"],
      must_not=[], expect_any=["AC_LOW_REFRIGERANT", "AC_DIRTY_FILTER", "AC_ICING", "AC_CAPACITOR"],
      persona="khách trả lời câu hỏi", region="nam", note="phủ định triệu chứng: nghẹt thoát nước không được đứng đầu"),
    D("air_conditioner",
      ["máy lạnh kêu to quá", "à không, kêu ở cục nóng chứ dàn lạnh êm ru à"],
      must_not=["AC_NOISY_INDOOR"], persona="khách sửa lời", region="nam"),
    D("air_conditioner",
      ["em ơi máy lạnh nhà chị chảy nước tong tong xuống sàn",
       "chị gọi người thông ống thoát nước rồi mà vẫn chảy"],
      must_not=["AC_DRAIN_BLOCKED"], persona="người kể chuyện", region="nam"),
    D("air_conditioner",
      ["máy lạnh bật không lên, bấm remote không ăn", "thay pin remote rồi mà vẫn không được"],
      must_not=[], expect_any=["AC_REMOTE_FAULT", "AC_PCB_FAULT"], persona="khách bình thường", region="nam",
      note="thay pin không loại được hỏng remote: không được loại nhầm"),
    D("air_conditioner",
      ["điều hoà chạy được 10 phút là tắt", "không phải do điện đâu, mấy cái khác vẫn chạy"],
      must_not=[], persona="khách bình thường", region="bac", note="không có lỗi nào bị loại nhầm"),
    D("air_conditioner",
      ["máy lạnh không mát, chắc do bẩn quá"],
      must_not=[], expect_any=["AC_DIRTY_FILTER", "AC_LOW_REFRIGERANT"],
      persona="khách tự đoán", note="khách đổ lỗi cho bẩn, không được hiểu là phủ định"),
    D("air_conditioner",
      ["máy lạnh không mát", "lâu lắm rồi chưa vệ sinh lần nào luôn"],
      must_not=[], expect_any=["AC_DIRTY_FILTER", "AC_LOW_REFRIGERANT"],
      persona="khách thật thà", note="chưa vệ sinh là bằng chứng ủng hộ lỗi bẩn"),
    D("air_conditioner",
      ["máy lạnh không mát", "có nên vệ sinh không em"],
      must_not=[], persona="khách hỏi ý kiến", via="ask", note="hỏi có nên vệ sinh không phải là đã vệ sinh"),
    D("air_conditioner",
      ["máy lạnh không mát", "em không biết có phải hết gas không ạ"],
      must_not=[], expect_any=["AC_LOW_REFRIGERANT"], persona="khách tự đoán", via="ask",
      note="nghi ngờ của khách là manh mối"),
    D("air_conditioner",
      ["máy lạnh không mát, dàn lạnh đóng tuyết trắng xoá", "mới vệ sinh rồi"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_ICING", "AC_LOW_REFRIGERANT"], persona="khách bình thường"),
    D("air_conditioner",
      ["KHOONG MATS GIF HEETS", "VEE SINH ROOIF"],
      must_not=["AC_DIRTY_FILTER"], persona="gõ Telex lỗi", style="telex chưa chuyển", note="đầu tiên là máy lạnh"),
    D("air_conditioner",
      ["máy lạnh khônggggg mátttt 😭😭", "vệ sinh rồi mà 😤"],
      must_not=["AC_DIRTY_FILTER"], persona="giới trẻ", style="kéo dài chữ + emoji"),
    D("air_conditioner",
      ["điều hòa nhà mình không mát lắm mặc dù đã vệ sinh cách đây 2 tuần"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT", "AC_OUTDOOR_FAN_MOTOR"],
      persona="khách nói gọn trong một câu", region="bac"),
    D("air_conditioner",
      ["máy lạnh nhà mình mới lắp tháng trước mà không mát, máy còn mới tinh"],
      must_not=["AC_DIRTY_FILTER"], persona="máy mới", note="máy mới tinh thì không do bẩn"),
    D("air_conditioner",
      ["máy lạnh không mát", "mình vừa bảo dưỡng tuần trước, lưới lọc sạch"],
      must_not=["AC_DIRTY_FILTER"], expect_any=["AC_LOW_REFRIGERANT", "AC_ICING", "AC_CAPACITOR", "AC_COMPRESSOR_FAULT", "AC_OUTDOOR_FAN_MOTOR", "AC_DRAIN_BLOCKED", "AC_REMOTE_FAULT"],
      persona="khách bình thường", note="câu làm BM25 xếp lỗi bẩn lên đầu trước khi sửa"),

    # =====================================================================
    # TỦ LẠNH
    # =====================================================================
    D("refrigerator",
      ["tủ lạnh ngăn mát không lạnh", "cửa đóng kín mà, gioăng còn tốt"],
      must_not=["FRIDGE_DOOR_GASKET"], persona="khách bình thường", region="nam"),
    D("refrigerator",
      ["tủ lạnh ngăn đá đóng tuyết dày, ngăn mát không lạnh", "em rã đông thủ công rồi mà vài hôm lại đóng"],
      must_not=[], expect_any=["FRIDGE_DEFROST_FAULT", "FRIDGE_FAN_FAULT"], persona="người kể chuyện",
      note="rã đông tay không loại được lỗi xả đá: phải giữ"),
    D("refrigerator",
      ["tủ lạnh kêu to ban đêm", "không phải tủ đâu, là quạt dàn lạnh kêu, còn block chạy êm"],
      must_not=[], persona="người rành kỹ thuật"),
    D("refrigerator",
      ["tu lanh nha minh khong lanh nua", "minh moi thay gioang cua thang truoc"],
      must_not=["FRIDGE_DOOR_GASKET"], persona="giới trẻ", style="không dấu"),
    D("refrigerator",
      ["tủ lạnh tắt đèn bên trong", "thay bóng đèn mới rồi vẫn không sáng"],
      must_not=["FRIDGE_LIGHT_FAULT"], persona="khách bình thường", note="đã thay bóng: lỗi bóng loại"),
    D("refrigerator",
      ["Cái tủ lạnh nhà bác chảy nước ra sàn cháu ạ", "Bác thông cái lỗ thoát nước rồi mà vẫn chảy"],
      must_not=["FRIDGE_DRAIN_BLOCKED"], persona="người lớn tuổi", region="bac"),

    # =====================================================================
    # MÁY GIẶT
    # =====================================================================
    D("washing_machine",
      ["máy giặt có mùi hôi", "mới vệ sinh lồng giặt tuần trước rồi mà vẫn hôi"],
      must_not=["WM_SMELL_MOLD"], persona="khách bình thường"),
    D("washing_machine",
      ["máy giặt rò nước ở cửa", "mới thay gioăng cửa rồi"],
      must_not=["WM_DOOR_SEAL_LEAK"], persona="khách bình thường"),
    D("washing_machine",
      ["mg nhà e k vắt dc", "e chia đều đồ r mà vẫn k vắt"],
      must_not=[], expect_any=["WM_NO_SPIN", "WM_MOTOR_FAULT", "WM_DRAIN_PUMP"], persona="giới trẻ", style="teencode",
      note="chia đều đồ không loại được hỏng dây curoa (cùng mã lỗi)"),
    D("washing_machine",
      ["máy giặt không xả được nước", "thay bơm xả mới rồi đó"],
      must_not=["WM_DRAIN_PUMP"], persona="khách bình thường"),
    D("washing_machine",
      ["máy giặt kêu rầm rầm khi vắt", "không phải do lệch đồ đâu, chỉ giặt có cái áo"],
      must_not=[], persona="khách bình thường", note="lệch tải chỉ là một phần của WM_NO_SPIN, không loại"),

    # =====================================================================
    # MÁY NƯỚC NÓNG / BÌNH NÓNG LẠNH
    # =====================================================================
    D("water_heater",
      ["bình nóng lạnh không nóng", "thay thanh đốt mới rồi vẫn không nóng"],
      must_not=["WH_HEATING_ELEMENT"], expect_any=["WH_THERMOSTAT"], persona="khách bình thường", region="bac"),
    D("water_heater",
      ["máy nước nóng ra nước đục, nóng yếu", "mới súc rửa bình hồi tháng trước"],
      must_not=["WH_SCALE_BUILDUP"], persona="khách bình thường", region="nam"),
    D("water_heater",
      ["bình nóng lạnh nhảy aptomat", "không có rò điện đâu em, thử bút thử điện rồi"],
      must_not=[], persona="khách tự kiểm", note="rò điện là lỗi an toàn, không được loại vì lời khách"),

    # =====================================================================
    # BẾP GAS / BẾP TỪ
    # =====================================================================
    D("gas_stove",
      ["bếp gas lửa đỏ, cháy không đều", "mình vệ sinh đầu đốt rồi mà vẫn đỏ"],
      must_not=["STOVE_BURNER_CLOGGED"], persona="khách bình thường"),
    D("gas_stove",
      ["bếp gas nhà mình có mùi gas", "không có mùi gas đâu, chỉ là lửa yếu"],
      must_not=[], persona="khách sửa lời", note="rò gas không được loại vì lời khách"),
    D("gas_stove",
      ["bếp ga lửa yếu cả 2 bếp", "mới thay van điều áp hôm qua"],
      must_not=["STOVE_REGULATOR"], persona="khách bình thường", region="nam"),
    D("induction_hob",
      ["bếp từ không lên nguồn", "à không, vẫn sáng đèn, chỉ là bấm cảm ứng không ăn"],
      must_not=["HOB_NO_POWER"], expect_any=["HOB_TOUCH_FAULT"], persona="khách sửa lời"),
    D("induction_hob",
      ["bếp từ báo lỗi E1", "mặt kính còn nguyên, không nứt gì đâu"],
      must_not=["HOB_GLASS_CRACKED"], persona="khách bình thường"),

    # =====================================================================
    # ẤM ĐUN / LÒ VI SÓNG / LÒ NƯỚNG
    # =====================================================================
    D("kettle",
      ["ấm siêu tốc đun lâu sôi", "mới tẩy cặn bằng giấm hôm qua rồi"],
      must_not=["KETTLE_SCALE"], persona="khách bình thường"),
    D("kettle",
      ["ấm siêu tốc sôi không tự ngắt", "không phải do cặn đâu, ấm còn sạch"],
      must_not=["KETTLE_SCALE"], expect_any=["KETTLE_THERMOSTAT"], persona="khách bình thường"),
    D("microwave_oven",
      ["lò vi sóng không nóng thức ăn", "mâm vẫn quay, đèn vẫn sáng bình thường"],
      must_not=["MW_TURNTABLE_MOTOR", "MW_NO_POWER"], expect_any=["MW_MAGNETRON"], persona="khách tả kỹ"),
    D("oven",
      ["lò nướng không nóng", "mới thay thanh nhiệt hôm thứ hai"],
      must_not=["OVEN_HEATING_ELEMENT"], persona="khách bình thường"),

    # =====================================================================
    # QUẠT
    # =====================================================================
    D("electric_fan",
      ["quạt điện quay yếu, kêu rè rè", "tra dầu rồi mà vẫn kêu"],
      must_not=["FAN_WORN_BEARING"], expect_any=["FAN_CAPACITOR", "FAN_MOTOR_BURNT"], persona="khách bình thường"),
    D("electric_fan",
      ["quạt cây không quay, chỉ ù ù", "thay tụ mới rồi"],
      must_not=["FAN_CAPACITOR"], persona="khách bình thường"),
    D("electric_fan",
      ["quạt điện quạt không tuốc năng"],
      must_not=[], expect_any=["FAN_OSCILLATION_FAULT"], persona="người ít chữ",
      note="không tuốc năng là triệu chứng, không phải phủ định nguyên nhân"),
    D("ceiling_fan",
      ["quạt trần lắc mạnh", "thợ vừa siết lại bộ treo rồi mà vẫn lắc"],
      must_not=["CEILFAN_MOUNT_LOOSE"], persona="khách bình thường"),

    # =====================================================================
    # ĐIỆN, ĐÈN, Ổ CẮM
    # =====================================================================
    D("light_bulb",
      ["đèn phòng ngủ không sáng", "thay bóng mới rồi vẫn không sáng"],
      must_not=["LIGHT_BULB_DEAD"], expect_any=["LIGHT_SWITCH_FAULT"], persona="khách bình thường"),
    D("light_bulb",
      ["den phong khach khong sang nua", "thay bong roi ma van z"],
      must_not=["LIGHT_BULB_DEAD"], persona="giới trẻ", style="không dấu"),
    D("power_outlet",
      ["ổ cắm cắm vào không có điện", "cắm cái khác vẫn chạy mà"],
      must_not=["OUTLET_NO_POWER"], persona="khách tự kiểm"),
    D("power_outlet",
      ["ổ cắm cứ nóng lên", "chỉ cắm một cái nồi cơm thôi chứ có cắm nhiều đâu"],
      must_not=["OUTLET_OVERLOAD"], persona="khách bình thường"),

    # =====================================================================
    # NƯỚC: VÒI, BỒN, ỐNG, BỒN CẦU
    # =====================================================================
    D("faucet",
      ["vòi nước chảy yếu", "tháo rửa đầu lọc rồi mà vẫn yếu"],
      must_not=["FAUCET_LOW_FLOW"], persona="khách bình thường"),
    D("faucet",
      ["vòi rửa nhỏ giọt suốt", "mới thay gioăng cao su rồi"],
      must_not=["FAUCET_DRIP"], expect_any=["FAUCET_CARTRIDGE"], persona="khách bình thường"),
    D("toilet",
      ["bồn cầu chảy nước liên tục xuống lòng bồn", "thay van xả mới rồi vẫn chảy"],
      must_not=["TOILET_FLAPPER_LEAK"], expect_any=["TOILET_FILL_VALVE"], persona="khách bình thường"),
    D("toilet",
      ["cầu tiêu nhà tui rỉ nước dưới chân", "à mà chân bồn cầu khô ráo, rỉ ở chỗ két nước"],
      must_not=["TOILET_BASE_LEAK"], persona="khách sửa lời", region="nam"),

    # =====================================================================
    # MÁY LỌC NƯỚC / MÁY RỬA BÁT / MÁY SẤY / KHOÁ
    # =====================================================================
    D("water_purifier",
      ["máy lọc nước có mùi lạ", "mới thay lõi lọc tháng trước"],
      must_not=["PURIFIER_FILTER_DUE"], persona="khách bình thường"),
    D("water_purifier",
      ["máy lọc nước lâu rồi em chưa thay lõi có sao không"],
      must_not=[], expect_any=["PURIFIER_FILTER_DUE"], via="ask", persona="khách hỏi",
      note="chưa thay lõi là ủng hộ, không phải phủ định"),
    D("clothes_dryer",
      ["máy sấy sấy lâu khô", "vệ sinh lọc xơ rồi mà vẫn vậy"],
      must_not=["DRYER_LINT_CLOGGED"], persona="khách bình thường"),
    D("dishwasher",
      ["máy rửa bát không lên nguồn", "à nhầm, vẫn sáng đèn, chỉ là không cấp nước"],
      must_not=["DW_NO_POWER"], persona="khách sửa lời"),
    D("smart_lock",
      ["khóa vân tay không mở được", "thay pin mới rồi"],
      must_not=["LOCK_LOW_BATTERY"], persona="khách bình thường"),
    D("smart_lock",
      ["khóa cửa thông minh hết pin rồi làm sao"],
      must_not=[], expect_any=["LOCK_LOW_BATTERY"], via="ask", persona="khách hỏi",
      note="hết pin là triệu chứng, không phải phủ định"),
]
