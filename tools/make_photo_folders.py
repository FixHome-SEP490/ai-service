"""Lay out the folders photographs get dropped into, one per device type.

Names must match `device_type` exactly, because `collect_images.py import-tree`
files a folder by its name and refuses one it does not recognise. Getting a name
wrong is not an error that shows up until the detector has been trained on
mislabelled data, so the folders are generated rather than typed.

Each folder gets a note in Vietnamese saying what belongs in it, what does not,
and which class it is most often confused with. The confusions are the useful
part: a sink and a tap share almost every photo, and an oven and a microwave
look alike enough that a mixed folder teaches the detector the wrong boundary.

    python tools/make_photo_folders.py create --at D:/anh-fixhome
    python tools/make_photo_folders.py status --at D:/anh-fixhome
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif"}

# target, what belongs, what does not, and the neighbour it is confused with
GUIDE: Dict[str, dict] = {
    "air_conditioner": {
        "target": 1500,
        "include": [
            "Dàn lạnh treo tường trong nhà, đủ các hãng Daikin, Panasonic, LG, Casper, Aqua, Midea",
            "Cục nóng đặt ngoài ban công hoặc gắn tường ngoài",
            "Máy lạnh âm trần, áp trần nếu có",
            "Máy lạnh đang chảy nước, bám bụi, ố vàng vì dùng lâu",
        ],
        "avoid": [
            "Quạt điều hoà hơi nước, đây là thiết bị khác hẳn",
            "Máy hút ẩm, máy lọc không khí",
            "Ảnh chỉ có remote mà không thấy máy",
        ],
        "confused_with": "Máy lọc không khí và quạt điều hoà, cả hai đều là hộp trắng gắn tường hoặc đặt sàn",
    },
    "ceiling_fan": {
        "target": 1200,
        "include": [
            "Quạt trần cánh sắt, cánh gỗ, cánh nhựa",
            "Quạt trần đèn, quạt trần trang trí",
            "Chụp từ dưới nhìn lên và chụp ngang tầm nếu trần thấp",
        ],
        "avoid": [
            "Quạt hút gắn trần nhà vệ sinh",
            "Đèn trần không có cánh quạt",
        ],
        "confused_with": "electric_fan. Quạt trần gắn cố định trên trần, quạt cây và quạt bàn đứng dưới sàn",
    },
    "electric_fan": {
        "target": 1500,
        "include": [
            "Quạt cây, quạt bàn, quạt hộp, quạt treo tường",
            "Các hãng phổ biến Asia, Senko, Điện Cơ Thống Nhất, Panasonic",
            "Quạt cũ bám bụi, lồng quạt gỉ",
        ],
        "avoid": [
            "Quạt trần, đã có thư mục riêng",
            "Quạt công nghiệp cỡ lớn trong nhà xưởng",
        ],
        "confused_with": "ceiling_fan. Phân biệt bằng chỗ đặt: đứng dưới sàn hay gắn trên trần",
    },
    "washing_machine": {
        "target": 1500,
        "include": [
            "Máy giặt cửa trên, lồng đứng, đây là loại phổ biến nhất ở Việt Nam",
            "Máy giặt cửa ngang",
            "Các hãng Aqua, Toshiba, Sanyo, LG, Samsung, Electrolux, Panasonic",
            "Máy đặt trong nhà tắm, ban công, gầm cầu thang, đúng chỗ người Việt hay để",
        ],
        "avoid": [
            "Máy sấy quần áo",
            "Máy rửa chén",
        ],
        "confused_with": "Máy sấy và máy rửa chén, cùng là hộp vuông có cửa tròn hoặc cửa vuông",
    },
    "refrigerator": {
        "target": 1200,
        "include": [
            "Tủ lạnh một cửa, hai cửa, side by side, multi door",
            "Các hãng Aqua, Sanyo, Toshiba, Panasonic, LG, Samsung, Funiki",
            "Tủ đang mở cửa thấy bên trong cũng được",
        ],
        "avoid": [
            "Tủ đông, tủ mát bán hàng, tủ trưng bày siêu thị",
            "Tủ quần áo",
        ],
        "confused_with": "Tủ đông và tủ mát thương mại. Chỉ lấy tủ lạnh gia đình",
    },
    "microwave_oven": {
        "target": 1200,
        "include": [
            "Lò vi sóng để bàn, lò vi sóng âm tủ",
            "Các hãng Sharp, Panasonic, Electrolux, Sunhouse, Toshiba",
            "Chụp thấy rõ mặt cửa kính và bảng điều khiển",
        ],
        "avoid": [
            "Lò nướng thùng, nồi chiên không dầu",
        ],
        "confused_with": "oven. Đây là cặp nhầm nặng nhất. Lò vi sóng có cửa kính tối màu và bảng phím số, lò nướng thùng có thanh nhiệt nhìn thấy được bên trong",
    },
    "oven": {
        "target": 1200,
        "include": [
            "Lò nướng thùng để bàn, thấy rõ thanh nhiệt bên trong",
            "Lò nướng âm tủ",
            "Các hãng Sunhouse, Sanaky, Lock&Lock, Bosch",
        ],
        "avoid": [
            "Lò vi sóng",
            "Nồi chiên không dầu, nồi nướng điện tròn",
        ],
        "confused_with": "microwave_oven. Nếu không chắc thì bỏ tấm đó đi, đừng đoán",
    },
    "gas_stove": {
        "target": 1500,
        "include": [
            "Bếp gas đôi để bàn, loại phổ biến nhất trong bếp Việt",
            "Bếp gas đơn mini dùng bình gas mini",
            "Bếp gas âm, bếp gas hồng ngoại",
            "Các hãng Rinnai, Namilux, Sunhouse, Paloma, Kangaroo",
            "Bếp bám dầu mỡ, họng lửa đóng cặn, đúng tình trạng thật",
        ],
        "avoid": [
            "Bếp từ, bếp hồng ngoại điện, hai loại này không dùng gas",
            "Bếp than, bếp củi",
        ],
        "confused_with": "Bếp từ và bếp điện. Bếp gas có kiềng sắt và núm vặn, bếp từ mặt kính phẳng",
    },
    "kettle": {
        "target": 1000,
        "include": [
            "Ấm siêu tốc nhựa và inox",
            "Bình đun nước có đế rời",
            "Các hãng Sunhouse, Lock&Lock, Philips, Sharp",
        ],
        "avoid": [
            "Bình thuỷ điện, bình giữ nhiệt",
            "Ấm đun trên bếp gas",
        ],
        "confused_with": "Bình thuỷ điện, cùng hình dáng nhưng có nắp bơm",
    },
    "television": {
        "target": 1200,
        "include": [
            "Tivi treo tường trong phòng khách, đúng bối cảnh thật",
            "Tivi đặt trên kệ",
            "Các hãng Samsung, LG, Sony, TCL, Casper, Asanzo",
            "Tivi đang tắt, đang bật, màn hình bị sọc hoặc tối",
        ],
        "avoid": [
            "Màn hình máy tính",
            "Ảnh sản phẩm nền trắng, thứ này đã có nhiều rồi",
        ],
        "confused_with": "Màn hình máy tính. Ưu tiên ảnh chụp trong nhà thật thay vì ảnh catalogue",
    },
    "sink": {
        "target": 1000,
        "include": [
            "Bồn rửa chén inox một hộc, hai hộc",
            "Lavabo rửa mặt trong nhà tắm",
            "Chụp toàn bộ bồn, kể cả khi có vòi trong khung",
        ],
        "avoid": [
            "Ảnh chỉ thấy vòi nước cận cảnh, để vào faucet",
            "Bồn tắm",
        ],
        "confused_with": "faucet. Hai thứ này gần như luôn nằm chung một khung hình. Quy tắc: thấy rõ lòng bồn thì là sink, chỉ cận cảnh vòi thì là faucet",
    },
    "faucet": {
        "target": 1000,
        "include": [
            "Vòi lavabo, vòi rửa chén, vòi gắn tường",
            "Vòi sen tắm, sen cây",
            "Vòi bị rỉ nước, đóng cặn vôi, gỉ sét",
        ],
        "avoid": [
            "Ảnh lấy cả bồn rửa làm chủ thể, để vào sink",
        ],
        "confused_with": "sink. Xem quy tắc ở thư mục sink",
    },
    "toilet": {
        "target": 1000,
        "include": [
            "Bồn cầu một khối, hai khối, bồn cầu treo tường",
            "Các hãng Inax, Viglacera, Toto, American Standard, Caesar",
            "Chụp cả két nước phía sau",
        ],
        "avoid": [
            "Bồn tiểu nam",
            "Bồn cầu ngồi xổm kiểu cũ, trừ khi nhóm quyết định hỗ trợ",
        ],
        "confused_with": "Bidet và bồn tiểu",
    },
    "power_outlet": {
        "target": 2000,
        "include": [
            "Ổ cắm âm tường hai chấu và ba chấu kiểu Việt Nam",
            "Mặt công tắc kèm ổ cắm, các hãng Panasonic, Sino, Điện Quang, Schneider",
            "Ổ cắm kéo dài, ổ cắm đa năng, hãng Lioa, Điện Quang",
            "Ổ cắm bị cháy đen, chảy nhựa, lỏng chân",
            "Ổ cắm đang cắm phích, thấy dây nhợ lộn xộn",
        ],
        "avoid": [
            "Ổ cắm kiểu Mỹ chân dẹt và ổ tròn kiểu châu Âu Schuko, đã có 2423 ảnh loại này rồi và đó chính là vấn đề",
            "Ổ cắm công nghiệp",
        ],
        "confused_with": "light_bulb, vì mặt công tắc đèn và mặt ổ cắm hay nằm chung một tấm. Chủ thể là lỗ cắm thì thuộc về đây",
    },
    "light_bulb": {
        "target": 1200,
        "include": [
            "Bóng đèn LED bulb, đèn tuýp LED, đèn LED âm trần downlight",
            "Đèn ốp trần, đèn máng, đèn huỳnh quang cũ",
            "Các hãng Điện Quang, Rạng Đông, Philips",
            "Đèn đã cháy, đen đầu, máng đèn hoen rỉ",
        ],
        "avoid": [
            "Đèn trang trí, đèn chùm pha lê phức tạp",
            "Đèn pin, đèn xe",
        ],
        "confused_with": "power_outlet nếu trong khung có cả công tắc. Chủ thể là nguồn sáng thì thuộc về đây",
    },
    "water_heater": {
        "target": 1500,
        "include": [
            "Bình nóng lạnh gián tiếp treo tường, hãng Ariston, Ferroli, Rossi, Picenza",
            "Máy nước nóng trực tiếp gắn tường phòng tắm, hãng Panasonic, Centon, Rheem",
            "Bình nóng lạnh năng lượng mặt trời đặt trên mái",
            "Bình bị rỉ nước, tường dưới bình bị ố",
        ],
        "avoid": [
            "Máy lọc nước nóng lạnh uống trực tiếp",
            "Cây nước nóng lạnh văn phòng",
        ],
        "confused_with": "Máy lọc nước và cây nước. Bình nóng lạnh gắn trong nhà tắm và nối với vòi sen",
    },
    "water_pipe": {
        "target": 1000,
        "include": [
            "Đường ống nước PPR, ống nhựa PVC trong nhà, hãng Bình Minh, Hoa Sen, Tiền Phong",
            "Mối nối ống, co, tê, van khoá",
            "Ống đang rò rỉ, mối nối rỉ sét, tường ẩm quanh ống",
            "Ống nước lộ thiên sau nhà, dưới gầm bồn rửa",
        ],
        "avoid": [
            "Ống gas, ống điều hoà",
            "Ống cấp nước công nghiệp cỡ lớn",
        ],
        "confused_with": "Ống gas và ống dẫn của điều hoà, hình dáng tương tự nhưng thuộc hệ thống khác",
    },
}

_TEMPLATE = """# {name_vi}  ({device_type})

