# Thuê máy GPU: máy nào, thuê thế nào, và những cách nó hỏng

Đọc file này trước khi thuê máy. Ngày 18/09/2026 mất **năm lần thuê** mới có một
máy chạy được, và bốn lần thất bại vì bốn nguyên nhân khác nhau. Toàn bộ nằm dưới
đây để không ai phải phát hiện lại.

Có hai loại máy, đừng lẫn: **máy train** (chạy YOLO, dùng một lần rồi huỷ) và
**máy serve** (chạy cả dịch vụ để test và demo). Yêu cầu của chúng khác nhau.

---

## Khi máy đã chốt bị người khác thuê

`machine_id 27076` là **một máy vật lý của một người cho thuê**, không phải một
loại máy. Ai thuê trước thì nó biến mất khỏi danh sách cho tới khi trả, và điều
đó sẽ xảy ra.

Trước khi kết luận là mất máy, chạy `status` — máy do **chính mình** đang thuê
cũng không còn xuất hiện trong danh sách cho thuê, và đó là nhầm lẫn hay gặp
nhất.

Nếu máy bận thật, tìm theo tiêu chuẩn thay vì theo tên card:

```
python tools/rent_gpu.py offers --gpu "" --min-vram 12 --min-cuda 13.0 --min-download 3000
```

`--gpu ""` là tìm **mọi loại card**. Không có nó thì lệnh ngầm lọc đúng RTX 3060
theo mặc định và báo không có máy nào, trong khi A4000 vẫn đang rảnh — đã dính
một lần.

Đo ngày 18/09: câu lệnh trên trả về **11 máy đạt chuẩn**, từ A4000 $0,092 tới
RTX 3090 $0,402, gồm cả 4070 Ti, 5060 Ti, V100, 4090. Nói cách khác nguồn cung
rộng; thứ hiếm không phải GPU mà là **CUDA ≥ 13.0 cộng đường truyền ≥ 3 Gb/s**.

Chọn máy thì **ưu tiên reliability rồi mới tới giá**. Chênh lệch giá cả ngày
chưa tới một đô; một lần thuê hỏng mất 15–30 phút.

---

## Máy serve: chốt con A4000 này

    machine_id 27076    host_id 150602
    RTX A4000, 16 GB, CUDA 13.0, 6.8 Gb/s xuống, tin cậy 0.9986
    khoảng $0.12/giờ, Delaware US
    Xeon E5-2699 v4, 8 core, 47 GB RAM

Đây là máy **đã chạy thông từ đầu đến cuối**: pull image 8,74 GB trong ~3 phút,
nạp Qwen, và **cổng công khai vào được từ ngoài**. Dùng lại nó.

    python tools/rent_gpu.py offers --machine 27076
    python tools/rent_gpu.py serve --offer <id vừa liệt kê>

Nếu nó không rentable thì **thường là do chính mình đang thuê** — chạy
`status` trước khi kết luận nó mất. Một host bị thuê hết trả về **không có offer
nào** chứ không trả về offer đã hết chỗ.

Máy dự phòng khi 27076 không có: lọc theo **độ tin cậy trước, giá sau**. Máy
serve tốn vài xu một giờ, một lần thuê thất bại tốn mười lăm phút.

    python tools/rent_gpu.py offers --min-cuda 13.0 --min-download 3000

---

## Ba điều kiện, hai cái máy tự kiểm được

**CUDA ≥ 13.0.** Image serve dựng trên `vllm/vllm-openai:v0.29.0`, cần driver
mới. Máy CUDA 12.2 hay 12.6 **nhận thuê, pull xong 9 GB, rồi mới chết** với
`Error 803: unsupported display driver / cuda driver combination`. Hiện
`rent_gpu.py serve` đã tự chặn (`SERVE_MIN_CUDA`).

**Băng thông ≥ 3 Gb/s.** Image có **một tầng 5,12 GB** thừa hưởng từ vLLM. Tầng
cỡ đó **không resume được**: đứt là tải lại từ đầu. Nên link chậm không phải tải
lâu, mà là **không bao giờ xong**. Đo thật:

