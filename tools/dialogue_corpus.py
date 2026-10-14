"""Generated multi-turn conversations, for coverage the hand-written set cannot reach.

`dialogue_cases.py` holds dialogues a person wrote and checked one by one. This
file builds tens of thousands more from the same two sources the service reads,
so every fault the knowledge base knows is tested in every way a customer can
push back on it, in every voice:

    who         an older northerner, a southern student, someone from Huế, an
                angry customer, a technician, someone who types one word, a
                worried parent, a polite office worker, a storyteller
    where       Bắc, Trung, Nam: "điều hòa" or "máy lạnh", "bình nóng lạnh" or
                "máy nước nóng", "hỏng" or "hư", "không" or "hông" or "nỏ",
                "sao" or "răng", "vậy" or "rứa" or "dzậy"
    how         accents, no accents, teencode, Telex that did not convert,
                caps lock, stretched letters, emoji, no punctuation, typos,
                voice-to-text, English words in the middle

and what the second turn does:

    done        reports a fix that has already been made ("mới vệ sinh rồi")
    cause       denies a cause, before or after naming it ("không phải do bẩn",
                "bẩn thì không phải")
    absent      gives evidence against a fault ("lưới lọc sạch")
    previous    rejects whatever the last answer led with ("không phải đâu")
    ask         one of the above, then a question ("vậy giờ là bị gì")
    keep        says something that is *not* an exclusion and must not be read
                as one: "chưa vệ sinh", "có nên vệ sinh không", a new symptom,
                a symptom that is absent from some other fault

The gold labels come from the curated lexicon, not from the service's output,
so a generated case can fail. The phrases are the lexicon's own, which makes
`done`, `cause` and `absent` a test of everything *around* the phrase - the
voice, the dialect, the typing, where the denial sits, what else is in the
message. The phrases themselves are tested by the hand-written set, which does
not use them verbatim.

    python tools/eval_dialogue.py --generated 20000
"""

from __future__ import annotations

import json
import random
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    from tools.dialogue_cases import Dialogue
except ImportError:  # run as a script from tools/
    from dialogue_cases import Dialogue

_ROOT = Path(__file__).resolve().parents[1]
_KB_PATH = _ROOT / "app" / "data" / "fault_knowledge_base.json"
_LEXICON_PATH = _ROOT / "app" / "data" / "dialogue_knowledge.json"


# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------

REGIONS: Dict[str, Dict[str, List[str]]] = {
    "bac": {
        "self": ["tôi", "mình", "em", "nhà mình", "nhà em", "nhà tôi"],
        "end": ["ạ", "nhé", "nhỉ", "đấy", "", "", "ạ", "cơ"],
        "broke": ["hỏng", "bị hỏng", "hỏng rồi"],
        "so": ["thế", "vậy"],
        "what": ["bị gì thế", "hỏng gì thế", "bị làm sao thế", "là bị gì vậy", "bị sao ạ"],
        "now": ["giờ", "bây giờ", "thế giờ", "vậy giờ"],
        "call": ["anh ơi", "chị ơi", "em ơi", "cho mình hỏi", "bạn ơi"],
    },
    "trung": {
        "self": ["tui", "mình", "em", "nhà tui", "nhà mình"],
        "end": ["hỉ", "rứa", "nờ", "hè", "", "", "tề"],
        "broke": ["hư", "hỏng", "bị hư"],
        "so": ["rứa", "vậy"],
        "what": ["bị chi rứa", "hư chi rứa", "răng rứa", "bị răng rứa", "là bị chi"],
        "now": ["chừ", "bây chừ", "rứa chừ", "giờ"],
        "call": ["anh ơi", "o ơi", "chị ơi", "em ơi"],
    },
    "nam": {
        "self": ["tui", "mình", "em", "nhà tui", "nhà em", "tụi tui"],
        "end": ["nha", "nè", "á", "đó", "hen", "nghen", "", "", "luôn á"],
        "broke": ["hư", "bị hư", "hư rồi"],
        "so": ["vậy", "dzậy", "zị"],
        "what": ["bị gì vậy", "hư cái gì dzậy", "bị sao zị", "bị gì dị", "là sao vậy"],
        "now": ["giờ", "dzậy giờ", "vậy giờ"],
        "call": ["anh ơi", "chị ơi", "em ơi", "bạn ơi", "cho hỏi chút"],
    },
}

