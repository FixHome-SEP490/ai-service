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
]
