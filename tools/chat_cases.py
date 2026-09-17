"""A hundred messages the way customers actually send them.

Written to be awkward on purpose. Real messages are not "máy lạnh không mát,
dàn lạnh bám tuyết" — they are "may lanh nha e k mat", sent without diacritics
from a phone, or three symptoms at once, or a question about price with no
device named, or a complaint that is not a question at all.

Each case says what a good answer does, not what words it uses. `expect` is one
of:

    diagnose   name a fault and give a price
    ask        one question back, because the message genuinely settles nothing
    answer     a grounded reply from the policy or price tables
    refuse     politely say this is not what FixHome does
    identify   say what the appliance is and ask what is wrong with it

`device` is the appliance a correct answer must land on, where there is one.
Left None when the message names none and none should be invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Case:
    text: str
    expect: str
    device: Optional[str] = None
    faults_any: List[str] = field(default_factory=list)
    """Any one of these counts as right. Several faults often fit one sentence."""

    note: str = ""

    corpus_any: List[str] = field(default_factory=list)
    """Written files at least one of which must appear in the retrieved prose.

    Checked at the file rather than the section, because which section answers
    a question is a tuning decision and pinning it would make every tweak a
    test failure. Which file is not: "vì sao dàn lạnh bám tuyết" has to reach
    the icing or refrigerant file and nothing else is a right answer.
    """

    pin: Optional[str] = None
    """Fault whose safety section must be pinned ahead of everything else.

    Only set where getting it wrong is irreversible. `tools/eval_retrieval.py`
    reports these separately from the rest, because a missed explanation is a
    gap and a missed warning is a defect."""

    business_any: List[str] = field(default_factory=list)
    """Business-layer files, for questions about booking, warranty or how a
    price is put together."""


CASES: List[Case] = [
    # ---------------------------------------------------- plain and clear
    Case("máy lạnh nhà em chạy cả ngày mà không mát", "diagnose", "air_conditioner",
         ["AC_LOW_REFRIGERANT", "AC_DIRTY_FILTER", "AC_ICING"]),
    Case("tủ lạnh ngăn mát không lạnh mà ngăn đá vẫn đông", "diagnose", "refrigerator",
         ["FRIDGE_FAN_FAULT", "FRIDGE_DEFROST_FAULT", "FRIDGE_LOW_GAS"]),
    Case("máy giặt không vắt được, quay một lúc rồi đứng", "diagnose", "washing_machine",
         ["WM_NO_SPIN", "WM_DRAIN_PUMP", "WM_MOTOR_FAULT"]),
    Case("bình nóng lạnh bật cả tiếng vẫn ra nước lạnh", "diagnose", "water_heater",
         ["WH_HEATING_ELEMENT", "WH_THERMOSTAT", "WH_INSTANT_NO_HOT"]),
    Case("bếp gas bật mãi không lên lửa, đánh tạch tạch", "diagnose", "gas_stove",
         ["STOVE_IGNITER"]),
    Case("bồn cầu dội nước không trôi", "diagnose", "toilet",
         ["TOILET_CLOGGED", "TOILET_WEAK_FLUSH"]),
    Case("vòi nước nhà tắm nhỏ giọt suốt đêm", "diagnose", "faucet",
         ["FAUCET_DRIP", "FAUCET_CARTRIDGE"]),
    Case("quạt trần quay chậm và kêu cọt kẹt", "diagnose", "ceiling_fan",
         ["CEILFAN_BEARING", "CEILFAN_CAPACITOR"]),
    Case("tivi có sọc dọc màn hình", "diagnose", "television",
         ["TV_PANEL_DAMAGE", "TV_MAIN_BOARD", "TV_BACKLIGHT"]),
    Case("lò vi sóng chạy nhưng không nóng thức ăn", "diagnose", "microwave_oven",
         ["MW_MAGNETRON"]),

    # ---------------------------------------------- no diacritics, phone typing
    Case("may lanh nha e k mat", "diagnose", "air_conditioner", [],
         note="Không dấu, viết tắt, vẫn phải hiểu"),
    Case("tu lanh k lanh", "diagnose", "refrigerator"),
    Case("may giat khong vat duoc", "diagnose", "washing_machine"),
    Case("binh nong lanh k nong", "diagnose", "water_heater"),
    Case("bep ga k len lua", "diagnose", "gas_stove"),
    Case("bon cau bi nghet", "diagnose", "toilet"),
    Case("voi nuoc bi ro", "diagnose", "faucet"),
    Case("quat tran keu to", "diagnose", "ceiling_fan"),
    Case("tivi mat tieng", "diagnose", "television"),
    Case("o cam bi chay den", "diagnose", "power_outlet"),

    # ------------------------------------------------- vague, must ask back
    Case("hư rồi", "ask", None, [], note="Không thiết bị, không triệu chứng"),
    Case("nhà em bị hỏng", "ask"),
    Case("cứu em với", "ask"),
    Case("máy hỏng rồi em ơi", "ask"),
    Case("sửa giúp em cái này", "ask"),
    Case("nó không chạy", "ask"),
    Case("bị lỗi", "ask"),
    Case("có vấn đề", "ask"),

    # ------------------------------------------- price, must use the tables
    Case("vệ sinh máy lạnh giá bao nhiêu", "answer"),
    Case("thay ổ cắm hết bao nhiêu tiền", "answer"),
    Case("thay gioăng cửa máy giặt bao nhiêu", "answer"),
    Case("bơm xả máy giặt giá sao em", "answer"),
    Case("block máy lạnh 12000 btu giá nhiêu", "answer"),
    Case("thay thanh đốt bình nóng lạnh giá bao nhiêu", "answer"),
    Case("công thay vòi sen là bao nhiêu", "answer"),
    Case("lắp quạt trần tốn bao nhiêu", "answer"),
    Case("vệ sinh máy giặt cửa ngang giá thế nào", "answer"),
    Case("magnetron lò vi sóng bao nhiêu tiền", "answer"),

    # ------------------------------------------------- policy questions
    Case("bao lâu nên vệ sinh máy lạnh một lần", "answer"),
    Case("máy giặt bao lâu vệ sinh", "answer"),
    Case("tủ lạnh có cần bảo trì định kỳ không", "answer"),
    Case("bình nóng lạnh bao lâu súc một lần", "answer"),

    # --------------------------------------------------- outside the trade
    Case("hôm nay trời đẹp không", "refuse"),
    Case("giá vàng bây giờ bao nhiêu", "refuse"),
    Case("bitcoin giá bao nhiêu", "refuse"),
    Case("chiến tranh thế giới xảy ra khi nào", "refuse"),
    Case("bạn tên gì", "refuse"),
    Case("kể chuyện cười đi", "refuse"),
    Case("2 cộng 2 bằng mấy", "refuse"),
    Case("cho xin số điện thoại giám đốc", "refuse"),

    # ------------------------------------- several symptoms in one message
    Case("máy lạnh không mát, chảy nước xuống tường, còn kêu to nữa", "diagnose",
         "air_conditioner"),
    Case("máy giặt vừa không vắt vừa rò nước ra sàn", "diagnose", "washing_machine"),
    Case("tủ lạnh không lạnh mà còn kêu ù ù cả đêm", "diagnose", "refrigerator"),
    Case("bình nóng lạnh không nóng với lại hay nhảy aptomat", "diagnose",
         "water_heater", ["WH_ELCB_TRIPS", "WH_HEATING_ELEMENT"]),

    # ------------------------------------------------- urgent and dangerous
    Case("ổ cắm bốc khói có mùi khét", "diagnose", "power_outlet",
         ["OUTLET_SHORT_CIRCUIT"]),
    Case("ngửi thấy mùi gas trong bếp", "diagnose", "gas_stove", ["STOVE_GAS_LEAK"]),
    Case("máy lạnh có mùi khét, bật lên là nhảy cầu dao", "diagnose",
         "air_conditioner", ["AC_SMELL_BURNT"]),
    Case("bình nóng lạnh bị rò điện giật nhẹ khi tắm", "diagnose", "water_heater",
         ["WH_ELCB_TRIPS"]),
    Case("nước chảy lênh láng ra nhà từ ống nước", "diagnose", "water_pipe",
         ["PIPE_BURST", "PIPE_JOINT_LEAK"]),

    # --------------------------------------------- awkward but still clear
    Case("con máy lạnh nhà t nó dở chứng k chịu mát", "diagnose", "air_conditioner"),
    Case("may giat nha minh no bi lam sao ay, k vat dc", "diagnose", "washing_machine"),
    Case("cái tủ lạnh nó cứ kêu suốt, khó chịu quá", "diagnose", "refrigerator"),
    Case("bồn cầu nhà mình nó xả yếu lắm ạ", "diagnose", "toilet"),
    Case("cái bình nước nóng hình như hỏng rồi, tắm toàn nước lạnh", "diagnose",
         "water_heater"),

    # --------------------------------------------- questions, not reports
    Case("máy lạnh bám tuyết là bị gì vậy em", "diagnose", "air_conditioner",
         ["AC_ICING", "AC_LOW_REFRIGERANT"]),
    Case("tại sao máy giặt lại rung mạnh khi vắt", "diagnose", "washing_machine"),
    Case("vì sao tủ lạnh đóng tuyết dày", "diagnose", "refrigerator",
         ["FRIDGE_DEFROST_FAULT"]),
    Case("bếp gas lửa đỏ có sao không", "diagnose", "gas_stove",
         ["STOVE_BURNER_CLOGGED"]),

    # ------------------------------------------ asking what to book or do
    Case("giờ em nên đặt dịch vụ gì", "ask", None, [],
         note="Chưa có thiết bị nào trong hội thoại"),
    Case("máy lạnh không mát thì nên đặt dịch vụ nào", "diagnose", "air_conditioner"),
    Case("trước khi thợ tới em cần làm gì", "answer"),
    Case("bên mình có nhận sửa tủ lạnh không", "answer"),

    # ------------------------------------------------ confusable devices
    Case("cái lò nhà em không nóng", "ask", None, [],
         note="Lò vi sóng hay lò nướng, phải hỏi"),
    Case("quạt nhà em kêu to quá", "ask", None, [],
         note="Quạt trần hay quạt điện"),
    Case("chỗ rửa bát bị rò nước", "ask", None, [],
         note="Chậu rửa hay vòi nước"),
    Case("lò vi sóng nhà em không quay đĩa", "diagnose", "microwave_oven",
         ["MW_TURNTABLE_MOTOR"]),
    Case("lò nướng thanh nhiệt không đỏ", "diagnose", "oven",
         ["OVEN_HEATING_ELEMENT"]),

    # ------------------------------------------------------ social noise
    Case("alo", "ask"),
    Case("chào em", "ask"),
    Case("em ơi", "ask"),
    Case("có ai không", "ask"),
    Case("ok cảm ơn em", "ask"),

    # ------------------------------------- long rambling, real customers
    Case("em chào anh, số là nhà em mới chuyển về được hai tháng, cái máy lạnh "
         "trong phòng ngủ dạo này bật lên chạy suốt mà phòng vẫn nóng, em có lau "
         "lưới lọc rồi mà vẫn vậy, không biết có phải hết gas không ạ",
         "diagnose", "air_conditioner", ["AC_LOW_REFRIGERANT"]),
    Case("máy giặt nhà mình mua được 5 năm rồi, dạo này mỗi lần vắt là nó nhảy "
         "lên rung bần bật, có khi còn dịch chuyển cả máy ra khỏi chỗ, em sợ nó "
         "hỏng luôn", "diagnose", "washing_machine"),
    Case("cho em hỏi cái tủ lạnh side by side nhà em ngăn đá đóng tuyết dày cả "
         "đốt tay, em rã đông thủ công rồi mà vài hôm lại đóng lại", "diagnose",
         "refrigerator", ["FRIDGE_DEFROST_FAULT"]),

    # ----------------------------------------------- price without device
    Case("sửa cái đó hết bao nhiêu", "ask"),
    Case("bên mình tính giá sao", "ask"),
    Case("mắc không em", "ask"),

    # -------------------------------------------- testing the boundaries
    Case("máy bay nhà em không bay được", "refuse", None, [],
         note="Có chữ máy nhưng không phải đồ gia dụng"),
    Case("xe máy không nổ", "refuse"),
    Case("laptop không lên nguồn", "refuse", None, [],
         note="Đồ điện tử nhưng ngoài 17 nhóm"),
    Case("điều hoà xe hơi không mát", "refuse", None, [],
         note="Điều hoà nhưng của xe, ngoài phạm vi tại nhà"),

    # --------------------------------------------- polite but unhelpful
    Case("dạ", "ask"),
    Case("vâng ạ", "ask"),
    Case("ừ", "ask"),
    Case("không", "ask"),
    Case("có", "ask"),

    # ------------------------------------------------- mixed intentions
    Case("máy lạnh không mát, mà vệ sinh máy lạnh giá bao nhiêu vậy em", "diagnose",
         "air_conditioner", [], note="Vừa tả bệnh vừa hỏi giá"),
    Case("tủ lạnh hỏng, bên mình bảo hành thế nào", "diagnose", "refrigerator"),
    Case("ổ cắm cháy rồi, giờ thay hết bao nhiêu", "diagnose", "power_outlet"),

    # -------------------------------------------------- unusual phrasing
    Case("nước nóng nhà em nó nguội ngắt à", "diagnose", "water_heater"),
    Case("cái quạt trần nó lắc lư như sắp rơi", "diagnose", "ceiling_fan",
         ["CEILFAN_MOUNT_LOOSE"]),
    Case("bóng đèn nhà em cứ chớp chớp", "diagnose", "light_bulb",
         ["LIGHT_FLICKERING"]),
    Case("đường ống nước kêu như búa gõ", "diagnose", "water_pipe", ["PIPE_NOISY"]),
    Case("nước máy nhà em đục ngầu", "diagnose", "water_pipe", ["PIPE_RUSTY_WATER"]),
    Case("ấm siêu tốc đun mãi không sôi", "diagnose", "kettle"),
    Case("ấm đun nước bị rò nước dưới đáy", "diagnose", "kettle", ["KETTLE_LEAK"]),
    Case("chậu rửa bát thoát nước chậm", "diagnose", "sink", ["SINK_CLOGGED"]),
    Case("dưới bồn rửa bị chảy nước ra sàn", "diagnose", "sink", ["SINK_TRAP_LEAK"]),
    Case("cống nhà tắm bốc mùi hôi", "diagnose", "sink", ["SINK_SMELL"]),
    Case("nắp bồn cầu bị gãy bản lề", "diagnose", "toilet", ["TOILET_SEAT_BROKEN"]),
    Case("két nước bồn cầu chảy suốt không ngừng", "diagnose", "toilet",
         ["TOILET_FLAPPER_LEAK", "TOILET_FILL_VALVE"]),
    Case("đèn trần bị vào nước sau cơn mưa", "diagnose", "light_bulb",
         ["LIGHT_FIXTURE_LEAK"]),
    Case("công tắc đèn bấm không ăn", "diagnose", "light_bulb",
         ["LIGHT_SWITCH_FAULT"]),
    Case("cắm sạc vào ổ mà lỏng lẻo rơi ra", "diagnose", "power_outlet",
         ["OUTLET_LOOSE_CONTACT"]),

    # ------------------------------------------------------------------
    # Questions the written corpus exists to answer.
    #
    # Everything above can be settled by naming a fault. These cannot: they ask
    # why something happens, what to do first, or what the rule is. Before the
    # corpus was wired in, the honest reply to all of them was a question.
    # ------------------------------------------------------------------

    # ------------------------------------------------ "vì sao", "thế nào"
    Case("vì sao dàn lạnh bám tuyết", "answer", "air_conditioner",
         ["AC_ICING", "AC_LOW_REFRIGERANT"],
         corpus_any=["faults/AC_ICING.md", "faults/AC_LOW_REFRIGERANT.md"]),
    Case("tại sao lửa bếp gas lại có màu đỏ", "answer", "gas_stove",
         ["STOVE_BURNER_CLOGGED"],
         corpus_any=["faults/STOVE_BURNER_CLOGGED.md", "devices/gas_stove.md"]),
    Case("sao quat cu phai lay tay quay moi chay", "answer", "electric_fan",
         ["FAN_CAPACITOR"],
         corpus_any=["faults/FAN_CAPACITOR.md"]),
    Case("tivi có tiếng mà màn hình tối thui là sao", "answer", "television",
         ["TV_BACKLIGHT"],
         corpus_any=["faults/TV_BACKLIGHT.md", "devices/television.md"]),
    Case("vì sao ấm siêu tốc sôi rồi mà không tự tắt", "answer", "kettle",
         ["KETTLE_THERMOSTAT", "KETTLE_SCALE"],
         corpus_any=["faults/KETTLE_THERMOSTAT.md", "faults/KETTLE_SCALE.md",
                     "devices/kettle.md"]),
    Case("cặn trắng đóng dưới đáy ấm có độc không", "answer", "kettle",
         ["KETTLE_SCALE"], corpus_any=["faults/KETTLE_SCALE.md"]),
    Case("bồn cầu xả yếu là do đâu", "answer", "toilet",
         ["TOILET_WEAK_FLUSH"],
         corpus_any=["faults/TOILET_WEAK_FLUSH.md", "devices/toilet.md"]),
    Case("sao đèn led mới mua nửa năm đã hỏng", "answer", "light_bulb",
         ["LIGHT_BULB_DEAD", "LIGHT_FLICKERING"],
         corpus_any=["faults/LIGHT_BULB_DEAD.md", "faults/LIGHT_FLICKERING.md",
                     "devices/light_bulb.md"]),
    Case("lò nướng nhà em nướng bánh cháy mặt mà sống ruột", "diagnose", "oven",
         ["OVEN_HEATING_ELEMENT"],
         corpus_any=["faults/OVEN_HEATING_ELEMENT.md", "devices/oven.md"]),
    Case("ống nước kêu cốp một cái mỗi lần khoá vòi", "diagnose", "water_pipe",
         ["PIPE_NOISY"], corpus_any=["faults/PIPE_NOISY.md"]),

    # ------------------------------------------ the ones that must warn first
    Case("bếp gas nhà em có mùi gas", "diagnose", "gas_stove",
         ["STOVE_GAS_LEAK"], pin="STOVE_GAS_LEAK",
         corpus_any=["faults/STOVE_GAS_LEAK.md"]),
    Case("bep ga nha e co mui ga so qua", "diagnose", "gas_stove",
         ["STOVE_GAS_LEAK"], pin="STOVE_GAS_LEAK",
         note="không dấu, đang hoảng"),
    Case("vỡ ống nước, nước phun khắp nhà", "diagnose", "water_pipe",
         ["PIPE_BURST"], pin="PIPE_BURST",
         corpus_any=["faults/PIPE_BURST.md"]),
    Case("quạt trần có mùi khét", "diagnose", "ceiling_fan",
         ["CEILFAN_MOTOR_BURNT"], pin="CEILFAN_MOTOR_BURNT",
         corpus_any=["faults/CEILFAN_MOTOR_BURNT.md"]),
    Case("quạt cây bốc mùi khét", "diagnose", "electric_fan",
         ["FAN_MOTOR_BURNT"], pin="FAN_MOTOR_BURNT",
         corpus_any=["faults/FAN_MOTOR_BURNT.md"]),
    Case("ổ cắm bị cháy đen", "diagnose", "power_outlet",
         ["OUTLET_SHORT_CIRCUIT"], pin="OUTLET_SHORT_CIRCUIT",
         corpus_any=["faults/OUTLET_SHORT_CIRCUIT.md"]),
    Case("lò vi sóng toé lửa trong ruột", "diagnose", "microwave_oven",
         ["MW_SPARKING"], pin="MW_SPARKING",
         corpus_any=["faults/MW_SPARKING.md"]),
    Case("đèn nhà tắm bị vào nước", "diagnose", "light_bulb",
         ["LIGHT_FIXTURE_LEAK"], pin="LIGHT_FIXTURE_LEAK",
         corpus_any=["faults/LIGHT_FIXTURE_LEAK.md"]),
    Case("ấm siêu tốc rò nước ở đáy", "diagnose", "kettle",
         ["KETTLE_LEAK"], pin="KETTLE_LEAK",
         corpus_any=["faults/KETTLE_LEAK.md"]),
    Case("chân bồn cầu bị rò nước ra sàn", "diagnose", "toilet",
         ["TOILET_BASE_LEAK"], pin="TOILET_BASE_LEAK",
         corpus_any=["faults/TOILET_BASE_LEAK.md"]),

    # --------------------------------------------------- the business layer
    Case("đặt lịch sửa chữa thế nào", "answer", None,
         business_any=["system/quy-trinh-dat-lich.md"]),
    Case("bảo hành bao lâu", "answer", None,
         business_any=["system/bao-hanh.md"]),
    Case("tiền công với tiền linh kiện tính riêng hay chung", "answer", None,
         business_any=["system/gia-va-cach-tinh-tien.md",
                       "system/bao-hanh.md"]),
    Case("fixhome là làm gì vậy", "answer", None,
         business_any=["system/tong-quan-fixhome.md",
                       "system/vai-tro-cua-ai.md"]),
    Case("thợ tới rồi mà em không đồng ý giá thì sao", "answer", None,
         business_any=["system/quy-trinh-dat-lich.md",
                       "system/gia-va-cach-tinh-tien.md"]),

    # ------------------------------- the five devices Backend already sells for
    # Phrased away from the symptom lists on purpose. A case written in the
    # same words as the index it is testing measures nothing.
    Case("bếp nhà mình đặt nồi lên nó kêu bíp bíp rồi thôi", "diagnose", "induction_hob",
         faults_any=["HOB_NO_PAN_DETECT", "HOB_ERROR_CODE"]),
    Case("bep tu nha e hien chu E2 roi tat", "diagnose", "induction_hob",
         faults_any=["HOB_ERROR_CODE"]),
    Case("bếp từ nấu được mười phút là tự tắt", "diagnose", "induction_hob",
         faults_any=["HOB_FAN_NOISY", "HOB_ERROR_CODE"]),
    Case("hôm qua làm rơi cái nắp nồi xuống mặt bếp từ", "diagnose", "induction_hob",
         faults_any=["HOB_GLASS_CRACKED"]),
    Case("cắm bếp từ vào là cả nhà mất điện", "diagnose", "induction_hob",
         faults_any=["HOB_NO_POWER"],
         note="phải cảnh báo trước khi hỏi"),

    Case("máy rửa bát chạy xong bát vẫn nhớt dầu", "diagnose", "dishwasher",
         faults_any=["DW_NOT_CLEAN"]),
    Case("mở cửa máy rửa chén ra thấy nước đọng ở đáy", "diagnose", "dishwasher",
         faults_any=["DW_NOT_DRAINING"]),
    Case("may rua bat cham dat", "ask", None,
         note="không đủ để kết luận, hỏi lại"),

    Case("máy sấy chạy cả tiếng mà áo vẫn ẩm", "diagnose", "clothes_dryer",
         faults_any=["DRYER_NOT_HEATING", "DRYER_LINT_CLOGGED"]),
    Case("máy sấy quần áo dạo này lâu khô hơn hẳn", "diagnose", "clothes_dryer",
         faults_any=["DRYER_LINT_CLOGGED", "DRYER_NOT_HEATING"]),

    Case("cây nước nóng lạnh nhà em không ra nước nữa", "diagnose", "water_purifier",
         faults_any=["PURIFIER_NO_WATER", "PURIFIER_NO_POWER"]),
    Case("nước lọc dạo này uống thấy có vị lạ", "diagnose", "water_purifier",
         faults_any=["PURIFIER_FILTER_DUE"]),
    Case("máy lọc nước kêu ù ù suốt đêm không nghỉ", "diagnose", "water_purifier",
         faults_any=["PURIFIER_PUMP_RUNS_ON"]),

    Case("khoá cửa đặt tay mãi không mở được", "diagnose", "smart_lock",
         faults_any=["LOCK_FINGERPRINT_FAIL", "LOCK_LOW_BATTERY"]),
    Case("khoá vân tay kêu tít tít mỗi lần mở cửa", "diagnose", "smart_lock",
         faults_any=["LOCK_LOW_BATTERY"]),
    Case("khoá nhận vân rồi mà cửa vẫn không bật ra", "diagnose", "smart_lock",
         faults_any=["LOCK_MOTOR_FAULT"]),
    Case("em đang đứng ngoài cửa không vào nhà được", "diagnose", "smart_lock",
         faults_any=["LOCK_LOCKED_OUT"]),

    # ------------------------------- nothing may be retrieved for these
    Case("hôm nay ăn gì ngon", "refuse", None,
         note="không thiết bị, không triệu chứng — không được lấy gì"),
    Case("thời tiết hôm nay thế nào", "refuse", None),
    Case("cho hỏi giá vàng hôm nay", "refuse", None),
]
