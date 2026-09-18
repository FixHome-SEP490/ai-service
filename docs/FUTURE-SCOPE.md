# Những thứ làm sau

Ghi lại để khỏi quên và để người sau khỏi thử lại những thứ đã thử rồi.

## Đọc thông số trên nhãn thiết bị

Khách chụp cái tem năng lượng hay tem model dán sau lưng máy, AI đọc ra công
suất, mã máy, năm sản xuất. Biết được thì gợi ý linh kiện sát hơn nhiều — bảng
791 linh kiện chia theo công suất, mà hiện mình đang đoán.

**YOLO không làm được việc này.** Nó cho ra khung và tên lớp, không đọc chữ. Đó
là bài toán khác hẳn.

**Qwen đọc được, nhưng chưa đủ tin.** Đã đo trên ảnh thật: ấm đun Zebra nó đọc
đúng "Zebra" dù chữ rất nhỏ ở đáy ấm. Ổ cắm VANLOCK nó đọc thành **"Vanook"** —
gần đúng mà sai, và một mã máy sai một ký tự thì tra ra linh kiện khác.

Và cách hỏi quyết định gần hết kết quả. Hỏi "thương hiệu của sản phẩm này là
gì?" thì nó trả lời đúng. Hỏi "trong ảnh có những chữ gì?" thì nó chỉ bắt được
watermark và bỏ sót luôn tên hãng.

Hướng nếu làm: đừng để Qwen đọc tự do. Cho nó một danh sách đóng các hãng phổ
biến ở Việt Nam và bắt chọn, giống cách đang làm với mã bệnh. Hãng thì hữu hạn,
mã máy thì không — mã máy nên dùng OCR chuyên dụng chứ không dùng VLM.

## Hướng dẫn thao tác qua ảnh chụp màn hình

Người muốn đăng ký làm thợ chụp màn hình app, AI nhìn và chỉ bấm vào đâu tiếp.

Đây là bài toán khác hẳn phần đang làm: không phải nhận thiết bị gia dụng mà là
đọc giao diện, và không phải tra bảng bệnh mà là bám theo một quy trình có thứ tự.

Điểm đáng lưu ý: nó **không cần model mới**. Giao diện app là thứ mình tự làm ra,
nên mỗi màn hình có thể được nhận bằng chính những chữ có trên đó. Phần khó không
nằm ở AI mà nằm ở việc viết ra quy trình từng bước cho đủ.

Cảnh báo: Qwen2.5-VL-3B đọc chữ tiếng Việt trên ảnh còn sai, như vụ Vanook ở
trên. Với ảnh chụp màn hình thì chữ sắc nét hơn ảnh chụp thiết bị nhiều nên có
thể khá hơn, nhưng phải đo trước khi hứa.

## Nhận ảnh HEIC

iPhone mặc định chụp HEIC. Service hiện chỉ nhận JPEG, PNG, WebP, nên app phải
tự chuyển trước khi gửi.

Phần lớn thư viện chọn ảnh của React Native tự chuyển sang JPEG, nhưng không
phải lúc nào cũng vậy, và khi không chuyển thì khách nhận lỗi mà không hiểu vì
sao. Công cụ dựng dataset đã xử lý HEIC bằng `pillow_heif`, chép sang service là
xong.

Đáng làm sớm hơn hai phần trên vì nó rẻ và vì nó là lỗi khách gặp thật.

## Đừng thử lại: cho Qwen soi lại crop của YOLO

Ý tưởng nghe hợp lý — YOLO cắt vùng thiết bị rồi để Qwen xác nhận lại đúng loại,
nhất là với các cặp dễ lẫn.

**Đã đo và nó không chạy.** 12 ảnh lò nướng và lò vi sóng, hỏi Qwen chọn một
trong hai, kèm gợi ý dấu hiệu phân biệt. Nó trả lời **giống hệt nhau cả 12 lần**.
Đảo thứ tự hai lựa chọn trong câu hỏi cũng không đổi, nên không phải thiên vị vị
trí — nó đơn giản là không phân biệt được.

Hỏi thẳng "bên trong có đĩa thuỷ tinh xoay không?" thì nó trả lời **KHÔNG cho cả
lò vi sóng thật**.

YOLO gọi đúng 3 trên 6 ảnh lò nướng. Thêm Qwen vào sẽ lật cả 3 cái đúng thành
sai. Cách đang dùng — hỏi khách một câu — vẫn là cách tốt nhất.

Nếu sau này đổi sang model VLM lớn hơn thì đo lại, đừng tin kết luận này mãi.

## Đổi sang model lớn hơn — ĐÃ LÀM, nhưng sang yolo11s chứ không phải YOLOv8s

Đòn mạnh nhất còn lại để tăng độ chính xác. Cùng dữ liệu, thường được thêm 3–5
điểm mAP. Tốn khoảng 7 tiếng và 1,5 đô trên máy thuê.

Train thêm epoch thì không đáng: đường cong đã phẳng, từ epoch 80 tới 100 chỉ
thêm 0,005 mAP.

Thêm ảnh cho lớp yếu thì có ích nhưng có giới hạn — ổ cắm đã có 2.423 ảnh train,
nhiều thứ nhì, mà vẫn chỉ đạt 76,6%. Số lượng không cứu được lớp mà giới hạn nằm
ở chính tấm ảnh.