# What the appliance is called, by region. Northern and southern names differ
# for several of them, and the customer uses their own.
DEVICE_NAMES: Dict[str, Dict[str, List[str]]] = {
    "air_conditioner": {"bac": ["điều hòa", "điều hoà", "cái điều hòa"], "trung": ["điều hòa", "máy lạnh"], "nam": ["máy lạnh", "cái máy lạnh", "máy lạnh"]},
    "ceiling_fan": {"bac": ["quạt trần"], "trung": ["quạt trần"], "nam": ["quạt trần"]},
    "electric_fan": {"bac": ["quạt điện", "quạt cây", "cái quạt"], "trung": ["quạt máy", "cái quạt"], "nam": ["quạt máy", "quạt đứng", "cái quạt"]},
    "washing_machine": {"bac": ["máy giặt"], "trung": ["máy giặt"], "nam": ["máy giặt", "cái máy giặt"]},
    "refrigerator": {"bac": ["tủ lạnh", "cái tủ lạnh"], "trung": ["tủ lạnh"], "nam": ["tủ lạnh", "tủ lạnh"]},
    "microwave_oven": {"bac": ["lò vi sóng", "lò vi ba"], "trung": ["lò vi sóng"], "nam": ["lò vi sóng", "lò vi ba"]},
    "oven": {"bac": ["lò nướng"], "trung": ["lò nướng"], "nam": ["lò nướng"]},
    "gas_stove": {"bac": ["bếp gas", "bếp ga"], "trung": ["bếp ga"], "nam": ["bếp ga", "bếp gas"]},
    "kettle": {"bac": ["ấm siêu tốc", "ấm đun nước"], "trung": ["ấm điện", "ấm siêu tốc"], "nam": ["bình đun nước", "ấm siêu tốc"]},
    "television": {"bac": ["tivi", "ti vi"], "trung": ["tivi"], "nam": ["tivi", "tv"]},
    "sink": {"bac": ["bồn rửa bát", "chậu rửa"], "trung": ["bồn rửa"], "nam": ["bồn rửa chén", "lavabo"]},
    "faucet": {"bac": ["vòi nước", "vòi rửa"], "trung": ["vòi nước"], "nam": ["vòi nước", "cái vòi"]},
    "toilet": {"bac": ["bồn cầu", "bệt"], "trung": ["bồn cầu"], "nam": ["bồn cầu", "toilet"]},
    "power_outlet": {"bac": ["ổ cắm", "ổ điện"], "trung": ["ổ cắm"], "nam": ["ổ cắm", "ổ điện"]},
    "light_bulb": {"bac": ["bóng đèn", "đèn"], "trung": ["bóng đèn"], "nam": ["bóng đèn", "cái đèn"]},
    "water_pipe": {"bac": ["ống nước", "đường ống"], "trung": ["ống nước"], "nam": ["ống nước", "đường ống nước"]},
    "water_heater": {"bac": ["bình nóng lạnh", "bình nóng lạnh"], "trung": ["bình nóng lạnh", "máy nước nóng"], "nam": ["máy nước nóng", "máy nước nóng"]},
    "induction_hob": {"bac": ["bếp từ"], "trung": ["bếp từ"], "nam": ["bếp từ", "bếp điện từ"]},
    "dishwasher": {"bac": ["máy rửa bát"], "trung": ["máy rửa bát"], "nam": ["máy rửa chén"]},
    "clothes_dryer": {"bac": ["máy sấy quần áo", "máy sấy"], "trung": ["máy sấy"], "nam": ["máy sấy đồ", "máy sấy"]},
    "water_purifier": {"bac": ["máy lọc nước"], "trung": ["máy lọc nước"], "nam": ["máy lọc nước"]},
    "smart_lock": {"bac": ["khóa vân tay", "khóa cửa thông minh"], "trung": ["khóa vân tay"], "nam": ["khóa vân tay", "khóa điện tử"]},
}


# ---------------------------------------------------------------------------
# Personas: how the same content is framed
# ---------------------------------------------------------------------------

PERSONAS = [
    "lớn tuổi", "trẻ", "bực bội", "kỹ thuật", "kiệm lời", "kể lể", "lịch sự", "lo lắng",
]


