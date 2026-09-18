# Phát triển chatbot từ đây: làm gì, theo thứ tự nào, và bằng cách nào

Ghi lại ngày 18/09/2026, sau khi chạy bộ 564 ca với mô hình thật lần đầu tiên.
File này dành cho người tiếp tục công việc, kể cả là chính mình ở phiên sau.

## Trạng thái hiện tại, bằng số

Đo trên máy thuê với Qwen thật, không phải stub:

| | |
|---|---|
| hành vi đúng loại (chẩn đoán / hỏi / trả lời / từ chối) | **529/564 = 93,8%** |
| trả lời nghiệp vụ | 33/33 = 100% |
| từ chối câu ngoài phạm vi | 15/15 = 100% |
| nhận đúng thiết bị | 447/498 = 89,8% |
| **nhận đúng mã bệnh** | **432/564 = 76,6%** |
| có dịch vụ đặt được | 486/516 = 94,2% |
| lỗi HTTP | 0 |
| ý định đặt lịch | 38/38 nhận ra, 11/11 ra nút |
| test tự động | 1.906 |

Truy hồi đo riêng ngoại tuyến: **472/472** danh sách bệnh, 19/19 văn bản, 9/9
nghiệp vụ, **10/10 ghim cảnh báo an toàn**, 15/15 im lặng.

## Vòng lặp cải tiến, đây là phần quan trọng nhất của file này

Cả ngày 18/09 tìm ra mười lỗi, và **không lỗi nào tìm được bằng cách đọc code**.
Tất cả đều lộ ra khi **chạy thật rồi so với kỳ vọng**. Vòng lặp:

1. Chạy bộ ca với mô hình thật trên máy thuê:
   `AI_SERVICE_URL=<địa chỉ> python tools/eval_chat_suite.py --out docs/chat-suite-results.json`
2. Đọc **danh sách ca sai ở cuối**, không đọc con số tổng. Công cụ đã chia sẵn
   theo loại sai, và các loại **không nặng như nhau**.
3. Với mỗi loại, viết một đoạn mã nhỏ **đo riêng** loại đó trên nhiều cách nói,
   không chỉ ca trong bộ. Ví dụ ý định đặt lịch: viết 38 cách khách thật sẽ nói,
   đo được 13, sửa, đo lại.
4. **Đo cả hai chiều.** Mọi lần mở rộng nhận dạng đều phải kiểm ca *không được
   nhận*. Ngày 18/09 mở rộng nhận dạng đặt lịch xong thì 8 câu triệu chứng thật
   bị hiểu thành đặt lịch.
5. **Quét toàn bộ kho tri thức làm bộ phủ định.** 2.154 câu triệu chứng viết tay
   là bộ ca âm tốt nhất đang có, và nó tự lớn lên khi viết thêm tài liệu:

       for d in kb.device_types:
           for f in kb.faults_for_device(d):
               for s in f.symptoms_vi:
                   assert not <hàm nhận dạng>(s)

6. Ghim thành test **sinh ca từ catalog** chứ không liệt kê tay, để thêm thiết bị
   là tự soi.
7. Merge → **chờ image build xong (~13 phút)** → dựng lại máy → đo lại. Bỏ bước
   chờ build là test đúng code cũ.

## Thứ tự việc nên làm tiếp

### 1. Mã bệnh 76,6% — việc lớn nhất còn lại

Bộ 564 ca chia sẵn ba loại sai, độ nặng khác nhau rõ rệt:

**Đúng thiết bị nhưng sai bệnh (82 ca)** — nặng trung bình. Khách vẫn được đúng
thiết bị và đúng nhóm dịch vụ, chỉ là mã bệnh lệch. Ví dụ `bếp gas lửa đỏ có sao
không` ra `STOVE_FLAME_OUT` thay vì `STOVE_BURNER_CLOGGED`. Cách sửa: thêm câu
triệu chứng thật vào tài liệu mã bệnh đúng, **không** sửa thuật toán. Ba lần sửa
thuật toán trong quá khứ đều bị revert, một lần làm mất hai ghim an toàn.

**Đúng loại nhưng sai thiết bị (19 ca)** — nặng hơn. `quạt bị rò điện` ra mã ổ
cắm. Cách sửa: alias thiết bị, và cân nhắc cặp dễ nhầm.

