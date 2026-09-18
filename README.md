<h1 align="center">FixHome — AI Service</h1>

<p align="center">
  <strong>Chẩn đoán sơ bộ thiết bị gia dụng từ ảnh và mô tả của khách</strong><br>
  <em>Tự host hoàn toàn. Không gọi API của bên thứ ba nào.</em>
</p>

<p align="center">
  <code>YOLO11s · 22 thiết bị</code> ·
  <code>Qwen2.5-VL-3B-AWQ trên vLLM</code> ·
  <code>RAG từ vựng, 3.319 đoạn</code> ·
  <code>một card 12GB</code>
</p>

---

## Bốn tầng, mỗi tầng một câu hỏi

| Tầng | Câu hỏi | Cái gì làm | Chạy ở đâu |
|---|---|---|---|
| Hội thoại | Đã biết gì rồi? | nhớ phiên, gom triệu chứng, nhận ý định đặt lịch | CPU |
| Thị giác | Đây là thiết bị gì? | YOLO11s, 22 lớp | GPU |
| Tri thức | Bệnh nào khả nghi? | 166 tài liệu → 3.319 đoạn, 134 mã bệnh | **CPU, 0 MB VRAM** |
| Ngôn ngữ | Nói bằng tiếng Việt thế nào? | Qwen2.5-VL-3B-AWQ | GPU |

Luồng: `phiên → ảnh → detector → loại thiết bị → truy hồi → danh sách bệnh kèm
trích dẫn → mô hình ngôn ngữ → lớp kiểm duyệt → phản hồi`

Mỗi tầng **bị cấm** trả lời câu của tầng khác, và điều đó được ghim bằng test chứ
không bằng lời nhắc: detector không được đặt tên bệnh, truy hồi không được viết
câu, mô hình ngôn ngữ **không được đóng góp sự thật**, tầng hội thoại không được
chẩn đoán.

**Mọi con số và mọi lời khuyên an toàn khách đọc đều đến từ một đoạn văn bản đã
truy hồi ra, và đoạn đó được trả về làm trích dẫn.** Sai một câu là truy được về
đúng tài liệu gây ra nó.

## Vì sao chia việc như vậy — đã đo, không phải phỏng đoán

**Qwen không phân biệt được thiết bị.** Nó gọi ảnh máy lạnh là "đèn sưởi", và khi
bắt phân biệt lò vi sóng với lò nướng trên 12 ảnh thì trả lời **giống hệt nhau cả
12 lần**, đảo thứ tự lựa chọn cũng không đổi. YOLO làm việc đó tốt hơn hẳn.

**Qwen cũng không nên chọn mã bệnh.** Đo trên 464 ca chẩn đoán với mô hình thật:

| | |
|---|---|
| mã bệnh đúng, truy hồi xếp **hạng nhất** | 429/464 = **92,5%** |
| mã bệnh đúng, trong **top-3** của truy hồi | 464/464 = **100%** |
| mã bệnh đúng, **Qwen tự chọn** | 340/464 = **73,3%** |

Mô hình **kém 19 điểm** so với việc chỉ lấy kết quả đầu của truy hồi, và cái giá
không chỉ là tên: chọn sai mã thì map sang sai dịch vụ. Nên **khi không có ảnh,
truy hồi dẫn đầu**. Còn **có ảnh thì mô hình vẫn quyết** — nó thấy được vết nứt,
vết cháy, nước đọng dưới máy, những thứ không nằm trong câu chữ của khách. Nửa
có-ảnh đó **chưa ai đo được**, vì bộ ca chỉ gửi chữ.

**Ngược lại YOLO không đọc được chữ.** Nó không hiểu "máy chạy cả ngày không mát",
và càng không hiểu "dù mới vệ sinh" — câu loại trừ mà chỉ mô hình ngôn ngữ đọc
được. Ba mô hình bù cho nhau đúng chỗ mỗi cái yếu.

## Khi không chắc thì hỏi, không đoán

Có những cặp thiết bị mà **một tấm ảnh về nguyên tắc không tách được**, và ma trận
nhầm lẫn của chính detector chỉ ra chúng:

| Cặp | Hỏi gì |
|---|---|
| máy giặt / máy sấy quần áo / máy rửa bát | máy dùng để làm gì (ba lựa chọn) |
| lò vi sóng / lò nướng | bên trong có đĩa thuỷ tinh xoay không |
| bếp gas / bếp từ | bếp có dùng bình gas không |
| quạt trần / quạt điện | quạt gắn ở đâu |
| chậu rửa / vòi, ổ cắm / bóng đèn | chỗ hỏng là cái nào |