def _open(persona: str, region: str, name: str, symptom: str, rng: random.Random) -> str:
    r = REGIONS[region]
    me = rng.choice(r["self"])
    end = rng.choice(r["end"])
    if persona == "lớn tuổi":
        return rng.choice([
            f"Cháu ơi, {name} nhà bác {symptom} cháu ạ",
            f"Chào cháu, {name} nhà bà dạo này {symptom}, cháu xem giúp bà với",
            f"Cô hỏi chút, {name} nhà cô {symptom} {end}",
        ])
    if persona == "trẻ":
        return rng.choice([
            f"{name} nhà {me} {symptom} {end}",
            f"ê {name} {symptom} {end}",
            f"{name} {symptom} lun {end}",
        ])
    if persona == "bực bội":
        return rng.choice([
            f"{name} mới mua chưa được bao lâu mà đã {symptom}, bực mình quá",
            f"{name} lại {symptom} nữa rồi, chán thật sự",
            f"làm ăn kiểu gì mà {name} {symptom} hoài vậy",
        ])
    if persona == "kỹ thuật":
        return rng.choice([
            f"{name} {symptom}, {me} đã kiểm tra nguồn điện ổn định",
            f"Tình trạng: {name} {symptom}. Đã thử khởi động lại.",
        ])
    if persona == "kiệm lời":
        return rng.choice([f"{name} {symptom}", f"{symptom}"])
    if persona == "kể lể":
        return rng.choice([
            f"hôm qua đang dùng bình thường thì tự nhiên {name} {symptom}, {me} lo quá không biết làm sao",
            f"{name} nhà {me} mua được ba năm rồi, trước giờ không sao, mấy hôm nay thì {symptom} {end}",
            f"chuyện là {name} nhà {me} {symptom}, con nhỏ nó cứ hỏi hoài {end}",
        ])
    if persona == "lịch sự":
        return rng.choice([
            f"{rng.choice(r['call'])}, {name} nhà {me} {symptom}, nhờ kiểm tra giúp {end}",
            f"Xin chào, {name} của {me} đang {symptom}. Mong được tư vấn {end}",
        ])
    # lo lắng
    return rng.choice([
        f"{name} nhà {me} {symptom}, có nguy hiểm không {end}",
        f"{name} {symptom}, {me} sợ quá {end}",
    ])


# ---------------------------------------------------------------------------
# Second turns
# ---------------------------------------------------------------------------

_DONE_BEFORE = [
    "đã", "mới", "vừa", "mới vừa", "hôm qua thợ mới", "tuần trước {me} có gọi người",
    "{me} tự", "bữa trước mới", "tháng trước vừa", "sáng nay vừa", "{me} đã", "{me} mới",
    "thợ vừa", "hôm kia mới", "đợt trước có",
]
_DONE_AFTER = ["rồi", "xong rồi", "rồi mà", "rồi đó", "xong xuôi rồi", "kỹ rồi", "rồi nha", "xong"]
_DONE_TAIL = [
    "", "", "mà vẫn {sym}", "nhưng vẫn vậy", "mà vẫn bị", "vẫn y chang", "mà không ăn thua",
    "mà chẳng ăn thua gì", "mà vẫn {sym} {end}", "nên không phải do cái đó đâu",
]

_CAUSE_BEFORE = [
    "không phải do {c} đâu", "chắc chắn không phải {c}", "không thể nào là {c} được",
    "đâu phải tại {c}", "{me} nghĩ không phải do {c}", "kp do {c} đâu",
    "không phải {c} đâu {end}", "không liên quan gì tới {c} đâu", "chắc không phải do {c} đâu",
    "không phải tại {c}", "đâu có phải {c}",
]
_CAUSE_AFTER = [
    "{c} thì không phải rồi", "{c} không phải đâu", "{c} thì {me} kiểm tra rồi, không sao",
    "{c} ổn mà", "{c} bình thường mà", "còn {c} thì không phải",
]

_ABSENT = ["{a}", "{a} mà", "{me} xem rồi, {a}", "{a} {end}", "{a} nha", "kiểm tra rồi {a}"]

_PREVIOUS = {
    "bac": ["không phải đâu", "sai rồi", "không đúng", "không phải cái đó", "không phải đâu ạ", "nhầm rồi"],
    "trung": ["không phải mô", "nỏ phải", "sai rồi", "không phải rứa", "không phải mô hè"],
    "nam": ["hông phải đâu", "hổng phải", "sai rồi", "trật lất rồi", "không phải đâu nha", "hông phải dzậy"],
}

_ASK = {
    "bac": ["vậy giờ là bị gì", "thế giờ nó bị làm sao", "vậy là hỏng gì ạ", "thế phải sửa cái gì", "nên đặt dịch vụ nào ạ"],
    "trung": ["rứa chừ bị chi", "rứa là hư chi", "chừ phải làm răng", "rứa đặt dịch vụ chi"],
    "nam": ["dzậy giờ bị gì", "vậy là hư cái gì", "giờ phải làm sao", "vậy đặt dịch vụ nào", "vậy giờ sao"],
}

_NOT_YET = [
    "chưa {d} lần nào", "{me} chưa {d}", "lâu rồi chưa {d}", "chưa có {d}", "từ hồi mua tới giờ chưa {d}",
]
_INTENT = [
    "có nên {d} không", "{d} hết bao nhiêu tiền", "{me} định {d}", "có cần {d} không", "{d} giá sao",
]