Mục tiêu: khoảng {target} ảnh.

## Bỏ ảnh gì vào đây
{include}

## Không bỏ vào đây
{avoid}

## Hay bị nhầm với
{confused_with}

## Lưu ý chung
Ảnh chụp trong nhà thật, ánh sáng thật, có đồ đạc xung quanh thì giá trị hơn ảnh
sản phẩm nền trắng. Dataset công khai đã thừa ảnh catalogue rồi, cái đang thiếu
là ảnh giống thứ khách hàng sẽ gửi lên.

Đa dạng thiết bị quan trọng hơn số lượng ảnh. Một trăm thiết bị khác nhau, mỗi
cái vài góc, có giá trị hơn nhiều so với năm tấm của cùng một cái nhân lên.

Chấp nhận jpg, jpeg, png, webp, bmp, heic. Ảnh nhỏ hơn 300px sẽ bị loại khi nạp.
Không cần đổi tên hay sắp xếp gì, cứ đổ vào đây.

{detector_note}
"""

_NOT_DETECTOR = """## Ghi chú
Lớp này hiện không nằm trong bộ nhận diện bằng ảnh, nhưng ảnh vẫn hữu ích cho
phần đọc dấu hiệu hư hại và cho việc mở rộng sau này."""

_README = """# Ảnh huấn luyện FixHome