Hỏi về **thứ khách nhìn thấy được**, không hỏi khách chọn nhãn — ai phân biệt được
lò vi sóng với lò nướng thì đã không cần gửi ảnh. Hỏi **đúng một lần**. Đọc được
**phủ định**: "không phải trần" là câu trả lời *quạt điện*. Và "không rõ" **không
phải** là "không".

Điều này quan trọng hơn cái tên, vì **lời khuyên an toàn của hai thiết bị trong
một cặp có thể trái ngược nhau**: bếp từ được tư vấn như bếp gas sẽ được dặn khoá
van bình gas — vô nghĩa cho thiết bị cắm điện, và tệ hơn là làm khách tin rằng vấn
đề đã được hiểu đúng.

## An toàn đi trước chẩn đoán

Một số mã bệnh có rủi ro tính mạng: rò gas, mùi khét ở ổ cắm, máy sấy tắc xơ vải.
Với những mã đó **cảnh báo được ghim lên trước** và đi trong **trường riêng**, không
trộn vào phần tài liệu tham khảo — trộn vào thì mô hình tóm tắt nó mất.

Ghim theo **mã bệnh xếp hạng nhất**, không theo cả danh sách. Hệ quả cho người bảo
trì: **bất kỳ thay đổi thứ hạng nào cũng có thể lấy mất một cảnh báo**, kể cả thay
đổi không làm đổi điểm mà chỉ đổi thứ tự khi hoà. Vì vậy **số cảnh báo ghim đúng là
một cổng chặn phát hành**, đo lại sau *mọi* thay đổi truy hồi. Ba lần sửa thuật
toán đã bị revert vì nó.

## Chạy tại máy, không cần GPU

Không có GPU thì detector và Qwen không nạp, nhưng **truy hồi, tri thức, hội thoại
và toàn bộ luật nghiệp vụ vẫn chạy** — đủ để phát triển và để chạy 1.906 test.

```bash
py -3.13 -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Mở `http://127.0.0.1:8000/chat` để chat, `http://127.0.0.1:8000/health` để kiểm.

`/health` **từ chối báo khoẻ nếu kho tri thức nạp về ít hơn 1.000 đoạn**, nên một
lần triển khai thiếu dữ liệu không thể lặng lẽ chạy với bộ não rỗng.

## Chạy đầy đủ mô hình trên GPU thuê

Đây là phần dùng nhiều nhất. Đọc **[docs/RENTING-A-GPU.md](docs/RENTING-A-GPU.md)**
để biết máy nào và năm cách nó hỏng; dưới đây là quy trình.

### 1. Image được build ở CI, không build ở máy

Hai image, build bằng GitHub Actions khi merge vào `main`:

| Image | Build khi đổi | Nội dung |
|---|---|---|
| `ghcr.io/fixhome-sep490/fixhome-serve` | `app/**`, `docker/serve/**`, `requirements.txt` | cả dịch vụ: vLLM + Qwen + YOLO + RAG + API |
| `ghcr.io/fixhome-sep490/fixhome-trainer` | `docker/train/**`, `requirements-*.txt` | môi trường train YOLO |

Build ở CI vì image serve **8,74 GB** — đẩy từ máy nhà chậm hơn build, và bản ở CI
luôn dựng từ checkout sạch. Image serve dựa trên `vllm/vllm-openai:v0.29.0` nên
CUDA, torch và vLLM đã khớp sẵn.

> **Sửa code mà chưa merge thì máy thuê không có bản sửa đó.** Chờ workflow
> `Serving image` xong (~13 phút) rồi mới dựng máy, nếu không là test đúng code cũ.

Muốn build tay: `gh workflow run "Serving image"`.

### 2. Thuê máy — đã chốt một con

```bash
# máy đã chạy thông từ đầu đến cuối: RTX A4000 16GB, CUDA 13.0, 6.8 Gb/s
python tools/rent_gpu.py offers --machine 27076
python tools/rent_gpu.py serve --offer <id vừa liệt kê>
```

Máy đó bận thì lọc theo **độ tin cậy trước, giá sau**:

```bash
python tools/rent_gpu.py offers --min-cuda 13.0 --min-download 3000
```

`serve` **tự từ chối** máy không đạt, trước khi tiêu đồng nào:

- **CUDA < 13.0** → vLLM chết với `Error 803: unsupported display driver` *sau khi*
  đã kéo 9 GB.
- **băng thông < 3 Gb/s** → image có **một tầng 5,12 GB không resume được**, nên
  link chậm không phải tải lâu mà là **không bao giờ xong**. Đo thật: 545 Mbps và
  1,4 Gb/s đều bỏ cuộc sau 33 và 19 phút; 6,8 Gb/s xong trong ~3 phút.

Điều kiện thứ ba **máy không kiểm được**: một host đạt cả hai, container khoẻ, mà
**cổng không vào được từ ngoài**. Đó là lý do phải chốt một host đã làm được việc.