def _fill(template: str, rng: random.Random, region: str, **values: str) -> str:
    r = REGIONS[region]
    values.setdefault("me", rng.choice(r["self"]))
    values.setdefault("end", rng.choice(r["end"]))
    text = template
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Typing styles
# ---------------------------------------------------------------------------

STYLES = [
    "chuẩn", "không dấu", "teencode", "telex sót", "viết hoa", "kéo dài", "emoji",
    "không dấu câu", "lỗi gõ", "giọng nói", "trộn tiếng anh",
]

_TEEN = {
    "không": ["ko", "k", "hông", "khum", "kh"], "được": ["dc", "đc"], "rồi": ["r", "rùi", "roài"],
    "gì": ["j", "gì"], "vậy": ["z", "v", "zị"], "mình": ["mik", "mk"], "biết": ["bít", "bik"],
    "với": ["vs"], "nước": ["nc", "nước"], "trước": ["trc"], "cũng": ["cx", "cũng"],
    "người": ["ng"], "mới": ["ms", "mới"], "xong": ["xog", "xong"], "luôn": ["lun"],
    "vệ": ["vệ"], "nhé": ["nha", "nhá"], "anh": ["a"], "chị": ["c"], "em": ["e"],
}
_ENGLISH = {
    "vệ sinh": ["clean", "vệ sinh"], "kiểm tra": ["check", "kiểm tra"], "sửa": ["fix", "sửa"],
    "điều khiển": ["remote"], "lưới lọc": ["filter", "lưới lọc"], "máy nén": ["block", "máy nén"],
    "bình thường": ["ok", "bình thường"], "thay": ["thay"],
}
_EMOJI = ["😭", "🥲", ":((", "huhu", "😤", "🙏", ":)", "😓", "hic", "🤦"]
_VOICE_FILLERS = ["ờ", "à", "kiểu là", "nói chung là", "ừm"]

_TONE_KEY = {"́": "s", "̀": "f", "̉": "r", "̃": "x", "̣": "j"}
_SHAPE = {"â": "aa", "ê": "ee", "ô": "oo", "ă": "aw", "ơ": "ow", "ư": "uw", "đ": "dd"}


def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", text)
    out = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    return out.replace("đ", "d").replace("Đ", "D")


def _telex(word: str) -> str:
    """A word as typed when the Vietnamese keyboard was off: "không" -> "khoong"."""
    decomposed = unicodedata.normalize("NFD", word)
    tone = ""
    base = []
    for ch in decomposed:
        if ch in _TONE_KEY:
            tone = _TONE_KEY[ch]
        else:
            base.append(ch)
    shaped = unicodedata.normalize("NFC", "".join(base))
    out = "".join(_SHAPE.get(c, c) for c in shaped)
    return out + tone


def _stretch(word: str, rng: random.Random) -> str:
    if len(word) < 2:
        return word
    return word + word[-1] * rng.randint(2, 4)


def _typo(word: str, rng: random.Random) -> str:
    if len(word) < 4:
        return word
    i = rng.randrange(1, len(word) - 1)
    kind = rng.choice(["swap", "drop", "double"])
    if kind == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    if kind == "drop":
        return word[:i] + word[i + 1 :]
    return word[:i] + word[i] + word[i:]


def styled(text: str, style: str, rng: random.Random) -> str:
    words = text.split()
    if style == "chuẩn":
        return text
    if style == "không dấu":
        return _fold(text).lower()
    if style == "teencode":
        out = []
        for w in words:
            key = w.lower().strip(",.!?")
            out.append(rng.choice(_TEEN[key]) if key in _TEEN and rng.random() < 0.8 else w.lower())
        joined = " ".join(out)
        return _fold(joined) if rng.random() < 0.5 else joined
    if style == "telex sót":
        accented = [i for i, w in enumerate(words) if _fold(w) != w and w.isalpha()]
        for i in rng.sample(accented, min(len(accented), rng.randint(1, 2))):
            words[i] = _telex(words[i].lower())
        return " ".join(words)
    if style == "viết hoa":
        return text.upper() + rng.choice(["", "!!!", "!!", " ?"])
    if style == "kéo dài":
        idx = [i for i, w in enumerate(words) if len(w) > 2]
        for i in rng.sample(idx, min(len(idx), rng.randint(1, 2))):
            words[i] = _stretch(words[i], rng)
        return " ".join(words)
    if style == "emoji":
        return f"{text} {' '.join(rng.sample(_EMOJI, rng.randint(1, 3)))}"
    if style == "không dấu câu":
        return "".join(c for c in text if c.isalnum() or c.isspace()).lower()
    if style == "lỗi gõ":
        idx = [i for i, w in enumerate(words) if len(w) >= 4]
        for i in rng.sample(idx, min(len(idx), 1)):
            words[i] = _typo(words[i], rng)
        return " ".join(words)
    if style == "giọng nói":
        out = []
        for w in "".join(c for c in text if c.isalnum() or c.isspace()).lower().split():
            if rng.random() < 0.12:
                out.append(rng.choice(_VOICE_FILLERS))
            out.append(w)
        return " ".join(out)
    if style == "trộn tiếng anh":
        out = text
        for vi, choices in _ENGLISH.items():
            if vi in out and rng.random() < 0.7:
                out = out.replace(vi, rng.choice(choices))
        return out
    raise ValueError(style)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _load():
    kb = json.loads(_KB_PATH.read_text(encoding="utf-8"))
    lexicon = json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))
    by_device: Dict[str, List[dict]] = {}
    for fault in kb["faults"]:
        by_device.setdefault(fault["device_type"], []).append(fault)
    return by_device, lexicon.get("faults", {})