Mỗi thư mục con là một loại thiết bị. **Tên thư mục phải giữ nguyên**, vì công cụ
nạp ảnh nhận diện loại thiết bị bằng đúng tên đó và sẽ bỏ qua thư mục lạ thay vì
đoán bừa. Xếp ảnh nhầm thư mục là lỗi không lộ ra cho tới khi mô hình đã học xong.

Mở file `_HUONG_DAN.md` trong từng thư mục để biết bỏ ảnh gì vào.

## Nạp vào dự án khi xong

    cd "D:/A FPT/A Term 9 FPT end game/Đồ Án/repo/ai-service"
    python tools/collect_images.py import-tree --from D:/anh-fixhome

Công cụ tự lọc ảnh trùng theo nội dung, thu nhỏ ảnh quá lớn, loại ảnh dưới 300px
và file không phải ảnh. Không cần dọn dẹp trước.

## Cảnh báo về ảnh thu thập tự động

Dự án đã thử cào ảnh từ Google và Bing và phải bỏ toàn bộ kết quả. Google đổi cấu
trúc trang nên không đọc được, còn Bing trả nội dung không liên quan cho công cụ
không phải trình duyệt: tìm "ổ cắm điện Panasonic" ra poster đồ án kiến trúc và
một đĩa gà rán, tìm "electrical wall socket" ra hộp mô hình máy bay.