**Từ chối oan (7 ca)** — nặng nhất, khách bị đuổi. Ngày 18/09 sửa hết 7: ba ca do
bỏ dấu (`mô tơ`→`o to`, `đọng hoài`→`dong ho`), ba ca do khoá thông minh thiếu
alias, một ca do cổng phạm vi xoá chữ đ.

Làm theo thứ tự ngược độ nặng: từ chối oan trước, rồi sai thiết bị, rồi sai bệnh.

### 2. Lớp máy sấy quần áo 69,1%

Yếu nhất của detector, và **không sửa bằng train thêm** — đường cong đã phẳng từ
epoch 60. Cần **ảnh chụp thật trong điều kiện thật**. Nó nhầm thành máy giặt
nhiều nhất, mà máy giặt cửa ngang với máy sấy cửa ngang là **cùng một tấm ảnh**,
nên phần này đã được xử ở tầng hội thoại: hỏi "máy nhà mình là máy giặt, máy sấy
quần áo, hay máy rửa bát ạ?" rồi mới chẩn đoán.

### 3. Chữ nghĩa do mô hình viết

Lỗi duy nhất tìm được ở đây là **nhại khung prompt** — 6/471 = 1,3%, đã sửa bằng
cách bóc sau khi sinh. Đừng sửa bằng prompt: mô hình 3B **chép lại câu cấm**.

Chưa có thước đo cho *chất lượng* câu chữ, chỉ có thước đo cho *có đúng mã bệnh
không*. Đây là khoảng trống lớn nhất về phương pháp. Muốn đo thì phải có người
đọc và cho điểm một mẫu, hoặc dùng một mô hình lớn hơn làm giám khảo.

### 4. Việc cần người, không phải cần code

- **821 mục** trong kho tri thức cần **thợ có nghề** xác nhận, danh sách gom sẵn
  ở `docs/CAN-THO-XAC-NHAN.md`, sinh bằng `python tools/review_backlog.py`. Phần
  lớn là chu kỳ bảo dưỡng và khoảng giá từng dòng máy. Viết được kiến thức phổ
  thông, không viết thay được kinh nghiệm hiện trường.
- **36 giá ước lượng** chờ Admin duyệt.

### 5. Nối vào ứng dụng

- AI trả `serviceCode` mà **chưa trả `serviceId`**, nên Backend phải tự tra. Xem
  `docs/CHATBOT-BOOKING-HANDOFF.md`.
- Luồng **"Đặt thợ ngay"** trên mobile chưa làm: danh sách dịch vụ → RAG → gợi ý
  → nút → sang màn đặt lịch có lọc sẵn. `repo/mobile` và `repo/backend` hiện chỉ
  được sửa và báo cáo, không commit.
- Bộ nhớ phiên nằm trong bộ nhớ tiến trình: khởi động lại là mất hội thoại đang
  dở, và hai worker không dùng chung. Giao diện đã viết sẵn cho một bản Redis.

## Loại lỗi lặp lại nhiều nhất, đọc kỹ

**Bỏ dấu tiếng Việt rồi khớp chuỗi con.** Ngày 18/09 gặp **bốn lần trong một
ngày**, ở bốn danh sách từ khoá khác nhau:

| từ khoá | nằm ẩn trong | hậu quả |
|---|---|---|
| `gia` (giá) | **giặt** | mọi câu về máy giặt bị coi là hỏi giá, trả lời bằng giá kính cửa |
| `re` (rẻ) | **remote** | mọi câu về điều khiển bị coi là hỏi giá |
| `o to` (ô tô) | **thợ tới**, **mô tơ** | "bao lâu thợ tới" bị từ chối là không sửa ô tô |
| `dong ho` (đồng hồ) | **đọng hoài** | ống nước không rút bị coi là đồng hồ đeo tay |
| `tho` (thợ) | **thôi**, **thoát**, **thông minh** | 8 câu triệu chứng bị coi là đặt lịch |

Luật, đã ghi trong mã nguồn nhưng vẫn bị vi phạm bốn lần:

1. **Khớp trọn từ, tuyệt đối không chuỗi con.**
2. **Không để từ khoá dưới bốn ký tự tự quyết định.**
3. **Sinh danh sách va chạm từ chính catalog**, đừng liệt kê tay — đã có test làm
   việc này trong `tests/test_keyword_collisions.py`.