def _tidy(text: str) -> str:
    """Joins of two templates that read badly: "nhà nhà em", "rồi mà mà vẫn"."""
    words = text.split()
    out: List[str] = []
    for w in words:
        if out and w == out[-1] and w in ("nhà", "mà", "rồi", "vẫn"):
            continue
        out.append(w)
    return " ".join(out)


def _short(symptom: str) -> str:
    return " ".join(symptom.split()[:4])


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

CATEGORIES = [
    "done", "done", "cause", "cause", "absent", "previous", "ask", "keep_not_yet",
    "keep_intent", "keep_new_symptom", "keep_negated_other", "multi",
    # What else a customer does in a conversation, beyond ruling things out.
    "confirm", "thanks", "price_followup", "safety", "safety_denied", "switch_device",
    "offtopic", "offtopic_return", "added_symptom", "greeting_first", "split_symptom",
    "worry_question",
    # Answering the question the assistant asked, and taking things back.
    "answer_yes", "answer_no", "retract", "correct_device", "pronoun",
    # The guess was wrong and the customer says what it is instead.
    "deny_and_hint",
]

_VAGUE = [
    "{n} nhà {me} bị sao ấy", "{n} có vấn đề {end}", "{n} dạo này lạ lắm", "{n} chạy không bình thường",
    "{n} nhà {me} trục trặc", "{n} bị gì đó {end}", "{n} hoạt động kỳ kỳ",
]
_YES = ["có", "có ạ", "dạ có", "có chứ", "có luôn", "rồi", "dạ rồi", "đúng rồi", "ừ có", "vâng", "có nha", "có em"]
_NO = ["không", "không ạ", "dạ không", "không có", "chưa", "chưa ạ", "không có đâu", "hông", "không thấy", "dạ chưa"]
_RETRACT = [
    "à nhầm, thật ra chưa {d}", "xin lỗi em nhớ nhầm, chưa {d} đâu", "à không, {me} chưa {d}",
    "khoan, hình như chưa {d}",
]
_PRONOUN = ["nó còn {s} nữa", "giờ nó {s}", "nó bị {s} luôn", "mà nó {s} nữa"]

_CONFIRM = {
    "bac": ["đúng rồi", "chuẩn rồi đấy", "đúng thế", "ừ đúng rồi em", "chính xác", "đúng là vậy"],
    "trung": ["đúng rồi", "đúng rứa", "chuẩn rồi", "ừ đúng"],
    "nam": ["đúng rồi đó", "chuẩn luôn", "y chang vậy á", "đúng rồi á em", "ừa đúng"],
}
_THANKS = ["cảm ơn em nhé", "ok cảm ơn", "cám ơn nhiều nha", "thanks em", "dạ em cảm ơn", "ok em", "tks"]
_PRICE = [
    "sửa cái đó hết bao nhiêu tiền", "vậy sửa bao nhiêu", "giá sửa khoảng bao nhiêu", "chi phí tầm bao nhiêu",
    "sửa cái này mất nhiêu tiền", "hết khoảng nhiêu vậy",
]
_WORRY = [
    "có nguy hiểm không", "tự sửa được không", "có cần gọi thợ không", "để vậy dùng tiếp được không",
    "sửa mất bao lâu", "có phải thay mới không",
]
_OFFTOPIC = [
    "à mà hôm nay thời tiết thế nào", "cho hỏi giá vàng hôm nay", "em có biết đá bóng tối nay không",
    "bitcoin giá bao nhiêu", "kể chuyện cười đi",
]
_RETURN = ["thôi quay lại cái máy, giờ sửa sao", "vậy cái máy kia giờ sao", "rồi quay lại vụ lúc nãy, giờ làm sao"]
_GREET = ["chào em", "alo", "shop ơi", "chào bạn", "xin chào", "hello"]
_SAFETY_DENY = ["không phải {c} đâu", "chắc không phải {c} đâu", "{c} thì không phải rồi"]


