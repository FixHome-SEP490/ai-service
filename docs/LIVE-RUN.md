# Chạy thật trên GPU thuê

Chờ PO cho phép mới thuê. File này để khi được phép thì chạy một mạch, không phải nhớ lại.

## Máy

RTX 3060 **12GB**, đúng như đã thống nhất từ đầu, và entrypoint viết theo card 12GB.

```
python tools/rent_gpu.py status                      # phải báo không có máy nào
python tools/rent_gpu.py offers --min-cuda 13.0      # mặc định đã là RTX_3060 12GB
python tools/rent_gpu.py serve --offer <id>
python tools/rent_gpu.py address --instance <id>
python tools/rent_gpu.py destroy --instance <id>     # làm ngay khi đo xong
```

Giá tham khảo lần gần nhất: $0.053/giờ. Chọn máy có `down` cao, vì ảnh khoảng 7GB và tiền thuê chạy trong lúc kéo ảnh.

`GPU_FRACTION` giữ mặc định 0.70. Trên card 12GB thì Qwen lấy 8.4GB và YOLO còn 3.6GB. Entrypoint đã ghi rõ 0.85 chỉ chừa 1.6GB, và đó là mức hết VRAM giữa chừng một request có ảnh chứ không phải lúc khởi động.

Ba thứ phải kiểm trước khi thuê, vì mỗi cái đều tốn trọn một lần thuê để phát hiện: không có máy nào đang chạy, ảnh serve đã build lại sau commit mới nhất trên `main`, và trọng số `detector-v1` còn trên Hugging Face.

## Chạy

API chỉ mở sau khi Qwen trả lời được, nên lúc đầu `/health` không phản hồi nghĩa là đang nạp model chứ không phải hỏng.

```
export AI_SERVICE_URL=http://<host>:<port>
python tools/eval_chat_suite.py
python tools/eval_chat_suite.py --only answer --show-replies
```

## Phải nhìn vào cái gì

Dòng **tri thức nghề** trong báo cáo. Nó đếm bao nhiêu câu trả lời thật sự trích tài liệu nghề chứ không chỉ trích bảng chính sách. Dòng này được thêm vào sau lần chạy đầu tiên, vì nếu không có nó thì mọi con số khác đều đẹp trong khi corpus không tới được câu trả lời.

Các nhánh an toàn, hỏi trực tiếp và đọc câu trả lời chứ đừng tin điểm số: mùi gas phải mở đầu bằng khoá van bình gas, vỡ ống nước phải mở đầu bằng khoá van tổng, mùi khét ở thiết bị đấu cứng phải nói ngắt aptomat chứ không phải tắt công tắc tường.

Một câu hỏi lạc đề phải trả về rỗng, không trích dẫn gì.

Thời gian trả lời mỗi câu, để biết card 12GB có đủ cho luồng thật hay không.

## Lần chạy ngày 17/09/2026 — chạy dở, và nó đáng tiền

Thuê RTX 3060 12GB, API lên được, Qwen trả lời được. Hỏi "vì sao dàn lạnh bám tuyết" thì service giải thích bao lâu nên vệ sinh tủ lạnh một lần.

Nguyên nhân: `answer()` — đường hỏi-đáp, tức bề mặt khung chat gọi — chỉ lấy văn bản từ bảng chính sách và bảng giá, không gọi `corpus_passages` cũng không gọi `safety_passages` lần nào. Corpus tới được đường chẩn đoán từ ảnh rồi dừng ở đó.

Bộ đánh giá ngoại tuyến không thấy vì nó dựng `DiagnosisContext`, tức đo đúng nửa đang chạy tốt. Đây là lý do một con số 100% ngoại tuyến không thay thế được một lần chạy thật.

Nửa nguy hiểm hơn là an toàn: người gõ "bếp nhà em có mùi gas" vào ô câu hỏi ở cùng căn phòng với người chụp ảnh cái bếp đó, nhưng chỉ người chụp ảnh mới được nhắc khoá van. Đã sửa, cảnh báo giờ ghim đầu ở cả hai bề mặt.

Sửa thêm một chỗ nữa tìm ra khi đọc bộ đánh giá: nó gửi câu hỏi không kèm `deviceType`, mà khung chat thật cũng vậy ở tin nhắn đầu. Giờ thiết bị được suy ra từ chính câu hỏi khi không ai truyền vào.

Tổng tiền hai lần thuê hôm đó: khoảng $0.05. Huỷ máy xong, không còn gì tính tiền.

Lần chạy tới bắt đầu lại từ đầu với ảnh đã có các sửa này.