4. Dùng **một hàm fold duy nhất**. Ngày 18/09 có một hàm tự copy lại cách bỏ dấu
   mà **quên đổi đ thành d**, nên `[a-z0-9]+` xoá luôn chữ đ: `bị rò điện` vào
   tới nơi thành `bi ro ien`.

## Nợ đã đo: `devices_named_in` vẫn khớp chuỗi con

**51 trong 2.154 câu triệu chứng của kho tri thức bị gán sai thiết bị** — đo bằng
cách cho mỗi câu đi qua `devices_named_in` rồi so với thiết bị mà tài liệu chứa nó
thuộc về. Đây là lần thứ **năm** loại lỗi bỏ dấu này xuất hiện, và lần này ở hàm
**trung tâm nhất**: alias được khớp bằng `in`, không phải trọn từ.

Thủ phạm nhiều nhất:

| alias | nằm ẩn trong | số ca |
|---|---|---|
| `ấm điện` → `am dien` | **cắm điện** → `cam dien` | 8 |
| `ống nước` | các câu có "ống" khác | 8 |
| `ổ điện` | câu về điện nói chung | 4 |
| `rửa bát`, `máy giặt` | câu của thiết bị khác nhắc tới | 6 |

Một alias gõ sai đã xoá: `power_outlet` có `'ổ mà'`, chắc là gõ nhầm `'ổ cắm'`, và
nó bỏ dấu thành `o ma` nằm lọt trong `do may` của câu "**d-o ma-y** quá lạnh" — một
mình nó gây 14 ca. Xoá xong 65 xuống 51.

Vì sao chưa sửa: đổi `devices_named_in` sang khớp trọn từ là **thay đổi lõi**, nó
quyết định thiết bị nào được chọn nên ảnh hưởng toàn bộ truy hồi, ghim an toàn và
mọi con số đã công bố. Phải làm khi có thời gian đo lại đầy đủ, không vá vội.

Khi làm, đo đúng bốn thứ này trước và sau: **51 ca gán sai** này, **472/472** danh
sách bệnh, **10/10 ghim an toàn**, và bộ 564 ca với mô hình thật. Và nhớ luật đã
ghi bốn lần: alias dưới bốn ký tự không được tự quyết định, và `"ấm"` trần không
được thêm vào vì nó trùng `"ẩm"` và `"âm"`.

## Những chỗ tuyệt đối không được làm hỏng

**Ghim cảnh báo an toàn 10/10.** Cảnh báo được ghim theo mã bệnh **xếp hạng
nhất**, nên *bất kỳ* thay đổi thứ hạng đều có thể lấy mất một cảnh báo — kể cả
thay đổi không làm đổi điểm, chỉ đổi thứ tự khi hoà. Đo lại con số này sau **mọi**
thay đổi truy hồi. Ba lần sửa thuật toán đã bị revert vì nó.

**Đường đặt lịch.** Khách nói muốn đặt thì phải ra dịch vụ và nút, không chẩn
đoán. 38/38 và 11/11 hiện tại được ghim bằng 107 test.

**AI hỏng không được chặn luồng đặt lịch.** Mọi đường thất bại đều phải kết thúc
bằng một dịch vụ đặt được, kể cả khi mô hình không trả lời được gì.

## Lệnh hay dùng

    # gate trước mỗi commit
    ruff check app tests tools && pytest -q

    # truy hồi, ngoại tuyến, nhanh
    python tools/eval_retrieval.py

    # toàn bộ đường đi, cần máy thuê
    AI_SERVICE_URL=<địa chỉ> python tools/eval_chat_suite.py --out docs/chat-suite-results.json

    # detector
    python tools/eval_detector.py --weights <best.pt> --split test --out docs/detector-v2-on-22class-test.json
    python tools/compare_detectors.py docs/detector-v1-on-22class-test.json docs/detector-v2-on-22class-test.json

    # danh sách cần thợ xác nhận
    python tools/review_backlog.py --out docs/CAN-THO-XAC-NHAN.md

Thuê máy: đọc `.claude/GPU-RENTAL.md` trước. Máy serve đã chốt là **machine
27076** (RTX A4000).