### 3. Máy tự kéo image và weights, mình không đẩy gì lên

Container khi khởi động tự làm:

1. kéo image từ GHCR (cần login, `serve` truyền sẵn credential)
2. tải weights detector từ Hugging Face theo `--weights-run`
3. tải Qwen2.5-VL-3B-AWQ từ Hugging Face
4. chạy vLLM ở loopback, rồi mở API ở cổng 8000

```bash
python tools/rent_gpu.py address --instance <id>   # in ra AI_SERVICE_URL
python tools/rent_gpu.py logs --instance <id> --tail 80
python tools/rent_gpu.py status
```

Máy lên khi `/health` trả `"attached": true` cho **cả** `vlm` và `detector`.
Giao diện chat ở **`<địa chỉ>/chat`**.

### 4. Đo, rồi huỷ

```bash
AI_SERVICE_URL=<địa chỉ> python tools/eval_chat_suite.py --out docs/chat-suite-results.json
python tools/rent_gpu.py destroy --instance <id>
```

> **Máy serve KHÔNG tự huỷ** — nó phải sống để test và demo. `status` ở đầu và cuối
> mỗi phiên, và cuối phiên phải thấy `Nothing rented. No charges accruing.`
> `destroy` **hỏi lại danh sách đang thuê để kiểm chứng**, không tin câu trả lời của
> API.

Giá tham chiếu: serve **$0.08–0.13/giờ**, train 3090 **~$0.22/giờ**.

## Train lại detector

```bash
python tools/rent_gpu.py offers --gpu RTX_3090 --min-vram 24
python tools/rent_gpu.py train --offer <id> --epochs 70 --batch 48 \
    --model yolo11s.pt --run-name detector-v3
```

Máy train **tự huỷ khi xong**: entrypoint đẩy weights lên Hugging Face **trước khi**
in `Done. Results in`, nên huỷ sau mốc đó không mất gì. Nó cũng ghi một marker để
chính sách restart-on-exit của vast.ai không lặng lẽ train lại và ghi đè weights đã
publish — chuyện đã xảy ra một lần, phát hiện ở epoch thứ hai.

Train thêm vòng từ weights đã có, không làm lại từ đầu:

```bash
python tools/rent_gpu.py train --offer <id> --epochs 30 \
    --resume-from detector-v2-yolo11s/weights/best.pt --run-name detector-v2-more
```

Lấy weights về máy: `python tools/hub.py pull-weights --repo <repo> --run <tên run>`

## Số đo hiện tại

**detector-v2** — yolo11s, 22 lớp, 23.678 ảnh (18.091 / 2.808 / 2.779), 70 epoch,
RTX 3090, 3 giờ 20 phút, **$0,72**. Tập test tách bằng băm nội dung.

| | |
|---|---|
| gọi đúng tên thiết bị, 22 lớp | **85,7%** |
| 17 lớp mà detector-v1 cũng biết | 83,9% → **86,2%** |
| 5 lớp mới thêm | **82,8%** |
| mAP50 / mAP50-95 (tập val) | 0,820 / 0,715 |

Chi tiết từng lớp, gồm cả ba lớp **tụt**, ở [docs/DETECTOR-V2.md](docs/DETECTOR-V2.md).

**Hội thoại** — 564 ca với mô hình thật: hành vi đúng loại **93,8%**, nghiệp vụ
33/33, từ chối ngoài phạm vi 15/15, ý định đặt lịch **38/38** và **11/11 ra nút**.

**Truy hồi, đo ngoại tuyến** — `python tools/eval_retrieval.py`:

```
shortlist   472/472  100%      pin          10/10  100%
corpus       19/19   100%      im lặng      15/15  100%
business      9/9    100%
```

**Gate** — `ruff check app tests tools && pytest -q` → **1.906 test**.

## API

Sáu endpoint, chỉ Backend gọi, client không gọi trực tiếp:

| | |
|---|---|
| `POST /api/v1/diagnosis/analyze` | ảnh base64 + mô tả → chẩn đoán |
| `POST /api/v1/diagnosis/analyze-upload` | như trên, multipart |
| `POST /api/v1/chat/ask` | câu hỏi tự do → trả lời có trích dẫn |
| `GET /api/v1/chat/acknowledgements` | câu chờ cho client hiện |
| `GET /api/v1/meta/catalog` | danh mục thiết bị và dịch vụ |
| `GET /health` | sống chưa, và mô hình đã nạp chưa |

Phản hồi dùng camelCase cho client TypeScript của Backend.