| băng thông | kết quả |
|---|---|
| 545 Mbps | retry 33 phút, không xong |
| 1,4 Gb/s | đứng 19 phút, không xong |
| 4,8 Gb/s | pull xong nhanh |
| 6,8 Gb/s | pull xong ~3 phút |

Đã chặn trong `SERVE_MIN_DOWNLOAD_MBPS`.

**Cổng phải vào được từ ngoài — cái này máy không kiểm được.** Có một máy đạt cả
hai điều kiện trên, container khoẻ, Uvicorn chạy, ánh xạ cổng đúng
(`8000/tcp → 40818` trên `0.0.0.0`), mà `curl` từ ngoài **timeout**. Host chặn
inbound. Máy đó reliability 0.981 và `verified: None`. Không có cách nào biết
trước ngoài việc **ưu tiên host đã từng làm được việc** — nên mới chốt 27076.

---

## Năm lần thuê ngày 18/09, mỗi lần một kiểu hỏng

1. **545 Mbps, CUDA 12.2** — pull retry 33 phút. Hỏng vì băng thông.
2. **6,6 Gb/s, CUDA 12.6** — pull xong dưới 1 phút, rồi `Error 803`. Hỏng vì driver.
3. **1,4 Gb/s, CUDA 13.0** — pull đứng 19 phút. Hỏng vì băng thông.
4. **4,8 Gb/s, CUDA 13.2** — container khoẻ, cổng không vào được. Hỏng vì host.
5. **6,8 Gb/s, CUDA 13.0, A4000** — chạy. Đây là 27076.

Tổng tiền cho bốn lần thất bại: khoảng **$0.09**. Tổng thời gian mất: hơn một
giờ. Tiền không đáng kể, thời gian mới đáng.

### Lần thứ sáu, 18/09 chiều: thử RTX 3060 12GB

PO hỏi có thuê 3060 12GB rẻ hơn được không, miễn hiệu năng không giảm. Câu trả
lời **chưa biết**, vì máy 3060 duy nhất đạt chuẩn lại hỏng theo kiểu số 4:
container chạy hoàn chỉnh — log có `Qwen is answering` và `Uvicorn running on
0.0.0.0:8000` — nhưng cổng bên ngoài không route, `curl` treo 12 giây rồi timeout.
Huỷ, quay lại A4000.

Vì vậy **3060 chưa bị loại, chỉ là chưa đo được**. Nếu lần sau muốn thử lại, đây
là những gì cần biết trước:

- Trên giấy 3060 có băng thông bộ nhớ 360 GB/s so với 448 GB/s của A4000, tức
  **thấp hơn khoảng 20%**. Sinh chữ là tác vụ nghẽn băng thông, nên nhiều khả
  năng độ trễ tăng cỡ đó. Phải đo mới biết, đừng suy từ con số này.
- VRAM 12GB so với 16GB. Với `GPU_FRACTION=0.70` thì Qwen được 8,4GB thay vì
  11,2GB; model chiếm 3,32GB nên vẫn vừa, nhưng KV cache hẹp hơn hẳn.
- Giá $0,081/giờ so với $0,108–0,123. Tiết kiệm khoảng **$0,03/giờ**, tức là
  chưa tới một đô cho cả một ngày làm việc. Không đáng đánh đổi lấy rủi ro.

Kết luận thực dụng: **cứ dùng A4000 27076**, trừ khi có ai đó cần chạy rất nhiều
giờ liên tục thì mới bõ công đo 3060.

---

## Cách nhận ra đang hỏng, đừng chờ mù

Đừng ngồi đợi `/health`. Đọc thẳng thông báo của vast.ai và log container:

    python tools/rent_gpu.py logs --instance <id> --tail 80

Dấu hiệu và nghĩa:

- `Retrying in 2 seconds` hoặc thông báo **không nhúc nhích quá 5 phút** → pull
  đang thất bại, không phải đang chậm. **Huỷ, đổi máy.**