Điểm nguy hiểm là **không có lỗi nào được báo**, số lượng ảnh vẫn tăng đều.

Nên nếu ảnh đến từ công cụ tự động, hãy mở ngẫu nhiên vài chục tấm mỗi thư mục
xem trước khi nạp. Mất mười phút, và rẻ hơn nhiều so với phát hiện sau khi train.

## Bảng mục tiêu

| Thư mục | Thiết bị | Mục tiêu |
| --- | --- | --- |
{rows}
"""


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def cmd_create(args: argparse.Namespace) -> None:
    root = Path(args.at).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog()

    rows = []
    created = existing = 0
    for device in catalog["devices"]:
        device_type = device["device_type"]
        guide = GUIDE.get(device_type)
        if guide is None:
            print(f"{device_type}: no guidance written, skipped")
            continue

        folder = root / device_type
        if folder.exists():
            existing += 1
        else:
            folder.mkdir(parents=True)
            created += 1

        note = "" if device.get("detector_class") else _NOT_DETECTOR
        (folder / "_HUONG_DAN.md").write_text(
            _TEMPLATE.format(
                name_vi=device["name_vi"],
                device_type=device_type,
                target=guide["target"],
                include=_bullets(guide["include"]),
                avoid=_bullets(guide["avoid"]),
                confused_with=guide["confused_with"],
                detector_note=note,
            ),
            encoding="utf-8",
        )
        rows.append(f"| `{device_type}` | {device['name_vi']} | {guide['target']} |")

    (root / "README.md").write_text(
        _README.format(rows="\n".join(rows)), encoding="utf-8"
    )

    total = sum(g["target"] for g in GUIDE.values())
    print(f"\n{root}")
    print(f"  {created} thư mục mới, {existing} đã có sẵn")
    print(f"  tổng mục tiêu: {total} ảnh trên {len(rows)} loại thiết bị")
    print("  mỗi thư mục có _HUONG_DAN.md, thư mục gốc có README.md")


def cmd_status(args: argparse.Namespace) -> None:
    root = Path(args.at).expanduser()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    catalog = {d["device_type"]: d for d in load_catalog()["devices"]}
    print(f"{'folder':<20}{'have':>8}{'target':>8}{'short':>8}")

    total_have = 0
    for device_type, guide in GUIDE.items():
        folder = root / device_type
        have = (
            sum(1 for p in folder.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES)
            if folder.is_dir()
            else 0
        )
        total_have += have
        mark = " " if folder.is_dir() else "?"
        print(
            f"{mark}{device_type:<19}{have:>8}{guide['target']:>8}"
            f"{max(0, guide['target'] - have):>8}"
        )

    unknown = [
        d.name
        for d in root.iterdir()
        if d.is_dir() and d.name not in GUIDE
    ]
    if unknown:
        print("\nThư mục không phải tên thiết bị, sẽ bị bỏ qua khi nạp:")
        for name in unknown:
            print(f"  {name}")
        print(f"\nTên hợp lệ: {', '.join(sorted(catalog))}")

    target = sum(g["target"] for g in GUIDE.values())
    print(f"\nTotal {total_have} / {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create every folder with its note")
    create.add_argument("--at", required=True)

    status = sub.add_parser("status", help="how many images each folder holds")
    status.add_argument("--at", required=True)

    args = parser.parse_args()
    {"create": cmd_create, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    main()