**Phiên chat:** id do **server phát**, không nhận id client tự đặt — trường này nhận
chuỗi bất kỳ nên hai client cùng gửi `"guest"` sẽ dùng chung hội thoại, tức thiết bị
và triệu chứng của người này hiện sang người kia. Client gửi rỗng lần đầu, rồi echo
lại id trong phản hồi.

## Khi hỏng thì suy giảm, không chặn

Luật nghiệp vụ: **AI hỏng không được chặn luồng đặt lịch**. Được thi hành bằng cấu
trúc, không bằng `try/except`:

- Mô hình ngôn ngữ quá **8 giây** → trả lời bằng chính các đoạn đã truy hồi. Văn
  phong tệ hơn, nội dung vẫn đúng và vẫn có trích dẫn, và **không bao giờ là trang
  lỗi**.
- Detector không nhận ra gì → hội thoại hỏi lại.
- Không có mã bệnh nào → mời gói kiểm tra tại nhà.
- **Mọi đường thất bại đều kết thúc bằng một dịch vụ đặt được.**

Mô hình 3B **chép lại thứ nó được cho xem, kể cả câu cấm** — nên prompt chỉ nói
điều *nên* làm, còn điều không được nói thì **chặn bằng mã sau khi mô hình trả
lời**: chuẩn hoá đại từ, bóc lời xin lỗi mở đầu, từ chối mọi câu đẩy khách sang
thợ ngoài FixHome, và bóc phần nhại khung prompt.

## Bố cục

```
app/
  api/            6 endpoint
  core/           cấu hình, ngưỡng, câu mặc định
  data/
    knowledge/    166 tài liệu tiếng Việt → 3.319 đoạn
    *.json        danh mục thiết bị, bảng bệnh, map dịch vụ, bảng giá
  services/pipeline/
    detector.py     YOLO
    retriever.py    truy hồi từ vựng có trọng số độ hiếm
    qwen_client.py  vLLM + lớp kiểm duyệt đầu ra
    local_pipeline.py  điều phối
    conversation.py    trạng thái phiên
  web/chat.html   giao diện chat
docker/
  serve/          image cả dịch vụ
  train/          image train YOLO
tools/            rent_gpu, hub, eval_*, build_dataset, autolabel, ...
tests/            1.906 test
docs/             số đo, thiết kế, hợp đồng với Backend
```

Công cụ hay dùng:

| | |
|---|---|
| `tools/rent_gpu.py` | offers / train / serve / address / status / logs / destroy |
| `tools/hub.py` | đẩy dữ liệu, lấy weights từ Hugging Face |
| `tools/eval_retrieval.py` | truy hồi, ngoại tuyến, vài giây |
| `tools/eval_chat_suite.py` | 564 ca, cần máy thuê |
| `tools/eval_detector.py` | tỉ lệ gọi đúng tên, từng lớp |
| `tools/compare_detectors.py` | so hai phiên bản detector |
| `tools/review_backlog.py` | gom mục cần thợ xác nhận |

## Hai môi trường ảo, và vì sao

`.venv` chạy dịch vụ và test. `.venv-tools` chỉ chứa `vastai` và client Hugging
Face. Tách ra vì `fiftyone` từng nâng `starlette` lên bản mà `fastapi` không chạy
được, và làm hỏng môi trường chính.

## Dữ liệu

Bộ dữ liệu ảnh **không nằm trong git** — 100 MB một file là giới hạn của GitHub, và
Git LFS cho 1 GB băng thông một tháng, một lần clone là hết. Dữ liệu ở Hugging Face
Hub; `datasets/split.json` thì **có** trong git vì nó là thứ làm số đo lặp lại được
giữa các máy.

## Chưa làm

- **821 mục** trong kho tri thức cần **thợ có nghề** xác nhận — chu kỳ bảo dưỡng và
  khoảng giá từng dòng máy. Danh sách gom sẵn ở
  [docs/CAN-THO-XAC-NHAN.md](docs/CAN-THO-XAC-NHAN.md).
- **36 giá** ước lượng chờ Admin duyệt.
- Lớp **máy sấy quần áo 69,1%** — cần ảnh chụp thật, không cần thêm epoch: đường
  cong học đã phẳng từ epoch 60.
- API trả `serviceCode` mà **chưa trả `serviceId`** — xem
  [docs/CHATBOT-BOOKING-HANDOFF.md](docs/CHATBOT-BOOKING-HANDOFF.md).
- Bộ nhớ phiên nằm trong bộ nhớ tiến trình: restart là mất hội thoại đang dở, hai
  worker không dùng chung. Giao diện đã viết sẵn cho bản Redis.
- **Chưa có thước đo chất lượng câu chữ** — chỉ đo được "có đúng mã bệnh không".

Việc tiếp theo và cách làm: [docs/CHATBOT-NEXT.md](docs/CHATBOT-NEXT.md).