def _one(
    category: str,
    device: str,
    faults: List[dict],
    cues: Dict[str, dict],
    rng: random.Random,
    by_device: Optional[Dict[str, List[dict]]] = None,
) -> Optional[Dialogue]:
    region = rng.choice(list(REGIONS))
    persona = rng.choice(PERSONAS)
    style = rng.choice(STYLES)
    seed = rng.random() < 0.8
    name = rng.choice(DEVICE_NAMES[device][region])

    def pick(group: str) -> Optional[dict]:
        pool = [f for f in faults if cues.get(f["fault_code"], {}).get(group)]
        return rng.choice(pool) if pool else None

    target: Optional[dict]
    if category in ("safety", "safety_denied"):
        pool = [f for f in faults if cues.get(f["fault_code"], {}).get("never_exclude")]
        if category == "safety_denied":
            pool = [f for f in pool if cues[f["fault_code"]].get("cause")]
        target = rng.choice(pool) if pool else None
    elif category in ("done", "keep_not_yet", "keep_intent"):
        target = pick("done")
    elif category == "cause":
        target = pick("cause")
    elif category == "absent":
        target = pick("absent")
    else:
        target = rng.choice(faults)
    if target is None or not target.get("symptoms_vi"):
        return None
    code = target["fault_code"]
    cue = cues.get(code, {})
    if cue.get("never_exclude") and category in ("done", "cause", "absent", "multi", "ask"):
        return None
    keep_top = False
    answers = ""
    expect_device = ""
    expect_top3: List[str] = []
    expect_urgent = False
    expect_status = ""
    symptom = rng.choice(target["symptoms_vi"])
    if category in ("safety", "safety_denied"):
        # Only symptoms that describe danger in words: "máy lạnh chạy" is in a
        # safety fault's list for retrieval reasons and warns of nothing.
        danger = ("khói", "khét", "cháy", "tia lửa", "chập", "nổ", "giật", "rò điện", "mùi gas", "hơi gas", "rò gas", "tê tay", "xẹt")
        loud = [s for s in target["symptoms_vi"] if any(w in s.lower() for w in danger)]
        if not loud:
            return None
        symptom = rng.choice(loud)
    if category.startswith("keep") and any(_fold(d).lower() in _fold(symptom).lower() for d in cue.get("done", [])):
        # The symptom itself reports the fix ("mới thay pin tháng trước mà đã
        # hết"); a "keep" case built on it would contradict its own opening.
        return None
    opening = _open(persona, region, name, symptom, rng)
    sym = _short(symptom)

    def done_turn() -> str:
        d = rng.choice(cue["done"])
        before = rng.choice(_DONE_BEFORE)
        after = rng.choice(_DONE_AFTER)
        tail = rng.choice(_DONE_TAIL)
        return _fill(f"{before} {d} {after} {tail}", rng, region, sym=sym)

    def cause_turn() -> str:
        c = rng.choice(cue["cause"])
        template = rng.choice(_CAUSE_BEFORE + _CAUSE_AFTER)
        return _fill(template, rng, region, c=c)

    def absent_turn() -> str:
        a = rng.choice(cue["absent"])
        return _fill(rng.choice(_ABSENT), rng, region, a=a)

    must_not: List[str] = []
    must_keep: List[str] = []
    deny_last = False
    via = "diagnose"
    turns = [opening]

    if category == "done":
        turns.append(done_turn())
        must_not = [code]
    elif category == "cause":
        turns.append(cause_turn())
        must_not = [code]
    elif category == "absent":
        turns.append(absent_turn())
        must_not = [code]
    elif category == "previous":
        turns.append(rng.choice(_PREVIOUS[region]))
        deny_last = True
    elif category == "ask":
        kinds = [k for k in ("done", "cause", "absent") if cue.get(k)]
        if not kinds or cue.get("never_exclude"):
            return None
        kind = rng.choice(kinds)
        turns.append({"done": done_turn, "cause": cause_turn, "absent": absent_turn}[kind]())
        turns.append(rng.choice(_ASK[region]))
        must_not = [code]
        via = "ask"
    elif category == "multi":
        # Two exclusions in one message, or across two turns.
        others = [
            f for f in faults
            if f["fault_code"] != code
            and not cues.get(f["fault_code"], {}).get("never_exclude")
            and (cues.get(f["fault_code"], {}).get("done") or cues.get(f["fault_code"], {}).get("cause"))
        ]
        kinds = [k for k in ("done", "cause", "absent") if cue.get(k)]
        if not others or not kinds:
            return None
        other = rng.choice(others)
        ocue = cues[other["fault_code"]]
        first = {"done": done_turn, "cause": cause_turn, "absent": absent_turn}[rng.choice(kinds)]()
        if ocue.get("done"):
            second = _fill(f"{rng.choice(_DONE_BEFORE)} {rng.choice(ocue['done'])} {rng.choice(_DONE_AFTER)}", rng, region)
        else:
            second = _fill(rng.choice(_CAUSE_BEFORE), rng, region, c=rng.choice(ocue["cause"]))
        if rng.random() < 0.5:
            turns.append(f"{first}, {second}")
        else:
            turns += [first, second]
        must_not = [code, other["fault_code"]]
    elif category == "keep_not_yet":
        turns.append(_fill(rng.choice(_NOT_YET), rng, region, d=rng.choice(cue["done"])))
        must_keep = [code]
    elif category == "keep_intent":
        turns.append(_fill(rng.choice(_INTENT), rng, region, d=rng.choice(cue["done"])))
        must_keep = [code]
    elif category == "keep_new_symptom":
        others = [f for f in faults if f["fault_code"] != code and f.get("symptoms_vi")]
        if not others:
            return None
        other = rng.choice(others)
        turns.append(_fill(rng.choice(["còn {s} nữa", "với lại {s}", "thêm cái {s}", "{s} luôn {end}", "mà còn {s}"]),
                           rng, region, s=rng.choice(other["symptoms_vi"])))
        must_keep = [code, other["fault_code"]]
    elif category == "keep_negated_other":
        others = [f for f in faults if f["fault_code"] != code and f.get("symptoms_vi")]
        if not others:
            return None
        other = rng.choice(others)
        s = rng.choice(other["symptoms_vi"])
        if s.split()[0] in ("không", "chẳng", "chưa"):
            return None
        turns.append(_fill(rng.choice(["không có {s}", "không bị {s} gì hết", "có {s} đâu", "{me} không thấy {s}"]),
                           rng, region, s=s))
        must_keep = [code]
    elif category in ("answer_yes", "answer_no"):
        if rng.random() < 0.6:
            turns = [_fill(rng.choice(_VAGUE), rng, region, n=name)]
        turns.append(rng.choice(_YES if category == "answer_yes" else _NO))
        answers = "yes" if category == "answer_yes" else "no"
    elif category == "deny_and_hint":
        others = [f for f in faults if f["fault_code"] != code and f.get("symptoms_vi")]
        if not others:
            return None
        other = rng.choice(others)
        turns.append(_fill(rng.choice([
            "{no}, mà nó còn {s}", "{no}, {me} thấy {s}", "{no} đâu, nó {s} cơ", "{no}, kiểu như là {s}",
            "{no}. Nó {s}",
        ]), rng, region, no=rng.choice(_PREVIOUS[region]), s=rng.choice(other["symptoms_vi"])))
        deny_last = True
        expect_top3 = [other["fault_code"]]
    elif category == "retract":
        if not cue.get("done") or cue.get("never_exclude"):
            return None
        d = rng.choice(cue["done"])
        turns.append(_fill(f"{rng.choice(_DONE_BEFORE)} {d} {rng.choice(_DONE_AFTER)}", rng, region))
        turns.append(_fill(rng.choice(_RETRACT), rng, region, d=d))
        must_keep = [code]
    elif category == "correct_device":
        others = [d for d in (by_device or {}) if d != device and d in DEVICE_NAMES]
        if not others:
            return None
        other = rng.choice(others)
        ofault = rng.choice([f for f in by_device[other] if f.get("symptoms_vi")])
        oname = rng.choice(DEVICE_NAMES[other][region])
        turns.append(_fill(rng.choice([
            "à nhầm, không phải {n0} mà là {n}", "{me} nói nhầm, là cái {n} chứ không phải {n0}",
            "không phải {n0} đâu, {n} mới đúng", "sửa lại: {n} nhé, không phải {n0}",
        ]), rng, region, n=oname, n0=name))
        turns.append(rng.choice(ofault["symptoms_vi"]))
        expect_device = other
    elif category == "pronoun":
        others = [s for s in target["symptoms_vi"] if s != symptom]
        if not others:
            return None
        turns.append(_fill(rng.choice(_PRONOUN), rng, region, s=rng.choice(others)))
        expect_device = device
        expect_top3 = [code]
    elif category == "confirm":
        turns.append(rng.choice(_CONFIRM[region]))
        keep_top = True
    elif category == "thanks":
        turns.append(rng.choice(_THANKS))
        keep_top = True
        via = "ask"
    elif category == "price_followup":
        kinds = [k for k in ("done", "cause", "absent") if cue.get(k)]
        if kinds and not cue.get("never_exclude") and rng.random() < 0.6:
            turns.append({"done": done_turn, "cause": cause_turn, "absent": absent_turn}[rng.choice(kinds)]())
            must_not = [code]
        turns.append(rng.choice(_PRICE))
        via = "ask"
    elif category == "worry_question":
        turns.append(rng.choice(_WORRY))
        keep_top = True
        via = "ask"
    elif category == "safety":
        expect_urgent = True
    elif category == "safety_denied":
        turns.append(_fill(rng.choice(_SAFETY_DENY), rng, region, c=rng.choice(cue["cause"])))
        # Never switched off by a sentence: the warning stays.
        expect_urgent = True
        must_keep = [code]
    elif category == "switch_device":
        others = [d for d in (by_device or {}) if d != device and d in DEVICE_NAMES]
        if not others:
            return None
        other = rng.choice(others)
        ofault = rng.choice([f for f in by_device[other] if f.get("symptoms_vi")])
        oname = rng.choice(DEVICE_NAMES[other][region])
        turns.append(_fill(rng.choice([
            "à còn cái {n} nhà {me} nữa, {s}", "thôi khoan, giờ cái {n} mới gấp, {s}",
            "cái {n} cũng bị nè, {s}", "hỏi luôn cái {n}: {s}",
        ]), rng, region, n=oname, s=rng.choice(ofault["symptoms_vi"])))
        expect_device = other
    elif category == "offtopic":
        turns.append(rng.choice(_OFFTOPIC))
        via = "ask"
        expect_status = "refused"
    elif category == "offtopic_return":
        turns.append(rng.choice(_OFFTOPIC))
        turns.append(rng.choice(_RETURN))
        via = "ask"
        expect_device = device
        keep_top = True
    elif category == "added_symptom":
        others = [s for s in target["symptoms_vi"] if s != symptom]
        if not others:
            return None
        turns.append(_fill(rng.choice(["còn {s} nữa", "với lại {s}", "à quên, {s} luôn"]), rng, region, s=rng.choice(others)))
        expect_top3 = [code]
    elif category == "greeting_first":
        turns = [rng.choice(_GREET), opening]
        expect_top3 = [code]
    elif category == "split_symptom":
        others = [s for s in target["symptoms_vi"] if s != symptom]
        if not others:
            return None
        turns = [f"{name} nhà {REGIONS[region]['self'][0]} bị hỏng", symptom, rng.choice(others)]
        expect_top3 = [code]
    else:
        raise ValueError(category)

    turns = [_tidy(t) for t in turns]
    turns = [styled(t, style, rng) for t in turns]
    turns = [t for t in turns if t.strip()]
    return Dialogue(
        device=device,
        turns=turns,
        must_not=must_not,
        via=via,
        persona=persona,
        region=region,
        style=style,
        must_keep=must_keep,
        deny_last=deny_last,
        seed_device=seed,
        category=category,
        note="generated",
        keep_top=keep_top,
        expect_device=expect_device,
        expect_top3=expect_top3,
        expect_urgent=expect_urgent,
        expect_status=expect_status,
        answers=answers,
    )


def generate(limit: int = 2000, seed: int = 20261014, devices: Optional[Sequence[str]] = None) -> List[Dialogue]:
    """`limit` dialogues, reproducibly from `seed`, spread over every appliance."""
    by_device, cues = _load()
    names = sorted(d for d in by_device if d in DEVICE_NAMES and (not devices or d in devices))
    rng = random.Random(seed)
    out: List[Dialogue] = []
    seen = set()
    attempts = 0
    while len(out) < limit and attempts < limit * 30:
        attempts += 1
        device = names[attempts % len(names)]
        category = CATEGORIES[(attempts // len(names)) % len(CATEGORIES)]
        dialogue = _one(category, device, by_device[device], cues, rng, by_device)
        if dialogue is None:
            continue
        key = (dialogue.device, tuple(dialogue.turns), dialogue.via)
        if key in seen:
            continue
        seen.add(key)
        out.append(dialogue)
    return out


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in generate(int(sys.argv[1]) if len(sys.argv) > 1 else 40):
        print(f"[{d.category}/{d.region}/{d.persona}/{d.style}] {d.device}: {' | '.join(d.turns)}  must_not={d.must_not} keep={d.must_keep}")