- `Error 803` / `unsupported display driver` → driver cũ. **Huỷ, đổi máy.**
- `Pull complete` / `Verifying Checksum` **đang nhảy** → bình thường, chờ.
- `== Waiting for the model to load` → đang nạp Qwen, mất 3–8 phút, bình thường.
- `Uvicorn running` mà `curl` vẫn timeout → **host chặn cổng. Huỷ, đổi máy.**

Watcher nên **tự dừng khi thấy dấu hiệu chí tử** thay vì đếm đến hết giờ. Ba lần
đầu ngày 18/09 mất tổng cộng hơn một giờ vì watcher chỉ biết đợi.

---

## Máy train

Khác máy serve ở chỗ image trainer nhỏ hơn và không cần cổng vào từ ngoài, nên
băng thông ít quan trọng hơn — nhưng nó phải tải **bộ dữ liệu 2,4 GB** từ
Hugging Face nên vẫn đừng lấy máy quá chậm.

Đã dùng thành công: **RTX 3090**, 70 epoch yolo11s, 3 giờ 20 phút, **$0.72**.
RTX 3060 cũng chạy được, chậm hơn khoảng gấp đôi.

**Đừng lấy card Blackwell (5090)**: image train là CUDA 12.1, cần 12.8.
`rent_gpu.py train` đã chặn sẵn.

    python tools/rent_gpu.py offers --gpu RTX_3090 --min-vram 24
    python tools/rent_gpu.py train --offer <id> --epochs 70 --batch 48 \
        --model yolo11s.pt --run-name detector-v3

Train thêm vòng từ weights đã publish, không train lại từ đầu:

    python tools/rent_gpu.py train --offer <id> --epochs 30 \
        --resume-from detector-v2-yolo11s/weights/best.pt --run-name detector-v2-more

---

## Luật về tiền, tuyệt đối không phá

**Máy train tự huỷ khi xong.** Entrypoint đẩy weights lên Hugging Face **trước
khi** in `Done. Results in`, nên huỷ sau mốc đó là an toàn, không mất gì.

**Máy serve KHÔNG tự huỷ.** Nó phải sống để test và demo. Vì vậy:

- Luôn `status` ở đầu và cuối mỗi phiên làm việc.
- Huỷ khi không còn dùng: `python tools/rent_gpu.py destroy --instance <id>`
- `destroy` **kiểm chứng lại bằng cách hỏi lại danh sách đang thuê**, không tin
  câu trả lời của API. Nếu nó báo vẫn còn thì vào
  https://cloud.vast.ai/instances/ xoá tay ngay.
- Cuối phiên, `status` phải in `Nothing rented. No charges accruing.`

Giá tham chiếu: serve $0.08–0.13/giờ, train 3090 khoảng $0.22/giờ. Một ngày làm
việc bình thường tốn dưới **một đô**.

---

## Sau khi máy lên

    python tools/rent_gpu.py address --instance <id>

In ra `AI_SERVICE_URL`, link `/health`, và endpoint chẩn đoán. Giao diện chat ở
**`<địa chỉ>/chat`**.

`/health` phải trả về `"attached": true` cho **cả** `vlm` và `detector`, và
`chunks` phải là **3319** (hoặc lớn hơn nếu kho tri thức đã thêm). Nếu `chunks`
nhỏ hơn con số đang dùng thì đang chạy **image cũ** — bài test sẽ đo sai code.

Chạy bộ 564 ca với mô hình thật:

    AI_SERVICE_URL=<địa chỉ> python tools/eval_chat_suite.py --out docs/chat-suite-results.json

**Nhớ: image serve chỉ build khi merge vào `main`** (workflow `Serving image`,
theo đường dẫn `app/**`, `docker/serve/**`, `requirements.txt`). Sửa code mà chưa
merge thì máy thuê **không có bản sửa đó**. Chờ build xong (khoảng 13 phút) rồi
mới dựng lại máy, nếu không sẽ test đúng con code cũ và tưởng bản sửa không ăn.
