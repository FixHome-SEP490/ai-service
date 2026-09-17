# Những chỗ kho tri thức cần thợ xác nhận

821 mục, trải trên 158 tài liệu. Danh sách này được sinh ra từ chính kho tri thức bằng `python tools/review_backlog.py`, nên nó không bao giờ lệch với file gốc.

Xếp theo thiết bị, thiết bị nhiều mã bệnh lên trước, vì đó cũng là thiết bị khách hỏi nhiều nhất. Trong mỗi thiết bị, mã bệnh nguy hiểm lên trước: trả lời sai ở đó tốn hơn trả lời sai một cái giá.

Cách dùng: mỗi lần ngồi xuống xử lý trọn một thiết bị. Trả lời xong thì sửa thẳng vào tài liệu tương ứng và xoá dòng đó khỏi `needs_technician_review` ở đầu file.

## Máy lạnh — 69 mục

**Hỏng máy nén** (KHẨN) — `faults/AC_COMPRESSOR_FAULT.md`

- Ngưỡng điện trở cách điện giữa cuộn dây và vỏ coi là đạt, vì nó phụ thuộc tiêu chuẩn áp dụng và tình trạng máy.
- Dòng khởi động và dòng làm việc định mức theo từng model, đọc trên tem máy.
- Điện trở các cuộn dây coi là bình thường theo từng loại máy nén.
- Máy là loại inverter hay không, vì với máy inverter thì bo công suất phải được loại trừ trước khi kết luận máy nén.
- Chi phí thay máy nén so với giá một máy mới cùng công suất tại thời điểm tư vấn, vì đây là con số quyết định cuộc nói chuyện sửa hay thay và nó thay đổi theo thị trường.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Mùi khét, nghi chập điện** (KHẨN) — `faults/AC_SMELL_BURNT.md`

- Phạm vi hư hỏng sau một sự cố chập điện, vì nó phụ thuộc chỗ chập nằm ở đâu và đã lan tới đâu, chỉ đánh giá được sau khi mở ra.
- Khi nào phải thay cả cụm dây và bo thay vì sửa từng linh kiện.
- Tiết diện dây và dòng aptomat phù hợp cho từng công suất máy, vì đây là phần hệ thống điện của nhà và cần thợ điện đánh giá theo quy chuẩn.
- Máy còn dùng được sau sự cố hay không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng tụ điện** — `faults/AC_CAPACITOR.md`

- Trị số điện dung và điện áp của tụ cho từng model máy. Phải đọc trên thân tụ cũ hoặc tra theo model, không suy đoán theo công suất.
- Ngưỡng suy giảm điện dung coi là phải thay.
- Tuổi thọ tụ tính bằng năm, vì chênh lệch theo nhiệt độ nơi lắp và chất lượng tụ là rất lớn.
- Máy là loại inverter hay không, khi khách không xác định được qua tem và qua biểu hiện.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nghẹt đường thoát nước ngưng** — `faults/AC_DRAIN_BLOCKED.md`

- Độ dốc tối thiểu của ống thoát nước ngưng, vì khuyến cáo khác nhau giữa các hãng và giữa các tài liệu thi công.
- Chiều dài ống thoát tối đa còn chảy được bằng trọng lực, ngưỡng vượt qua thì cần bơm nước ngưng.
- Máng có thể rửa tại chỗ hay phải tháo dàn ra, chỉ quyết được sau khi mở nắp nhìn.
- Chỗ nghẽn có nằm trong đoạn đi âm tường không, và chi phí xử lý đoạn âm.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đóng tuyết dàn lạnh** — `faults/AC_ICING.md`

- Nhiệt độ bề mặt dàn lạnh coi là bình thường khi máy chạy, vì nó phụ thuộc loại môi chất, model và điều kiện phòng.
- Ngưỡng lưu lượng gió tối thiểu theo từng model, dưới ngưỡng đó thì bắt đầu có rủi ro đóng băng.
- Áp suất phía thấp coi là bình thường, nằm ở tài liệu của bệnh thiếu gas và cũng để thợ chốt tại chỗ.
- Máy có thừa công suất so với phòng hay không, chỉ đánh giá được khi khảo sát.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng mô tơ quạt dàn lạnh** — `faults/AC_INDOOR_FAN_MOTOR.md`

- Thông số mô tơ quạt dàn lạnh theo từng model, gồm công suất, tốc độ, và kiểu tín hiệu điều khiển.
- Trị số tụ mô tơ trên máy dùng loại có tụ.
- Ngưỡng lưu lượng gió coi là đạt sau khi sửa, vì không có mốc chung và thợ đánh giá bằng phép đo tại chỗ.
- Lỗi nằm ở mô tơ hay ở mạch điều khiển trên bo, với máy đời mới có tín hiệu phản hồi. Chỉ tách được bằng phép đo.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Thiếu gas, xì gas** — `faults/AC_LOW_REFRIGERANT.md`

- Những mục sau cố ý không ghi số cụ thể trong tài liệu này, vì số đúng phụ thuộc loại môi chất, model máy và điều kiện lúc đo. Khi trả lời khách, hệ thống nói theo hướng dẫn chung và để thợ chốt số tại chỗ.
- Áp suất phía thấp và phía cao coi là bình thường ở từng loại môi chất, ứng với nhiệt độ ngoài trời tại Việt Nam.
- Áp suất nitơ dùng để thử kín và thời gian giữ áp, vì mỗi hãng có khuyến cáo riêng và vượt mức khuyến cáo có thể làm hỏng dàn.
- Mức chân không cần đạt và thời gian giữ trước khi nạp.
- Lượng môi chất nạp bù cho mỗi mét ống vượt chiều dài tiêu chuẩn, vì khác nhau theo hãng và theo loại môi chất. Tra tem máy.
- Chênh lệch nhiệt độ gió vào gió ra coi là đạt, vì con số này thay đổi theo độ ẩm trong phòng.
- Mã lỗi của các hãng ngoài ba hãng đã xác nhận ở trên. Không được đoán.
**Hỏng quạt cục nóng** — `faults/AC_OUTDOOR_FAN_MOTOR.md`

- Thông số mô tơ quạt theo từng model: công suất, tốc độ, chiều quay, kiểu đấu.
- Trị số tụ quạt theo từng model.
- Thời gian máy tự ngắt vì quá nhiệt rồi chạy lại coi là bình thường, vì nó khác nhau theo máy và theo nhiệt độ ngoài trời.
- Máy nén có bị ảnh hưởng hay không sau thời gian chạy với quạt không quay, chỉ đánh giá được bằng phép đo tại chỗ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Lỗi bo mạch điều khiển** — `faults/AC_PCB_FAULT.md`

- Mã lỗi của các hãng ngoài ba hãng đã đối chiếu. Đây là mục quan trọng nhất trong danh sách này. Tra theo tài liệu của đúng model, không đoán, không suy từ hãng khác.
- Khi nào sửa bo còn hợp lý so với thay bo, và bảo hành của phương án sửa.
- Bo thay thế đa năng có phù hợp với model cụ thể không và mất tính năng gì.
- Giá trị đọc của cảm biến coi là bình thường ở từng nhiệt độ.
- Điện áp tại chỗ có nằm trong dải chấp nhận được không, và có cần ổn áp không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Bẩn lưới lọc và dàn lạnh** — `faults/AC_DIRTY_FILTER.md`

- Chu kỳ vệ sinh khuyến cáo chính xác cho từng model, vì các hãng ghi khác nhau.
- Mức giảm lưu lượng gió coi là bất thường, vì không có mốc chung và thợ đánh giá bằng kinh nghiệm cộng phép đo tại chỗ.
- Máy có cần tháo dàn ra vệ sinh hay chỉ xịt tại chỗ là đủ, chỉ quyết được sau khi mở nắp nhìn.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Máy chạy ồn, rung lắc** — `faults/AC_NOISY_INDOOR.md`

- Mức ồn coi là bình thường theo từng model, vì các hãng công bố khác nhau và cảm nhận của khách cũng khác nhau.
- Khe hở tiêu chuẩn giữa quạt lồng sóc với vỏ và với máng nước.
- Kiểu đệm giảm chấn và cách bắt chân máy nén theo từng model.
- Tiếng máy nén nghe được coi là bất thường hay không, vì việc này cần tai nghề và cần nghe trực tiếp.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng điều khiển từ xa** — `faults/AC_REMOTE_FAULT.md`

- Mã remote thay thế tương thích theo từng model máy, và với remote đa năng thì mã hãng cần cài.
- Máy có nút nguồn cơ trên thân hay không, và nút đó nằm ở đâu, vì khác nhau theo model và nhiều máy giấu nút dưới nắp.
- Cách mở khóa trẻ em trên từng loại remote, vì tổ hợp nút khác nhau theo hãng.
- Cách đổi mã lệnh khi hai máy cùng hãng bị điều khiển chung một remote.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Máy lạnh** — `devices/air_conditioner.md`

- Bảng quy đổi công suất theo diện tích và thể tích phòng, vì con số phụ thuộc quá nhiều vào hướng nắng, mái, cửa kính và số người.
- Tuổi thọ tính bằng năm của từng bộ phận cụ thể.
- Mã lỗi của các hãng ngoài ba hãng đã đối chiếu ở trên. Không được đoán.
- Mức tiêu thụ điện chính xác của từng model, vì con số trong tài liệu này là khoảng ước lượng theo công suất chứ không phải thông số đo.
- Các mốc áp suất và thông số đo đạc, nằm ở tài liệu của từng bệnh và để thợ chốt tại chỗ.
- Chi phí. Mọi con số tiền gửi cho khách lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Máy giặt — 70 mục

**Cấp nước không ngắt, tràn nước** (KHẨN) — `faults/WM_OVERFLOW.md`

- Thông số van cấp và cảm biến mực nước theo từng model.
- Mức nước định mức theo từng chế độ giặt, để biết mức nào là cao bất thường.
- Độ cao đầu ống xả cho phép theo khuyến cáo của hãng.
- Cách kiểm tra cảm biến mực nước trên từng model.
- Mã lỗi liên quan tới cấp nước của từng hãng. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Mòn bạc đạn lồng giặt** — `faults/WM_BEARING_NOISE.md`

- Chi phí thay bạc đạn so với giá một máy mới cùng khối lượng tại thời điểm tư vấn. Đây là con số quyết định cuộc nói chuyện sửa hay thay và nó thay đổi theo thị trường và theo model.
- Model nào cho thay riêng bạc đạn, và model nào phải thay cả cụm thùng hoặc cụm lồng vì thùng liền khối không tách được.
- Tình trạng trục lồng, chỉ đánh giá được sau khi mở máy.
- Thông số bạc đạn và phớt theo từng model.
- Tốc độ vắt định mức, để biết tải lên bạc.
- Tuổi thọ bạc đạn tính bằng năm hoặc bằng số mẻ giặt.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng khoá cửa** — `faults/WM_DOOR_LOCK.md`

- Vị trí cần mở khoá khẩn cấp theo từng model, và model nào không có.
- Thời gian chờ nhả khoá sau khi kết thúc chu trình, theo từng model.
- Ngưỡng nhiệt độ nước dưới đó máy mới nhả khoá, trên model có giặt nước nóng.
- Thông số cụm khoá cửa theo từng model, và model nào phần móc liền với cánh cửa.
- Mã lỗi liên quan tới cửa của từng hãng. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rách gioăng cửa, rò nước** — `faults/WM_DOOR_SEAL_LEAK.md`

- Mã gioăng thay thế theo từng model, và gioăng tương thích nào dùng được.
- Model nào thay gioăng được từ phía trước, và model nào phải tháo mặt trước máy.
- Cách lắp vòng kẹp và lực căng đúng theo từng model.
- Gioăng còn chỉnh lại được hay phải thay, chỉ đánh giá được khi nhìn tại chỗ.
- Tuổi thọ gioăng tính bằng năm hoặc bằng số mẻ giặt.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng bơm xả, nghẹt đường xả** — `faults/WM_DRAIN_PUMP.md`

- Vị trí nắp lưới lọc và ống xả khẩn cấp theo từng model, và model nào không có.
- Độ cao ống xả cho phép theo khuyến cáo của hãng.
- Thông số bơm xả theo từng model.
- Cách kiểm tra cảm biến mực nước trên từng model.
- Mã lỗi liên quan tới xả nước của từng hãng. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng mô tơ giặt** — `faults/WM_MOTOR_FAULT.md`

- Máy thuộc kiểu truyền động nào, vì nó quyết định cả chẩn đoán lẫn chi phí. Không đoán từ hãng hay từ năm sản xuất.
- Thông số mô tơ và chổi than theo từng model, và chiều dài chổi tối thiểu còn dùng được.
- Cách kiểm tra cảm biến tốc độ trên từng model.
- Ngưỡng điện trở cuộn dây và cách điện coi là đạt.
- Chi phí thay mô tơ so với giá một máy mới cùng khối lượng tại thời điểm tư vấn.
- Mã lỗi liên quan tới mô tơ của từng hãng. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Không vắt, hỏng dây curoa hoặc lệch tải** — `faults/WM_NO_SPIN.md`

- Ngưỡng mất cân bằng cho phép theo từng model, và số lần máy thử cân lại trước khi bỏ cuộc.
- Thông số và độ căng dây curoa theo từng model, và model nào dùng truyền động trực tiếp.
- Tốc độ vắt định mức theo từng model.
- Khối lượng giặt tối thiểu và tối đa khuyến cáo.
- Mã lỗi liên quan tới vắt của từng hãng. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Không cấp nước, nghẹt van cấp** — `faults/WM_NO_WATER_INLET.md`

- Áp lực nước tối thiểu và tối đa để van cấp làm việc đúng, theo từng model.
- Thông số van cấp theo từng model, và model nào có hai van.
- Vị trí và cách tháo lưới lọc đầu van trên từng model.
- Thời gian chờ cấp nước trước khi máy báo lỗi, theo từng model.
- Mã lỗi liên quan tới cấp nước của từng hãng. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Lỗi bo mạch điều khiển** — `faults/WM_PCB_FAULT.md`

- Mã lỗi của các hãng. Đây là mục quan trọng nhất trong danh sách này. Tra theo tài liệu của đúng model, không đoán, không suy từ hãng khác.
- Khi nào sửa bo còn hợp lý so với thay bo, và bảo hành của phương án sửa.
- Model nào cần nạp chương trình hoặc cần khớp đời máy khi thay bo.
- Giá trị đọc của từng cảm biến coi là bình thường.
- Điện áp tại chỗ có nằm trong dải chấp nhận được không, và có cần ổn áp không.
- Máy thuộc loại truyền động trực tiếp hay không, vì nó quyết định bo công suất có tách riêng hay không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hôi lồng giặt, đóng cặn** — `faults/WM_SMELL_MOLD.md`

- Chu kỳ vệ sinh lồng khuyến cáo theo từng hãng.
- Model nào tháo lồng ra rửa được, và model nào thùng liền khối rất khó tháo.
- Nhiệt độ nước tối đa máy cho phép khi chạy chu trình vệ sinh.
- Loại hóa chất vệ sinh lồng phù hợp với từng model, vì một số hãng có khuyến cáo riêng.
- Gioăng cửa còn lau được hay mốc đã ăn sâu phải thay, chỉ đánh giá được khi nhìn tại chỗ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Máy giặt** — `devices/washing_machine.md`

- Mã lỗi của các hãng. Tài liệu này chưa có mã máy giặt nào được đối chiếu đủ tin cậy, nên tuyệt đối không đoán. Đây là mục quan trọng nhất trong danh sách này.
- Vị trí lưới lọc bơm và ống xả khẩn cấp theo từng model, vì nó khác nhau và có model không có.
- Vị trí và số lượng bu lông vận chuyển theo từng model.
- Độ cao ống xả cho phép theo khuyến cáo của hãng.
- Áp lực nước tối thiểu để van cấp làm việc đúng.
- Tuổi thọ tính bằng năm của từng bộ phận.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Tủ lạnh — 51 mục

**Hỏng block máy nén** (KHẨN) — `faults/FRIDGE_COMPRESSOR.md`

- Ngưỡng điện trở cách điện giữa cuộn dây và vỏ coi là đạt. Có tài liệu nghề nêu mức tham chiếu, nhưng con số phụ thuộc tiêu chuẩn áp dụng và tình trạng máy, nên thợ đối chiếu theo tài liệu chuẩn chứ không dùng con số nghe được.
- Trị số điện trở các cuộn dây và dòng định mức theo từng model, đọc trên tem.
- Thời gian phải để tủ đứng yên sau khi vận chuyển trước khi cắm điện, vì khuyến cáo khác nhau giữa các hãng.
- Tủ là loại inverter hay không, vì với tủ inverter thì bo công suất phải được loại trừ trước khi kết luận block.
- Chi phí thay block so với giá một tủ mới cùng dung tích tại thời điểm tư vấn, vì đây là con số quyết định cuộc nói chuyện sửa hay thay và nó thay đổi theo thị trường.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng bộ xả đá, đóng tuyết dày** — `faults/FRIDGE_DEFROST_FAULT.md`

- Ngưỡng nhiệt độ tác động của cảm biến xả đá và của cầu chì nhiệt theo từng model. Có tài liệu nêu mức tác động của cầu chì nhiệt quanh bảy mươi độ, nhưng con số khác nhau giữa các hãng và các dòng, nên phải tra theo linh kiện thực tế chứ không áp dụng chung.
- Chu kỳ xả đá theo từng model, vì nó khác nhau và trên tủ đời mới còn thay đổi theo điều kiện.
- Đặc tính đóng mở của cảm biến xả đá theo nhiệt độ, để đo cho đúng.
- Trị số điện trở của thanh xả đá theo từng model.
- Lý do vì sao cầu chì nhiệt đứt, vì cầu chì là bảo vệ và nó đứt vì một nguyên nhân khác.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng quạt gió dàn lạnh** — `faults/FRIDGE_FAN_FAULT.md`

- Thông số quạt gió theo từng model, gồm điện áp, công suất và kiểu điều khiển.
- Điều kiện làm quạt dừng theo thiết kế của từng hãng, vì nhiều tủ tắt quạt khi mở cửa và một số tủ còn tắt quạt trong chu kỳ xả đá. Biết điều này mới đọc đúng được việc quạt không chạy.
- Cách kiểm tra cửa gió ở đường xuống ngăn mát trên từng model.
- Tuổi thọ quạt tính bằng năm.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Thiếu gas, xì gas dàn lạnh** — `faults/FRIDGE_LOW_GAS.md`

- Lượng môi chất nạp theo từng model, đọc trên tem máy. Lượng này rất nhỏ và phải nạp bằng cân, không ước lượng.
- Áp suất tham chiếu theo từng loại môi chất và theo điều kiện đo.
- Áp suất nitơ dùng để thử kín và thời gian giữ áp.
- Mức chân không cần đạt trước khi nạp.
- Chỗ thủng có tiếp cận được không, và có sửa được không, chỉ đánh giá được tại chỗ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hở gioăng cửa** — `faults/FRIDGE_DOOR_GASKET.md`

- Mã gioăng thay thế theo từng model, và gioăng đại trà nào tương thích.
- Mức hao điện do gioăng hở. Có nguồn nêu con số tỉ lệ phần trăm, nhưng nó phụ thuộc độ hở, dung tích tủ, nhiệt độ phòng và cách dùng, nên không dùng con số cụ thể khi trả lời khách.
- Tuổi thọ gioăng tính bằng năm.
- Gioăng còn phục hồi được hay phải thay, chỉ đánh giá được khi nhìn và thử tại chỗ.
- Cách chỉnh bản lề trên từng model.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nghẹt lỗ thoát nước** — `faults/FRIDGE_DRAIN_BLOCKED.md`

- Vị trí lỗ thoát nước theo từng model, vì nó khác nhau và có model giấu lỗ ở chỗ khó thấy.
- Đường kính ống dẫn và dụng cụ thông phù hợp, để không làm thủng ống.
- Chi tiết dẫn hướng ở miệng lỗ thoát có trên model nào và lắp thế nào.
- Cách tháo và vệ sinh khay hứng trên từng model.
- Chu kỳ vệ sinh khay hứng khuyến cáo theo hãng.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng đèn tủ lạnh** — `faults/FRIDGE_LIGHT_FAULT.md`

- Loại đèn theo từng model: bóng rời hay cụm led liền khối, và cách tháo chao đèn.
- Công suất và kiểu đui của bóng thay thế.
- Vị trí công tắc cửa trên từng model và cách kiểm tra nó.
- Trên tủ đời mới, tín hiệu cửa có điều khiển quạt gió hay không, vì điều này khác nhau theo hãng và nó quyết định cách đọc triệu chứng.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Tủ chạy ồn, rung** — `faults/FRIDGE_NOISY.md`

- Mức ồn coi là bình thường theo từng model, vì các hãng công bố khác nhau và cảm nhận của khách cũng khác nhau.
- Cách chỉnh chân tủ và kiểu đệm giảm chấn theo từng model.
- Khoảng cách tối thiểu từ tủ tới tường và tới hai bên theo khuyến cáo của hãng, vì nó khác nhau và nó ảnh hưởng cả tiếng ồn lẫn khả năng thải nhiệt.
- Tiếng máy nén nghe được coi là bất thường hay không, vì việc này cần tai nghề và cần nghe trực tiếp.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Tủ lạnh** — `devices/refrigerator.md`

- Nhiệt độ ngăn mát và ngăn đá coi là đạt theo từng model, và cách đo tại chỗ.
- Tuổi thọ tính bằng năm của từng bộ phận cụ thể.
- Mã lỗi của các hãng. Tài liệu này hiện chưa có mã tủ lạnh nào được đối chiếu đủ tin cậy, nên tuyệt đối không đoán. Đây là mục quan trọng nhất trong danh sách này.
- Thời gian phải để tủ đứng yên sau khi vận chuyển trước khi cắm điện, vì khuyến cáo khác nhau giữa các hãng.
- Loại môi chất và lượng nạp của từng model, đọc trên tem máy.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Quạt điện — 45 mục

**Đứt, hở dây nguồn** (KHẨN) — `faults/FAN_CORD_DAMAGE.md`

- Tiết diện dây đúng cho công suất của quạt khi thay.
- Lõi dây có đứt ngầm ở chỗ nào khác không. Không nhìn thấy được, cần đo.
- Có rò điện ra vỏ không, và nếu có thì rò từ dây hay từ cuộn dây.
- Aptomat chống giật của nhà có làm việc không, nếu đã có hiện tượng tê tay.
- Ổ cắm có bị hỏng theo không, khi phích cắm đã cháy xém.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Cháy cuộn dây mô tơ** (KHẨN) — `faults/FAN_MOTOR_BURNT.md`

- Cuộn dây đã cháy thật hay mùi khét tới từ chỗ khác. Bốn nguồn mùi không tách được qua tin nhắn.
- Mức độ cháy, và cuộn dây còn cứu được không.
- Quấn lại có đáng với model đó không, sau khi biết công quấn và giá quạt tương đương.
- Bạc trục và tụ có phải nguyên nhân gốc không, vì thay mô tơ mà không xử lý gốc thì bệnh quay lại.
- Nhánh điện trong nhà có vấn đề gì không, nếu quạt làm nhảy aptomat.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng tụ khởi động** — `faults/FAN_CAPACITOR.md`

- Trị số tụ đúng cho model quạt đang dùng. Đọc trên thân tụ cũ hoặc tra theo model, không suy đoán.
- Cuộn dây mô tơ còn nguyên không, nếu quạt đã bị ù kéo dài trước khi gọi.
- Bạc trục có còn trơn không, vì tụ mới lắp vào một mô tơ bạc kẹt thì vẫn không chạy được.
- Cách đấu dây tụ vào cuộn đề trên đúng model đó.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng bộ tuốc năng, không đảo gió** — `faults/FAN_OSCILLATION_FAULT.md`

- Bộ tuốc năng có thay rời được cho model đó không, hay phải thay cả cụm.
- Bánh răng mòn tới mức nào, và tra lại mỡ có còn ăn không.
- Tay biên có cong không, vì tay biên cong thì siết ốc cũng không hết lệch.
- Phần đỡ cổ quạt bằng nhựa có nứt không.
- Với quạt có điều khiển từ xa: việc bật đảo đi qua bo mạch hay qua cơ cấu cơ khí.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng công tắc, nút chỉnh tốc độ** — `faults/FAN_SWITCH_FAULT.md`

- Quạt dùng công tắc cơ hay bo mạch điều khiển. Hai loại đi hai hướng khác hẳn.
- Cụm công tắc thay thế có đúng chủng loại cho model đó không, hay phải dùng loại tương đương.
- Tiếp điểm có phát nhiệt tới mức nguy hiểm chưa, khi nhựa quanh phím đã ố.
- Các đầu dây vào công tắc đấu đúng số nào, trước khi tháo.
- Bo mạch có đáng sửa không, với quạt có điều khiển từ xa.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rung lắc, cong cánh, lỏng chân đế** — `faults/FAN_WOBBLE.md`

- Cánh quạt thay thế có đúng cỡ, đúng số cánh và đúng kiểu khớp trục cho model đó không.
- Bạc trục có mòn không, khi rung vẫn còn sau khi đã rửa cánh và siết ốc.
- Trục mô tơ có cong không. Trục cong thì thay cánh mới cũng vẫn rung.
- Bộ treo quạt tường còn chắc không, và tường có còn giữ được vít không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Khô bạc đạn, mòn bạc trục** — `faults/FAN_WORN_BEARING.md`

- Bạc còn dùng được sau khi tra dầu hay đã mòn phải thay. Cần đo khe hở mới chắc.
- Quạt dùng bạc đồng hay vòng bi. Vòng bi không tra dầu kiểu này được.
- Cỡ bạc đúng khi thay.
- Trục có bị mòn hoặc cong không, vì trục mòn thì thay bạc mới cũng không hết khe hở.
- Cuộn dây còn nguyên không, nếu quạt đã bị kẹt và bật thử nhiều lần trước khi gọi.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Quạt điện** — `devices/electric_fan.md`

- Trị số tụ điện đúng cho từng model quạt. Lắp sai trị số thì quạt chạy yếu hoặc nóng, và con số này in trên thân tụ cũ chứ không suy ra được.
- Cuộn dây mô tơ còn nguyên không, khi nghi cháy. Cần đo mới biết.
- Bạc trục còn dùng được sau khi tra dầu hay đã mòn phải thay.
- Dây nguồn đúng tiết diện khi thay.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Máy nước nóng — 49 mục

**Rò điện, nhảy chống giật** (KHẨN) — `faults/WH_ELCB_TRIPS.md`

- Ngưỡng điện trở cách điện giữa thanh đốt và vỏ coi là đạt, và cách đo đúng.
- Điện trở nối đất đạt yêu cầu, và cách làm tiếp địa cho nhà chưa có. Đây là phần của hệ thống điện và cần thợ điện đánh giá theo quy chuẩn, không lấy con số nghe được.
- Tiết diện dây và dòng aptomat phù hợp cho công suất máy.
- Thông số thiết bị chống dòng rò phù hợp.
- Thanh đốt còn dùng được hay phải thay, chỉ quyết được sau khi đo.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Thủng, rò bình chứa** (KHẨN) — `faults/WH_TANK_LEAK.md`

- Bình còn bảo hành ruột bình không, và thời hạn bảo hành riêng của ruột bình theo từng hãng.
- Chu kỳ thay thanh magie theo chất lượng nước của khu vực.
- Nguồn rò chính xác, chỉ xác định được bằng cách lau khô và quan sát tại chỗ.
- Áp lực nước của nhà có vượt ngưỡng thiết kế của bình không, và có cần van giảm áp không.
- Giá treo và tường còn chịu được bình mới không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng rơ le nhiệt** (KHẨN) — `faults/WH_THERMOSTAT.md`

- Nhiệt độ cài an toàn, và mức thấp hơn nên dùng cho nhà có trẻ nhỏ.
- Ngưỡng tác động của rơ le nhiệt và của bộ bảo vệ quá nhiệt theo từng model.
- Cách kiểm tra rơ le trên từng model.
- Van an toàn xả ở áp suất nào, và nhỏ giọt bao nhiêu là bình thường.
- Bộ bảo vệ quá nhiệt có bị can thiệp trong lần sửa trước không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng thanh đốt** — `faults/WH_HEATING_ELEMENT.md`

- Điện trở cuộn dây thanh đốt theo từng công suất, để đo cho đúng.
- Ngưỡng cách điện giữa thanh đốt và vỏ coi là đạt.
- Thời gian đun bình thường theo từng dung tích, để biết bao lâu là bất thường.
- Thanh đốt thay thế đúng công suất và đúng loại theo model.
- Bình có mấy thanh đốt.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Máy nước nóng trực tiếp không nóng** — `faults/WH_INSTANT_NO_HOT.md`

- Áp lực và lưu lượng nước tối thiểu để máy kích, theo từng model.
- Công suất máy và yêu cầu tương ứng về tiết diện dây và dòng aptomat. Đây là phần của hệ thống điện và cần thợ điện đánh giá theo quy chuẩn.
- Mức tăng nhiệt độ máy đạt được ở một lưu lượng nhất định, để biết nước ra bao nhiêu độ là bình thường.
- Vị trí và cách vệ sinh lưới lọc đầu vào trên từng model.
- Máy có bộ bảo vệ quá nhiệt đóng lại bằng tay không và nút ở đâu.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nước yếu, nghẹt đường vào bình** — `faults/WH_LOW_PRESSURE.md`

- Áp lực nước tối thiểu và tối đa cho từng model bình.
- Vị trí lưới lọc và van một chiều theo từng lắp đặt, và khách có tự tháo được không.
- Đường ống nước nóng có đúng kích thước không.
- Nhà có cần bơm tăng áp không, và nếu có thì áp lực cho phép là bao nhiêu.
- Cặn trong bình tới mức nào, chỉ biết được sau khi mở.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đóng cặn canxi trong bình** — `faults/WH_SCALE_BUILDUP.md`

- Chu kỳ vệ sinh bình theo chất lượng nước của khu vực. Đây là con số khác nhau rất nhiều giữa nơi dùng nước máy mềm và nơi dùng nước giếng khoan, nên không đưa một con số chung.
- Chu kỳ thay thanh magie.
- Mức mòn của thanh magie coi là phải thay.
- Thanh đốt còn dùng lại được sau khi làm sạch cặn hay phải thay, chỉ quyết được sau khi đo và nhìn.
- Tình trạng men bên trong bình và bình còn dùng được bao lâu.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Máy nước nóng** — `devices/water_heater.md`

- Tiết diện dây dẫn và dòng aptomat phù hợp cho từng công suất máy. Đây là phần hệ thống điện của nhà và cần thợ điện đánh giá theo quy chuẩn, không lấy con số nghe được.
- Điện trở nối đất đạt yêu cầu, và cách làm tiếp địa cho nhà chưa có.
- Chu kỳ vệ sinh bình, súc cặn và thay thanh magie theo từng hãng và theo chất lượng nước khu vực.
- Áp lực nước tối thiểu để máy trực tiếp kích được, theo từng model.
- Nhiệt độ cài an toàn cho nhà có trẻ nhỏ.
- Mã lỗi của các hãng trên máy đời mới có bảng điện tử. Không đoán.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Bếp gas — 37 mục

**Lửa tự tắt giữa chừng** (KHẨN) — `faults/STOVE_FLAME_OUT.md`

- Bếp có cảm ứng nhiệt hay không. Nhiều bếp cũ không có, và khi đó toàn bộ nhánh chẩn đoán chính không áp dụng.
- Cảm ứng nhiệt còn làm việc không, sau khi đã lau sạch. Cần đo mới biết.
- Van an toàn bên trong bếp có kẹt không. Không phân biệt được bằng quan sát.
- Đầu cảm ứng có đúng vị trí so với ngọn lửa không, nếu nó đã từng bị uốn.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rò rỉ gas** (KHẨN) — `faults/STOVE_GAS_LEAK.md`

- Chu kỳ thay dây dẫn gas và van điều áp theo năm. Các nguồn nêu con số khác nhau và nó còn tuỳ loại dây, nên để đại lý gas hoặc thợ xác nhận.
- Chỗ rò cụ thể. Thử xà phòng cho biết vị trí nhưng không cho biết nguyên nhân gốc.
- Van điều áp có còn đúng áp làm việc không.
- Bình có còn hạn kiểm định không. Đây là việc của đại lý gas.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Van điều áp và bình gas** (KHẨN) — `faults/STOVE_REGULATOR.md`

- Áp làm việc mà bếp của khách cần, và van đang dùng có đúng loại không. Bếp gia dụng và bếp công nghiệp khác nhau.
- Chu kỳ thay van điều áp theo năm. Để đại lý gas hoặc thợ xác nhận.
- Van có còn giữ đúng áp không. Cần đo mới biết, không nhìn được.
- Gioăng miệng bình còn tốt không. Việc của đại lý gas.
- Bình có còn hạn kiểm định không. Cũng là việc của đại lý gas.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Núm vặn kẹt, không tắt được lửa** (KHẨN) — `faults/STOVE_VALVE_STUCK.md`

- Loại mỡ bôi trơn dùng được cho van gas. Phải là loại chuyên dụng chịu nhiệt, không phải mỡ hay dầu thông thường.
- Van côn còn kín không sau khi bôi lại mỡ. Cần thử kín mới biết.
- Trục núm có nứt ngầm không, nếu trước đó đã bị vặn mạnh.
- Van bếp có phải là chỗ rò không, khi khách có mùi gas mà thử trên dây không ra.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Không lên lửa, đánh lửa hỏng** — `faults/STOVE_IGNITER.md`

- Bộ đánh lửa của model khách đang dùng chạy pin hay chạy điện lưới. Khác nhau thì cách kiểm tra khác hẳn.
- Loại và số lượng pin đúng cho model đó.
- Khoảng cách chuẩn từ đầu kim đánh lửa tới mâm chia lửa, nếu nghi kim đã bị uốn.
- Bo mạch đánh lửa còn làm việc không, khi đã loại hết các nhánh rẻ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Họng lửa nghẹt, lửa đỏ lửa yếu** — `faults/STOVE_BURNER_CLOGGED.md`

- Vị trí lá gió và cách chỉnh trên đúng model khách đang dùng. Khác nhau theo hãng và theo đời bếp.
- Đầu phun có đúng cỡ và còn nguyên không. Mòn hoặc lệch thì lửa không bao giờ đúng dù vệ sinh sạch.
- Mâm chia lửa đã biến dạng hay chưa, và có nên thay không.
- Áp làm việc của van điều áp có phù hợp với bếp không, nếu lửa vẫn sai sau khi đã vệ sinh.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Bếp gas** — `devices/gas_stove.md`

- Chu kỳ thay dây dẫn gas và van điều áp. Có nguồn nêu con số theo năm nhưng khác nhau giữa các nguồn và theo loại dây, nên để đại lý gas hoặc thợ xác nhận thay vì đưa một con số chung.
- Áp suất làm việc của van điều áp phù hợp với từng loại bếp, vì bếp dân dụng và bếp công nghiệp khác nhau.
- Loại van điều áp khớp với loại van bình đang dùng.
- Bếp có cảm ứng nhiệt hay không, và nó còn làm việc không.
- Khoảng cách an toàn từ bình gas tới bếp và tới nguồn nhiệt.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Bếp từ — 17 mục

**Nứt vỡ mặt kính bếp từ** (KHẨN) — `faults/HOB_GLASS_CRACKED.md`

- Hãng nào có bán mặt kính rời tại Việt Nam và hãng nào buộc thay cả bếp. Đây là thứ quyết định chi phí nhiều nhất và hiện tài liệu này chưa dám nói chắc.
- Thời gian đặt mặt kính chính hãng, để nói trước cho khách thay vì để khách chờ mà không biết chờ bao lâu.
- Vết nứt ở mép ngoài vùng nấu thì có trường hợp nào thợ xử lý được mà không phải thay cả tấm kính hay không.
**Bếp từ mất nguồn** (KHẨN) — `faults/HOB_NO_POWER.md`

- Dòng định mức aptomat riêng nên dùng cho bếp từ đôi, vì bếp đôi hai vùng nấu cùng chạy hết công suất là mức tải mà nhiều tủ điện nhà cũ không được tính tới.
- Ngưỡng dòng rò của ELCB phù hợp khi bếp lắp âm bàn có mặt kim loại, để không bị nhảy oan mà vẫn bảo vệ được người dùng.
- Bếp từ nhập khẩu chạy điện 200V của Nhật cắm vào lưới 220V thì hỏng nguồn theo kiểu nào, vì loại bếp này khá phổ biến ở Việt Nam qua hàng nội địa.
**Bếp từ báo mã lỗi E** — `faults/HOB_ERROR_CODE.md`

- Bảng mã lỗi của các hãng bán chạy nhất ở Việt Nam. Có bảng đó thì trợ lý trả lời được ngay thay vì phải hỏi hãng rồi chờ thợ.
- Mã nào thợ xử lý tại chỗ được và mã nào phải mang bếp về xưởng, để nói trước cho khách biết mình sẽ mất bếp mấy ngày.
**Quạt tản nhiệt bếp từ kêu hoặc hỏng** — `faults/HOB_FAN_NOISY.md`

- Khoảng hở tối thiểu quanh bếp âm theo hướng dẫn của các hãng bán chạy, để nói được con số khi tư vấn cho khách sắp lắp tủ bếp.
- Quạt tản nhiệt thay rời được trên dòng nào, và dòng nào phải thay cả cụm.
**Bảng cảm ứng bếp từ không ăn** — `faults/HOB_TOUCH_FAULT.md`

- Bo cảm ứng thay rời được trên dòng nào bán ở Việt Nam, và dòng nào phải thay cả cụm cùng mặt kính — chênh lệch chi phí lớn.
- Khoá trẻ em của từng hãng mở bằng thao tác gì. Có bảng đó thì trợ lý hướng dẫn được ngay thay vì phải hỏi hãng rồi chờ.
**Bếp từ không nhận nồi** — `faults/HOB_NO_PAN_DETECT.md`

- Đường kính đáy tối thiểu thực tế của các dòng bếp đang bán, vì con số mười hai phân là mức chung chứ không đúng với mọi hãng.
- Trong số ca gọi báo không nhận nồi, bao nhiêu phần trăm hoá ra là hỏng mâm từ thật. Con số đó quyết định nên hỏi mấy câu trước khi mời đặt thợ.
**Bếp từ** — `devices/induction_hob.md`

- Tỉ lệ thật của bếp nhập khẩu nội địa trong số ca gọi sửa, để biết có nên hỏi về biến áp ngay từ đầu hay không.
- Hãng nào bán mặt kính rời tại Việt Nam, vì đây là câu khách hỏi đầu tiên khi nứt kính và hiện tài liệu chưa trả lời được.
- Mức công suất biến áp tối thiểu nên khuyến nghị cho bếp đôi nội địa Nhật.

## Lò vi sóng — 41 mục

**Phóng tia lửa trong lò** (KHẨN) — `faults/MW_SPARKING.md`

- Vách lò có bị thủng hay chỉ tróc sơn bề mặt. Hai thứ này khác nhau về kết cục và không phân biệt được chắc qua ảnh.
- Khoang lò còn giữ được sóng không, sau khi đã có vết cháy hoặc rỉ.
- Sò cao tần có bị ảnh hưởng chưa, nếu lò đã phóng tia trong thời gian dài.
- Ống dẫn sóng phía sau tấm mica có bị bẩn hoặc cháy không.
- Lò còn đáng sửa không, nếu vách đã hỏng.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng công tắc cửa** — `faults/MW_DOOR_SWITCH.md`

- Cửa còn đóng khít và giữ được sóng không. Không kiểm tra được tại nhà, và không nên tin các mẹo thử bằng điện thoại.
- Công tắc nào trong cụm đang hỏng, và có nên thay cả cụm không.
- Chốt cửa và lỗ chốt còn đúng vị trí không, hay bản lề đã xệ.
- Lưới chắn trên cửa còn nguyên không.
- Nếu cầu chì đã từng đứt: nguyên nhân gốc là gì.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Quạt tản nhiệt ồn, nghẹt** — `faults/MW_FAN_NOISY.md`

- Quạt tản nhiệt còn đủ lưu lượng gió không. Quạt vẫn quay không có nghĩa là vẫn đủ gió.
- Lá tản nhiệt của sò có bị bụi bít không.
- Bạc quạt còn dùng được sau khi tra dầu hay đã mòn phải thay.
- Cảm biến nhiệt bảo vệ có còn làm việc không, nếu lò đã từng chạy quá nóng.
- Sò cao tần đã bị ảnh hưởng chưa, nếu quạt yếu đã kéo dài.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng sò cao tần** — `faults/MW_MAGNETRON.md`

- Sò cao tần thay thế có còn hàng cho model đó không, và có đúng công suất không.
- Hỏng nằm ở sò, ở diode, ở tụ, hay ở biến áp cao áp. Bốn chi tiết cho cùng triệu chứng và chênh nhau nhiều về giá. Cần đo.
- Công tắc cửa có phải nguyên nhân không, vì trên một số lò nó cắt mạch cao áp mà vẫn cho mâm và đèn chạy.
- Quạt tản nhiệt có còn làm việc không, vì quạt yếu là nguyên nhân gốc làm sò chết sớm.
- Các chi tiết còn lại trong mạch cao áp còn dùng được bao lâu, nếu khách quyết thay sò.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Không lên nguồn, đứt cầu chì** — `faults/MW_NO_POWER.md`

- Nguyên nhân gốc làm đứt cầu chì. Đây là câu hỏi quan trọng nhất của mã này, vì chi phí của năm nguyên nhân chênh nhau rất nhiều.
- Công tắc cửa có phải nguyên nhân không. Nhánh phổ biến nhất.
- Các chi tiết trong mạch cao áp còn nguyên không.
- Nhánh điện của bếp có chịu được tải của lò không, nếu aptomat hay nhảy.
- Lò còn đáng sửa không, sau khi biết nguyên nhân gốc.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng mô tơ mâm xoay** — `faults/MW_TURNTABLE_MOTOR.md`

- Mô tơ mâm xoay thay thế có đúng cho model đó không.
- Mâm và vòng lăn thay thế có đúng đường kính và đúng kiểu rãnh không.
- Mô tơ hỏng hay chỉ là dây và mối nối tới nó bị đứt. Nhánh sau rẻ hơn.
- Đáy lò có bị rỉ thủng do nước chảy xuống lâu ngày không. Nếu có thì vấn đề vượt ra khỏi mã này.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Lò vi sóng** — `devices/microwave_oven.md`

- Mức rò sóng cho phép và cách đo. Chỉ đo được bằng thiết bị chuyên dụng, không có cách nào kiểm tra tại nhà, và không nên tin các mẹo kiểm tra bằng điện thoại.
- Sò cao tần còn tốt không. Cần đo, và việc đo nằm ở phần có tụ cao áp.
- Cửa và lưới chắn còn giữ được sóng không.
- Cầu chì đứt vì lý do gì. Cầu chì đứt là hậu quả chứ không phải nguyên nhân, và thay chì mà không tìm gốc thì nó đứt tiếp.
- Lò có còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Ổ cắm điện — 45 mục

**Vỡ, nứt mặt ổ cắm** (KHẨN) — `faults/OUTLET_BROKEN_FACE.md`

- Đế âm tường có còn nguyên không, và lỗ vít có bị doa rộng không.
- Vết nứt do va đập hay do nhiệt. Nếu do nhiệt thì nguyên nhân gốc là gì.
- Vít bắt dây phía sau có lỏng không, và đầu dây có bị ảnh hưởng không.
- Đoạn dây nối vào ổ có còn nguyên cách điện không, nếu ổ đã từng nóng.
- Ổ đặt ở vị trí đó có đúng quy định không, với ổ ở khu vực ẩm.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Quá tải, dùng quá nhiều thiết bị một ổ** (KHẨN) — `faults/OUTLET_OVERLOAD.md`

- Tiết diện dây nhánh và dòng định mức của aptomat có phù hợp nhau không.
- Tổng tải thực tế của nhánh đó là bao nhiêu, và nó vượt bao nhiêu so với khả năng.
- Các ổ cắm trong phòng có cùng một nhánh không.
- Có cần kéo nhánh riêng cho thiết bị nặng không, và kéo từ đâu.
- Dây hiện có đã lão hoá tới mức nào, ở nhà cũ.
- Nhà có aptomat chống dòng rò không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Chập cháy ổ cắm** (KHẨN) — `faults/OUTLET_SHORT_CIRCUIT.md`

- Đoạn dây nối vào ổ có bị nhiệt làm hỏng cách điện không, và cần cắt bỏ tới đâu.
- Đường dây trong tường có bị ảnh hưởng không.
- Aptomat của nhánh còn làm việc đúng không, sau khi đã cắt một dòng chập.
- Các ổ khác trên cùng nhánh có cùng tình trạng không.
- Tiết diện dây có phù hợp với tải thực tế không, nếu nghi nguyên nhân gốc là quá tải.
- Nhà có aptomat chống dòng rò không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rò điện làm nhảy aptomat** (KHẨN) — `faults/OUTLET_TRIPS_BREAKER.md`

- Nhà dùng aptomat thường hay aptomat chống dòng rò, và nó còn làm việc không.
- Thiết bị nào đang rò, và rò ở mức bao nhiêu. Cần đo.
- Điện trở cách điện của đường dây nhánh đó. Đây là phép đo quyết định khi nghi dây chứ không nghi thiết bị.
- Tiết diện dây và dòng định mức của aptomat có phù hợp nhau không.
- Nhà có dây nối đất thật không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Lỏng tiếp xúc, ổ cắm rơ** — `faults/OUTLET_LOOSE_CONTACT.md`

- Vít bắt dây phía sau ổ có lỏng không. Đây là chỗ nguy hiểm hơn và nó không nhìn thấy được từ ngoài.
- Lá tiếp xúc đã mòn tới mức nào.
- Đoạn dây nối vào ổ có bị nhiệt làm ảnh hưởng chưa.
- Phích cắm của thiết bị có còn đúng cỡ không, nếu nghi phích làm banh ổ.
- Các ổ khác trong nhà có cùng tình trạng không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Ổ cắm mất điện, đứt dây** — `faults/OUTLET_NO_POWER.md`

- Vị trí điểm đứt hoặc điểm mất tiếp xúc trên đường dây. Cần dò bằng thiết bị.
- Nguyên nhân aptomat nhảy, nếu đó là nhánh được xác định.
- Mối nối trong các hộp điện còn chắc không.
- Dây của nhánh đã lão hoá tới mức nào, ở nhà cũ, và có nên kéo lại cả nhánh không.
- Có nên xử lý bằng cách kéo dây mới đi nổi thay vì đục tường không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Ổ cắm điện** — `devices/power_outlet.md`

- Tiết diện dây của nhánh và dòng định mức của aptomat có phù hợp với tải thực tế không.
- Nhà có dây nối đất thật không, và ổ ba lỗ có được nối đất không.
- Nhà có aptomat chống dòng rò không, và nó còn làm việc không.
- Nguyên nhân gốc nằm ở ổ cắm hay ở nhánh dây. Quyết định việc thay ổ có đủ hay không.
- Đường dây trong tường có bị lão hoá hoặc bị chuột cắn không.
- Vị trí ổ cắm ở khu vực ẩm có đúng quy định không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Tivi — 39 mục

**Hỏng dải đèn nền** — `faults/TV_BACKLIGHT.md`

- Dải đèn nền có còn hàng cho model đó không. Với model đời cũ thì có thể không còn.
- Bệnh nằm ở dải led hay ở mạch cấp cho đèn nền trên bo nguồn. Hai cái cho triệu chứng giống hệt nhưng chi phí khác nhau.
- Tấm nền có còn nguyên không, khi phép thử đèn pin không cho kết quả rõ.
- Máy có còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng bo xử lý tín hiệu** — `faults/TV_MAIN_BOARD.md`

- Bo xử lý thay thế có còn hàng cho model đó không.
- Bệnh nằm ở bo xử lý hay bo nguồn, khi triệu chứng là bật tắt lặp lại. Cần đo.
- Bo T-CON có phải nguyên nhân không, khi triệu chứng là hình vỡ.
- Có sửa được bằng cách hàn lại mối tiếp xúc không, hay phải thay cả bo.
- Bo nguồn có cấp đúng điện áp không, vì bo nguồn sai mức kéo theo bo xử lý.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Mất tiếng, hỏng loa** — `faults/TV_NO_SOUND.md`

- Loa thay thế có đúng cho model đó không, hay phải dùng loa tương đương.
- Mất tiếng do loa, do mạch khuếch đại, hay do phần giải mã trên bo xử lý. Cần đo để tách.
- Dây nối từ bo tới loa có còn nguyên không, nhất là nếu máy từng có chuột.
- Máy có còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Vỡ, lỗi tấm nền** — `faults/TV_PANEL_DAMAGE.md`

- Tấm nền có thay rời được cho model đó không, và có còn hàng không. Câu hỏi phải trả lời trước khi bàn tới giá.
- Lỗi nằm ở tấm nền hay ở mối nối cáp mềm. Hai cái cho triệu chứng giống nhau nhưng chi phí khác hẳn.
- Bo T-CON có phải nguyên nhân không.
- Máy có còn hạn bảo hành không, và hãng có chính sách hỗ trợ thay tấm nền không.
- Tấm nền thay thế là hàng mới hay hàng tháo máy.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng bo nguồn** — `faults/TV_POWER_BOARD.md`

- Bo nguồn thay thế có đúng cho model đó không, hay nên sửa bo cũ.
- Bệnh nằm ở bo nguồn hay bo xử lý, khi triệu chứng là bật lên rồi tự tắt. Cần đo.
- Có hỏng thêm bo nào khác không, nếu nguyên nhân là sét.
- Mạch cấp cho đèn nền còn tốt không, khi triệu chứng là có tiếng mà màn tối.
- Máy có còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng điều khiển, mắt nhận** — `faults/TV_REMOTE_FAULT.md`

- Điều khiển thay thế có đúng loại cho model đó không, nhất là với smart tv cần các nút riêng.
- Remote dùng hồng ngoại hay sóng vô tuyến, nếu khách không chắc.
- Mắt nhận có hỏng không, khi đã loại hết các nhánh khác. Cần đo.
- Mắt nhận có nằm trên bo riêng thay được không, hay gắn liền bo xử lý.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Tivi** — `devices/television.md`

- Tấm nền có thay rời được cho model đó không, và có còn hàng không. Với nhiều model đời cũ thì không còn.
- Loại tấm nền là led hay oled, nếu khách không biết. Nó loại hẳn một nhánh chẩn đoán.
- Bo nào đang hỏng, khi triệu chứng nằm ở nhóm hình ảnh lỗi. Không tách được qua tin nhắn.
- Máy còn hạn bảo hành không. Nếu còn thì mọi phép tính sửa hay thay đều không áp dụng.
- Giá treo tường có bắt đúng phần chịu lực không, nếu khách nhắc tới tivi nghiêng hoặc giá lỏng.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Bồn cầu — 41 mục

**Rò rỉ chân bồn cầu** (KHẨN) — `faults/TOILET_BASE_LEAK.md`

- Mặt bích thoát còn nguyên không, và chiều cao của nó so với mặt sàn có đúng không.
- Vòng đệm thuộc loại nào và loại thay thế có phù hợp không.
- Thân sứ có nứt ở đáy không. Rất khó thấy vì nằm khuất.
- Sàn đã thấm tới đâu, và có cần xử lý chống thấm không.
- Ống thoát phía dưới có bị nứt hoặc lệch không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nghẹt bồn cầu** (KHẨN) — `faults/TOILET_CLOGGED.md`

- Nghẹt nằm ở bồn cầu, ở đường ống của căn hộ, hay ở trục chung của toà nhà.
- Có vật rắn trong ống không, và nó nằm ở đâu.
- Bể phốt có đầy không, nếu nghẹt lặp lại.
- Ống thoát có đủ độ dốc không, và có bị võng không.
- Ống thông hơi có thông không.
- Thân sứ có bị nứt không, nếu khách đã dùng hoá chất hoặc nước sôi.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng van cấp nước két** — `faults/TOILET_FILL_VALVE.md`

- Van cấp thay thế có đúng kiểu vào nước và đúng chiều cao cho két đó không.
- Áp lực nước tại vị trí đó có đủ không, nếu nghi nguyên nhân là áp lực.
- Gioăng ở đáy két chỗ van cấp đi qua có còn kín không, nếu phải tháo van.
- Bộ xả có còn tốt không, để quyết định có thay cùng lúc.
- Đường ống có cặn nhiều không, nếu lưới lọc bẩn lại nhanh sau khi đã rửa.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rò van xả, chảy nước liên tục** — `faults/TOILET_FLAPPER_LEAK.md`

- Bộ xả thay thế có tương thích với két của model đó không, nhất là với bồn đời cũ.
- Miệng lỗ xả đã mòn tới mức nào, và thay nắp có đủ không.
- Van cấp có còn tốt không, để quyết định có nên thay cùng lúc.
- Gioăng giữa két và thân bồn có còn kín không, nếu phải tháo bộ xả ra.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Gãy, lỏng nắp bồn cầu** — `faults/TOILET_SEAT_BROKEN.md`

- Kiểu miệng bồn và khoảng cách lỗ bắt ốc, nếu khách không đo được hoặc không chắc.
- Bồn cầu có phải loại dùng nắp rửa hoặc nắp thông minh không, vì loại đó không thay tự do.
- Miệng bồn có bị nứt quanh lỗ ốc không, nếu đã từng siết quá tay.
- Đai ốc cũ có tháo ra được không, nếu đã rỉ chặt.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Xả yếu, nghẹt lỗ xả vành** — `faults/TOILET_WEAK_FLUSH.md`

- Lỗ vành có thông được hoàn toàn không, hay đã tắc tới mức không phục hồi.
- Lòng ống cong si phông có đóng cặn không, và men trong đó có bị rỗ không.
- Mực nước két đúng cho model đó là bao nhiêu, nếu két không có vạch đánh dấu.
- Bộ xả có mở đủ hành trình không.
- Áp lực nước tại vị trí đó có đủ không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Bồn cầu** — `devices/toilet.md`

- Bồn cầu dùng kiểu ống xả nào và phụ kiện thay thế có tương thích không, nhất là với bồn đời cũ.
- Thân sứ có nứt không. Vết nứt nhỏ rất khó thấy và đôi khi chỉ lộ ra khi đã thấm sàn.
- Nguyên nhân nghẹt nằm ở bồn, ở đường ống của căn hộ, hay ở trục chung.
- Bể phốt có đầy không, nếu nghẹt lặp lại nhiều lần.
- Gioăng chân bồn và mặt bích thoát có còn kín không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Đường ống nước — 47 mục

**Vỡ ống, xì nước mạnh** (KHẨN) — `faults/PIPE_BURST.md`

- Vị trí chính xác của điểm vỡ. Cần dò bằng thiết bị nếu ống nằm trong tường hoặc dưới nền.
- Vật liệu ống và tuổi của tuyến, quyết định giữa sửa điểm và thay tuyến.
- Có hư hỏng ở đoạn khác trên cùng tuyến không.
- Phần tường, sàn hoặc trần đã ngấm tới đâu, và có cần xử lý chống thấm không.
- Nhánh điện ở khu vực đã ngập có an toàn để dùng lại không.
- Sự cố thuộc phần của căn hộ hay phần chung của toà nhà, với chung cư.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nghẹt đường ống thoát** — `faults/PIPE_CLOGGED.md`

- Nghẹt nằm ở nhánh nào, và có phải trục chung của toà nhà không.
- Bể phốt có đầy không.
- Ống thoát có đủ độ dốc không, và có bị võng không.
- Ống thông hơi có thông không.
- Có rễ cây trong ống không, ở nhà có sân vườn.
- Sự cố thuộc phần sở hữu riêng hay phần sở hữu chung, với chung cư.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rò rỉ mối nối đường ống** — `faults/PIPE_JOINT_LEAK.md`

- Vị trí chính xác của mối nối bị rò. Cần dò bằng thiết bị nếu nằm trong tường.
- Vật liệu ống và kiểu mối nối, quyết định cách xử lý.
- Có mối nối nào khác trên cùng tuyến cũng sắp hỏng không.
- Phần tường, sàn hoặc trần đã ngấm tới đâu, và có cần xử lý chống thấm không.
- Nên sửa điểm hay nên đi tuyến mới, với nhà có hệ thống đã lão hoá.
- Sự cố thuộc phần của căn hộ hay phần chung của toà nhà, với chung cư.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nước đục, rỉ sét đường ống** — `faults/PIPE_RUSTY_WATER.md`

- Nguồn gây đục nằm ở đường ống trong nhà, ở bể chứa, ở bình nóng lạnh, hay ở nguồn cấp.
- Vật liệu ống và tuổi của tuyến.
- Chất lượng nước có đạt yêu cầu không. Chỉ xét nghiệm mới trả lời được, và hệ thống này không kết luận được từ mô tả hay từ ảnh.
- Bể chứa có cần vệ sinh không, và nắp có kín không.
- Hệ lọc có phù hợp với loại cặn đang gặp không, nếu khách định lắp lọc.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Áp lực nước yếu toàn nhà** — `faults/PIPE_LOW_PRESSURE.md`

- Áp lực thực tế tại điểm vào nhà là bao nhiêu. Cần đo, và nó là căn cứ quyết định có nên lắp bơm không.
- Vật liệu ống và tuổi của tuyến, quyết định giữa xử lý điểm và thay tuyến.
- Lòng ống có bị hẹp tới mức nào, nếu nghi rỉ hoặc cặn.
- Bơm và rơ le áp có làm việc đúng không, ở nhà có bơm.
- Có chỗ rò nào đang lấy nước không, nếu áp tụt đột ngột.
- Việc lắp bơm hút trực tiếp có được phép ở khu vực đó không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Ống kêu, búa nước** — `faults/PIPE_NOISY.md`

- Đường ống có được cố định đúng cách không, và khoảng cách kẹp có phù hợp không.
- Áp lực làm việc thực tế là bao nhiêu, nếu nhà có bơm.
- Có nên lắp thiết bị giảm chấn không, và lắp ở đâu.
- Tiết diện lòng ống có bị hẹp không, nếu tiếng đi kèm áp lực yếu.
- Có chỗ rò nào không, nếu nghe tiếng nước khi mọi vòi đều khoá.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đường ống nước** — `devices/water_pipe.md`

- Vật liệu ống đang dùng và tuổi của hệ thống. Quyết định cả chẩn đoán lẫn phương án xử lý.
- Vị trí chính xác của chỗ rò. Cần dò bằng thiết bị.
- Đường ống đi theo tuyến nào, ở nhà không có bản vẽ.
- Áp lực nước tại điểm vào nhà là bao nhiêu, nếu nghi nhánh áp yếu.
- Lòng ống có bị hẹp do rỉ hoặc do cặn không.
- Sự cố thuộc phần của căn hộ hay phần chung của toà nhà, với chung cư.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Quạt trần — 36 mục

**Cháy cuộn dây mô tơ quạt trần** (KHẨN) — `faults/CEILFAN_MOTOR_BURNT.md`

- Nguồn mùi khét là mô tơ, bộ đèn, mối nối trong bát treo, hay hộp số trên tường. Bốn nguồn không tách được qua tin nhắn.
- Mức độ cháy của cuộn dây, và còn cứu được không.
- Quấn lại có đáng với model đó không, sau khi biết công quấn và giá quạt tương đương.
- Tụ và bạc có phải nguyên nhân gốc không, vì thay mô tơ mà không xử lý gốc thì bệnh quay lại.
- Mối nối trong hộp đấu dây trên trần và nhánh điện của phòng có vấn đề gì không, nếu quạt làm nhảy aptomat.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Lỏng bộ treo, mất cân bằng cánh** (KHẨN) — `faults/CEILFAN_MOUNT_LOOSE.md`

- Kết cấu trần tại vị trí lắp có chịu được tải treo động không. Đây là câu hỏi quyết định và nó chỉ trả lời được sau khi mở ra xem.
- Con nở hoặc vít còn bám chắc không, và lỗ có bị doa rộng không.
- Chốt an toàn hoặc cáp phụ có được lắp không, và còn nguyên không.
- Khớp cầu treo có mòn không.
- Bộ cánh có cần cân lại không, và cánh nào lệch.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Khô dầu, mòn bạc trục quạt trần** — `faults/CEILFAN_BEARING.md`

- Quạt dùng bạc đồng hay vòng bi, và có tra dầu được từ ngoài không.
- Bạc còn dùng được sau khi tra dầu hay đã mòn phải thay. Cần đo khe hở mới chắc.
- Cụm quay đã tụt xuống chưa, tức là bạc dưới đã mòn tới mức nào.
- Trục có mòn hoặc cong không, vì trục mòn thì thay bạc mới cũng không hết khe hở.
- Bộ treo có bị ảnh hưởng chưa, nếu quạt đã rung một thời gian.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng hộp số, chiết áp** — `faults/CEILFAN_SPEED_SWITCH.md`

- Loại bộ chỉnh tốc độ đang dùng, kiểu cuộn kháng hay kiểu điện tử. Quyết định cả hướng chẩn đoán lẫn linh kiện thay thế.
- Bộ thay thế có tương thích với model quạt không, nhất là với loại điện tử.
- Mối nối trong đế âm tường và trên trần có còn chắc không. Đây là nhánh rẻ hay bị bỏ sót.
- Hộp số có phát nhiệt tới mức nguy hiểm chưa, khi mặt nhựa đã ố.
- Tụ của quạt có còn tốt không, để loại trừ nhánh kia.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng tụ điện quạt trần** — `faults/CEILFAN_CAPACITOR.md`

- Trị số tụ đúng cho model quạt trần đó. Đọc trên thân tụ cũ hoặc tra theo model, không suy đoán.
- Cuộn dây mô tơ còn nguyên không, nếu quạt đã bị ù kéo dài trước khi gọi.
- Bạc trục có còn trơn không, vì tụ mới lắp vào một mô tơ bạc nặng thì vẫn quay chậm.
- Bộ chỉnh tốc độ trên tường có còn đúng không, để loại trừ nhánh kia trong cùng một lần.
- Bộ treo có còn chắc không. Khi đã hạ quạt xuống thì đây là lúc kiểm tra luôn.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Quạt trần** — `devices/ceiling_fan.md`

- Kết cấu trần tại vị trí lắp có chịu được tải treo động không. Đây là câu hỏi quan trọng nhất của cụm và không trả lời được từ dưới sàn.
- Trị số tụ đúng cho từng model.
- Bạc trục còn dùng được sau khi tra dầu hay đã mòn.
- Chốt an toàn hoặc cáp phụ có được lắp không, và còn nguyên không.
- Loại bộ chỉnh tốc độ đang dùng, vì hai loại đi hai hướng chẩn đoán khác nhau.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Máy sấy quần áo — 14 mục

**Tắc lọc xơ vải, tắc đường thoát ẩm** (KHẨN) — `faults/DRYER_LINT_CLOGGED.md`

- Chu kỳ hút xơ đường ống nên khuyến nghị cho căn hộ Việt Nam, vì con số của nhà sản xuất tính cho nhà có đường ống ngắn và thẳng.
- Máy bơm nhiệt có cần hút ống không hay chỉ cần vệ sinh dàn ngưng, vì loại này không có ống thoát ra ngoài.
- Cầu chì nhiệt đứt rồi thì thay được rời hay phải thay cả cụm, trên các dòng phổ biến ở Việt Nam.
**Máy sấy không ra hơi nóng** — `faults/DRYER_NOT_HEATING.md`

- Thời gian một mẻ tiêu chuẩn của máy bơm nhiệt bán ở Việt Nam, để nói được con số thay vì nói "lâu hơn". Đây là câu khách hỏi ngay sau khi nghe giải thích, và hiện tài liệu chưa trả lời được.
- Cầu chì nhiệt thay rời được trên những dòng nào, và dòng nào phải thay cả cụm. Chên lệch chi phí giữa hai trường hợp đủ lớn để khách muốn biết trước.
- Cảm biến độ ẩm bám cặn thì lau bằng gì cho an toàn, vì đây là việc khách tự làm được nếu được chỉ đúng cách, mà chỉ sai thì xước lá cảm biến.
**Lồng máy sấy không quay** — `faults/DRYER_NOT_SPINNING.md`

- Dây curoa thay rời được trên dòng nào tại Việt Nam, và dòng nào phải đặt theo model — điều này quyết định thợ đi một lượt hay hai.
- Tuổi thọ dây curoa theo số mẻ sấy, để trả lời được câu "bao lâu thì phải thay" bằng con số.
**Máy sấy không lên nguồn** — `faults/DRYER_NO_POWER.md`

- Công tắc cửa thay rời được trên dòng nào bán ở Việt Nam, để thợ mang sẵn.
- Máy sấy có cần đường điện riêng không theo công suất phổ biến ở Việt Nam, vì khách hay cắm chung ổ với máy giặt và đây là câu tư vấn đáng giá.
**Máy sấy kêu to, lồng sấy rơ** — `faults/DRYER_NOISY.md`

- Con lăn đỡ lồng thay theo cặp hay thay lẻ được, vì điều đó quyết định chi phí và khách hay hỏi trước.
- Tiếng máy bơm nhiệt bình thường to cỡ nào so với máy thông hơi, để trả lời được câu "máy kêu thế có bình thường không" mà không phải so với trí nhớ của khách.
**Máy sấy quần áo** — `devices/clothes_dryer.md`

- Tỉ lệ máy bơm nhiệt so với máy thông hơi trong số ca gọi tại Việt Nam, vì lời khuyên đầu tiên khác nhau giữa hai loại.
- Chu kỳ vệ sinh dàn ngưng nên khuyến nghị cho khí hậu ẩm, vì con số của nhà sản xuất tính cho khí hậu khô hơn.

## Máy rửa bát — 12 mục

**Rò nước cửa máy rửa bát** — `faults/DW_DOOR_LEAK.md`

- Gioăng cửa thay rời được trên dòng nào bán ở Việt Nam, và dòng nào phải đặt theo model — quyết định thợ đi một lượt hay hai.
- Ngưỡng bọt của nước rửa chén thường gây tràn là bao nhiêu, để nói được cụ thể thay vì chỉ nói "đừng dùng".
**Máy rửa bát không thoát nước** — `faults/DW_NOT_DRAINING.md`

- Chiều cao tối thiểu của khúc uốn ống xả theo hướng dẫn lắp đặt, để nói được con số thay vì nói "phải có khúc uốn".
- Với máy âm tủ đấu cứng, ngắt điện ở đâu trên các mẫu tủ bếp phổ biến, vì lời khuyên "ngắt aptomat nhánh bếp" chỉ đúng khi tủ bếp có nhánh riêng.
**Máy rửa bát không lên nguồn** — `faults/DW_NO_POWER.md`

- Phao chống tràn ở khay đáy có trên dòng nào, và thợ xoá cảnh báo đó bằng cách nào, để nói trước cho khách biết thợ sẽ làm gì.
- Với máy âm tủ đấu cứng, ngắt điện ở đâu trên các mẫu tủ bếp phổ biến — vì lời khuyên "ngắt aptomat nhánh bếp" chỉ đúng khi tủ bếp có nhánh riêng.
**Máy rửa bát không cấp nước** — `faults/DW_NO_WATER.md`

- Van cấp nước thay rời được trên dòng nào bán ở Việt Nam, để thợ mang sẵn.
- Áp lực nước vào tối thiểu của máy rửa bát dân dụng, để tư vấn được cho nhà dùng bể ngầm thay vì chỉ nói "cần áp lực nhất định".
**Máy rửa bát rửa không sạch** — `faults/DW_NOT_CLEAN.md`

- Độ cứng nước máy ở Hà Nội và Thành phố Hồ Chí Minh, để tư vấn lượng muối cụ thể thay vì nói chung chung.
- Có nên khuyên khách dùng viên rửa ba trong một thay cho muối rời hay không, vì với nước quá cứng thì viên tích hợp không đủ.
**Máy rửa bát** — `devices/dishwasher.md`

- Loại muối và chất trợ xả phù hợp với độ cứng nước máy ở Hà Nội và Thành phố Hồ Chí Minh, để tư vấn cụ thể thay vì nói chung chung.
- Máy nhập khẩu 110V chiếm bao nhiêu trong số ca gọi, để biết có nên hỏi ngay từ đầu hay không.

## Ấm đun nước — 40 mục

**Rò nước ở đáy bình** (KHẨN) — `faults/KETTLE_LEAK.md`

- Có rò điện ra vỏ không. Cần đo, và đây là câu hỏi quan trọng nhất nếu khách đã thấy tê tay.
- Rò nước xuất phát từ gioăng mâm nhiệt, từ mối ghép, hay từ thân ấm nứt.
- Cụm tiếp điểm ở đáy ấm và ở đế có bị cháy không.
- Mâm nhiệt còn nguyên lớp bảo vệ không, nếu đã từng bị cạo cặn bằng vật cứng.
- Ấm còn hạn bảo hành không.
- Nhà có aptomat chống dòng rò không, và nó còn làm việc không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng công tắc, chân tiếp xúc** — `faults/KETTLE_SWITCH.md`

- Cụm tiếp điểm ở đế có bị cháy không, và nhựa quanh đó đã bị nhiệt tới mức nào.
- Đế cắm có bán rời cho model đó không, nếu vấn đề nằm ở đế hoặc ở dây.
- Công tắc và lẫy giữ có thay riêng được không.
- Có rò điện ra vỏ không, nếu tiếp điểm đã ướt hoặc đã cháy.
- Ấm có đang rò ở đáy không, nếu đế ướt mà khách không rót tràn.
- Ấm còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng rơ le nhiệt** — `faults/KETTLE_THERMOSTAT.md`

- Rơ le có còn tốt không, sau khi đã tẩy cặn và đã kiểm nắp cùng mực nước.
- Đường dẫn hơi có thông không.
- Rơ le chống cạn có cắt ở đúng ngưỡng không.
- Mâm nhiệt có bị ảnh hưởng chưa, nếu ấm đã bị đun tới cạn nhiều lần vì không tự tắt.
- Gioăng quanh mâm nhiệt có còn kín không, cùng lý do.
- Ấm còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng mâm nhiệt** — `faults/KETTLE_HEATING_BASE.md`

- Mâm nhiệt hỏng hay chỉ mất điện tới nó. Cần đo để tách.
- Rơ le chống cạn có hỏng ở trạng thái cắt không, và trên model đó nó có thay riêng được không.
- Cụm tiếp điểm ở đáy ấm và ở đế có còn tốt không.
- Gioăng quanh mâm còn kín không, nếu ấm đã từng bị đun cạn.
- Ấm còn hạn bảo hành không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đóng cặn vôi trong bình** — `faults/KETTLE_SCALE.md`

- Mâm nhiệt có bị hỏng lớp bảo vệ do cạo cặn không, nếu khách đã từng cạo.
- Mâm nhiệt còn nguyên không, nếu ấm đã đun lâu với lớp cặn dày trong nhiều năm.
- Rơ le có còn tốt không, nếu tẩy cặn xong mà ấm vẫn tắt sớm hoặc vẫn không tự tắt.
- Cặn màu bất thường đến từ nguồn nước hay từ chính cái ấm.
- Chất lượng nước có vấn đề gì không, nếu nước có mùi hoặc vị lạ. Cần xét nghiệm, và hệ thống này không kết luận được.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Ấm siêu tốc** — `devices/kettle.md`

- Ấm có đáng sửa không so với giá thay mới. Với cụm này, câu trả lời thường là không.
- Rò nước xuất phát từ gioăng mâm nhiệt hay từ thân ấm nứt.
- Mâm nhiệt còn nguyên không, nếu ấm đã từng bị đun cạn.
- Cụm tiếp điểm ở đế có bị cháy không.
- Có rò điện ra vỏ không, nếu khách đã thấy tê tay. Cần đo.
- Nhà có aptomat chống dòng rò không, nếu đã có hiện tượng tê tay.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Bóng đèn — 39 mục

**Máng đèn thấm nước, hoen rỉ** (KHẨN) — `faults/LIGHT_FIXTURE_LEAK.md`

- Nguồn nước ở đâu, và phần thấm đã lan tới đâu. Đây là câu hỏi quan trọng nhất và nó thường không trả lời được từ dưới.
- Đã có chạm chập trong máng đèn hoặc trong khoang trần chưa.
- Đèn ở vị trí đó cần cấp bảo vệ nào.
- Trần thạch cao đã hỏng tới mức nào, và có cần thay tấm không.
- Các mối nối điện trong khoang trần có bị ảnh hưởng không.
- Nhà có aptomat chống dòng rò không, và nó còn làm việc không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đèn chớp nháy, hỏng driver** — `faults/LIGHT_FLICKERING.md`

- Mối nối trên nhánh có lỏng không. Đây là nhánh quan trọng nhất về an toàn và nó không kiểm được từ ngoài.
- Điện áp trên nhánh có ổn định không.
- Tiết diện dây có đủ không, nếu đèn tối rõ rệt khi tải lớn khởi động.
- Driver có thay rời được không.
- Công tắc có phải loại chỉnh độ sáng hoặc loại có đèn báo không, nếu khách không chắc.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng công tắc đèn** — `faults/LIGHT_SWITCH_FAULT.md`

- Mạch có phải công tắc hai chiều không, nếu khách không chắc.
- Vít bắt dây trong hộp công tắc có lỏng không.
- Đầu dây nối vào công tắc có bị nhiệt làm giòn cách điện không, nếu nhựa đã ố.
- Đế âm tường có còn nguyên không.
- Công tắc có đang gánh tải lớn hơn mức thiết kế không.
- Các công tắc khác trong nhà có cùng tình trạng không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Bóng đèn cháy, hết tuổi thọ** — `faults/LIGHT_BULB_DEAD.md`

- Đui đèn và dây tới đèn có còn tốt không, khi bóng mới cũng không sáng.
- Driver có thay rời được không, với đèn led lớn hoặc đèn âm trần.
- Nguyên nhân bóng cháy lặp lại ở cùng một vị trí. Cần đo điện áp và kiểm tra đui.
- Điện áp trên nhánh đó có bất thường không.
- Máng đèn có thoát nhiệt được không, với đèn âm trần trong trần thạch cao.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đèn sáng yếu, điện áp thấp** — `faults/LIGHT_DIM.md`

- Điện áp trên nhánh có đủ không, nếu nhiều đèn cùng yếu. Cần đo.
- Có mối nối kém ở đâu trên nhánh không.
- Tiết diện dây có đủ không, nếu đèn tối rõ khi tải lớn khởi động, hoặc nếu đèn cuối dãy yếu hơn đèn đầu dãy.
- Máng đèn có chịu được công suất cao hơn không, nếu khách muốn thay bóng sáng hơn.
- Chấn lưu có còn tốt không, với đèn tuýp mà ống mới thay vào vẫn mờ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Đèn chiếu sáng** — `devices/light_bulb.md`

- Loại đèn và loại driver đang dùng, và driver có thay rời được không.
- Nhánh điện có vấn đề gì không, nếu nhiều đèn cùng chớp.
- Mối nối trong trần hoặc trong hộp điện có lỏng không.
- Nguồn nước ở đâu, nếu đèn bị thấm.
- Đèn ở khu vực ẩm có đúng cấp bảo vệ không.
- Tiết diện dây có đủ không, nếu đèn sáng yếu ở cuối dãy dài.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Lò nướng — 39 mục

**Nứt kính cửa, hỏng bản lề** — `faults/OVEN_DOOR_GLASS.md`

- Kính thay thế có đúng loại chịu nhiệt, đúng kích thước và đúng độ dày không.
- Kính có bán rời cho model đó không, hay phải thay cả cụm cửa.
- Vết nứt nằm ở lớp kính nào.
- Bản lề có chỉnh lại được không, hay phải thay.
- Gioăng thay thế có đúng loại và đúng kiểu ngàm không.
- Quạt làm mát vỏ có chạy không, nếu mặt ngoài cửa nóng bất thường.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng thanh nhiệt** — `faults/OVEN_HEATING_ELEMENT.md`

- Thanh nhiệt thay thế có đúng công suất, đúng kích thước, và đúng kiểu chân không.
- Có nên thay cả hai thanh cùng lúc không, nếu chúng cùng tuổi.
- Vỏ thanh nhiệt có nứt không, nếu lò làm nhảy aptomat.
- Chi tiết nào cấp điện chung cho cả hai thanh đang hỏng, nếu không thanh nào đỏ.
- Cầu chì nhiệt có đứt không, và vì lý do gì.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng rơ le nhiệt** — `faults/OVEN_THERMOSTAT.md`

- Rơ le lệch bao nhiêu so với nhiệt độ thực. Cần đo bằng thiết bị chuẩn.
- Hỏng nằm ở cảm biến hay ở bo điều khiển, với lò điện tử.
- Cầu chì nhiệt có đứt không, và vì lý do gì.
- Thanh nhiệt còn nguyên cả hai không, để loại nhánh kia.
- Gioăng cửa còn kín không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng bộ hẹn giờ, công tắc** — `faults/OVEN_TIMER_FAULT.md`

- Bộ hẹn giờ có nằm trên mạch cấp cho thanh nhiệt không, với model đó.
- Hỏng nằm ở màng phím hay ở bo điều khiển, với lò điện tử. Chênh lệch chi phí lớn.
- Ý nghĩa của mã lỗi, tra theo đúng model. Không suy đoán.
- Cầu chì nhiệt có đứt không, và nguyên nhân gốc là gì.
- Rơ le nhiệt có còn cắt đúng không, để loại nhánh kia.
- Lò có đủ khe thoáng không, nếu nghi quá nhiệt.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng quạt đối lưu** — `faults/OVEN_FAN_FAULT.md`

- Quạt nào đang hỏng, quạt đối lưu hay quạt làm mát vỏ.
- Lò có quạt đối lưu không, nếu khách không chắc.
- Mô tơ quạt còn tốt không, hay chỉ là bạc khô và muội bám.
- Hốc tủ có đủ khe thoáng theo yêu cầu lắp đặt không, với lò âm tủ.
- Các linh kiện bên trong đã bị ảnh hưởng chưa, nếu quạt làm mát đã hỏng một thời gian.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Lò nướng** — `devices/oven.md`

- Thanh nhiệt thay thế có đúng công suất và đúng kiểu chân không.
- Rơ le nhiệt còn đúng không. Cần đo hoặc cần so với nhiệt kế lò.
- Cầu chì nhiệt đứt vì lý do gì, nếu nó đã đứt.
- Bo điều khiển có đáng sửa không, với lò điện tử.
- Kính cửa thay thế có đúng loại chịu nhiệt không.
- Lò có đủ khe thoáng theo yêu cầu lắp đặt không, với lò âm tủ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Khóa cửa thông minh — 12 mục

**Khóa không đọc thẻ từ, mã số sai** — `faults/LOCK_CARD_FAULT.md`

- Số lần nhập sai trước khi khoá tự khoá tạm và thời gian khoá, theo từng hãng — để nói được con số cụ thể cho khách đang chờ.
- Thẻ từ sao chép thêm được ở đâu, và có rủi ro bảo mật gì khi sao chép, vì khách hỏi câu này rất nhiều và hiện tài liệu chưa dám trả lời.
**Khóa vân tay không nhận vân** — `faults/LOCK_FINGERPRINT_FAIL.md`

- Số vân tay tối đa đăng ký được trên các dòng phổ biến ở Việt Nam, để nói chắc với khách là đăng ký nhiều lần một ngón không sợ hết ô.
- Dòng nào dùng cảm biến điện dung và dòng nào dùng cảm biến quang, vì lời khuyên về tay ẩm chỉ đúng với loại thứ nhất.
**Kẹt ngoài cửa, không vào được nhà** — `faults/LOCK_LOCKED_OUT.md`

- Thời gian thợ mở khoá khẩn cấp tới nơi trong giờ hành chính và ngoài giờ, để nói được điều gì đó cụ thể cho người đang đứng ngoài cửa.
- Giấy tờ thợ yêu cầu để xác minh chủ nhà, để báo trước cho khách chuẩn bị.
**Khóa thông minh hết pin** — `faults/LOCK_LOW_BATTERY.md`

- Dòng khoá nào ở Việt Nam đã bỏ hẳn cổng sạc khẩn cấp, vì lời khuyên quan trọng nhất ở đây chỉ đúng với dòng còn giữ nó.
- Tuổi thọ pin thực tế theo số lần mở mỗi ngày, để trả lời được câu "bao lâu thay một lần" bằng con số thay vì bằng khoảng.
**Mô tơ chốt khóa không chạy** — `faults/LOCK_MOTOR_FAULT.md`

- Mô tơ chốt thay rời được trên dòng nào và dòng nào phải thay cả thân khoá, vì chênh lệch chi phí lớn và khách muốn biết trước.
- Cửa xệ bao nhiêu milimet thì phải chỉnh bản lề chứ không chỉ mở rộng lỗ chốt, để thợ khỏi phải quay lại lần hai.
**Khóa cửa thông minh** — `devices/smart_lock.md`

- Hãng nào còn giữ ổ khoá cơ dự phòng và hãng nào đã bỏ hẳn, vì lời khuyên "tìm nắp nhựa che ổ cơ" chỉ đúng với nhóm thứ nhất.
- Thời gian trung bình thợ mở được một khoá bị kẹt chốt, để nói trước cho khách đang đứng ngoài cửa thay vì để họ chờ không biết bao lâu.

## Máy lọc nước — 13 mục

**Máy lọc nước rò rỉ nước** — `faults/PURIFIER_LEAK.md`

- Loại gioăng cốc lọc hay phải thay nhất trên các dòng bán ở Việt Nam, để thợ mang sẵn và khách không phải chờ thêm một lượt.
- Có nên khuyên lắp van khoá tự động chống tràn cho máy đặt gầm tủ không, và chi phí khoảng bao nhiêu — vì đây là thứ ngăn được nguyên nhóm sự cố này.
**Máy lọc nước không lên nguồn** — `faults/PURIFIER_NO_POWER.md`

- Thông số adapter của các dòng phổ biến, để thợ mang sẵn và khách không phải chờ thêm một lượt hẹn.
- Máy không bơm thì cần áp lực nước vào tối thiểu bao nhiêu, vì nhánh đó hiện được chuyển sang mã bệnh khác mà không có con số nào để nói.
**Máy lọc nước không ra nước** — `faults/PURIFIER_NO_WATER.md`

- Áp suất bơm hơi bình áp tiêu chuẩn của các dòng bán ở Việt Nam, để nói được con số khi khách hỏi thợ sẽ làm gì.
- Áp lực nước vào tối thiểu để máy RO chạy được, vì nhà dùng bể ngầm hỏi câu này rất nhiều và hiện tài liệu chỉ nói chung chung.
**Bơm máy lọc chạy liên tục** — `faults/PURIFIER_PUMP_RUNS_ON.md`

- Van áp cao thay rời được trên dòng nào bán ở Việt Nam, để thợ mang sẵn thay vì phải quay lại lần hai. Đây là linh kiện hỏng nhiều nhất của mã bệnh này.
- Bơm chạy khô khoảng bao lâu thì hỏng, để nói được mức độ gấp bằng thời gian thay vì nói chung chung là "sớm". Khách hỏi "để tới cuối tuần được không" rất nhiều và hiện tài liệu chưa trả lời được.
- Tiếng bơm bình thường to cỡ nào, vì khách hay hỏi "máy kêu thế có bình thường không" và hiện chỉ có cách so với chính nó lúc trước.
**Lõi lọc hết hạn, nước có mùi vị lạ** — `faults/PURIFIER_FILTER_DUE.md`

- Chu kỳ thay từng cấp lõi theo chất lượng nước máy từng quận, vì khoảng ba tới sáu tháng hiện đang quá rộng để tư vấn cho một nhà cụ thể.
- Có nên khuyên khách dán tem ngày thay lõi lên thân máy không, và thợ của bên mình có làm việc đó sẵn hay không — nếu có thì câu hỏi khó nhất của mã bệnh này tự biến mất.
**Máy lọc nước** — `devices/water_purifier.md`

- Chu kỳ thay từng cấp lõi theo chất lượng nước máy từng khu vực, vì con số ba tới sáu tháng hiện đang là khoảng rất rộng.
- Loại lõi phổ biến nhất thợ nên mang sẵn khi đi bảo dưỡng, để khách không phải chờ thêm một lượt.

## Vòi nước — 30 mục

**Rò rỉ chân vòi, mối nối** — `faults/FAUCET_BASE_LEAK.md`

- Ống mềm cấp còn dùng được bao lâu, và có nên thay cả hai cùng lúc không.
- Gioăng thân vòi có còn kín không, khi vòi đã được siết chặt.
- Mặt bồn rửa có chịu được lực siết không, nhất là với bồn đá nhân tạo hoặc bồn sứ mỏng.
- Van chặn có còn đóng kín được không.
- Phần gỗ đáy tủ đã hỏng tới đâu, và cần xử lý thế nào.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hỏng lõi vòi trộn** — `faults/FAUCET_CARTRIDGE.md`

- Lõi vòi thay thế có đúng loại và đúng cỡ cho model đó không. Không có chuẩn chung giữa các hãng.
- Model đó có bán lõi rời không, hay chỉ bán cả vòi.
- Đai ốc giữ lõi có tháo ra được không, nếu đã rỉ chặt.
- Ngàm và ren trong thân vòi có còn tốt không.
- Nước nóng đã tới vòi chưa, nếu triệu chứng là không chỉnh được nhiệt độ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Mòn gioăng, rò rỉ vòi nước** — `faults/FAUCET_DRIP.md`

- Bệ tựa bên trong vòi còn nguyên không, với vòi hai tay. Đây là câu hỏi quyết định giữa thay gioăng và thay vòi.
- Lõi vòi thay thế có đúng loại và đúng cỡ không.
- Ren ở thân vòi có còn tốt không.
- Van chặn có còn đóng kín được không.
- Nước có nhiều cặn tới mức nên lắp lọc không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Nghẹt đầu lọc, áp lực nước yếu** — `faults/FAUCET_LOW_FLOW.md`

- Đầu lọc thay thế có đúng ren và đúng cỡ không, nếu lưới đã rách hoặc ren đã trờn.
- Lõi vòi có bị cặn không, nếu nước mạnh ở ống mềm mà yếu ở vòi.
- Áp lực nước tại vị trí đó có đủ không, nếu nghi nhánh áp lực.
- Nước có nhiều cặn tới mức nên lắp lọc tổng không, và loại lọc nào phù hợp.
- Bể chứa có cần vệ sinh không, nếu đầu lọc bị bít lại rất nhanh sau khi rửa.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Vòi nước** — `devices/faucet.md`

- Lõi vòi thay thế có đúng loại và đúng cỡ cho model đó không. Không có chuẩn chung giữa các hãng.
- Bệ tựa bên trong vòi hai tay còn nguyên không, vì bệ mòn thì thay gioăng cũng không kín.
- Ren ở thân vòi có còn tốt không.
- Ống mềm cấp còn dùng được bao lâu.
- Van chặn có còn đóng kín được không, nếu van đã kẹt hoặc đã cũ.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## Bồn rửa — 30 mục

**Nghẹt đường thoát bồn rửa** — `faults/SINK_CLOGGED.md`

- Nghẹt nằm ở bẫy nước hay ở đường ống phía sau.
- Bẫy nước thuộc loại nào, và có tháo được bằng tay không.
- Ống thoát sau bẫy có đủ độ dốc không, và có bị võng không, nếu nghẹt lặp lại.
- Gioăng và đai ốc của bẫy có còn dùng được không sau khi tháo ra lắp vào.
- Đường ống chung có vấn đề không, nếu nhiều chỗ cùng chậm.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rò rỉ ống thoát dưới bồn** — `faults/SINK_TRAP_LEAK.md`

- Bẫy nước thuộc loại nào, và phụ kiện thay thế có tương thích không.
- Giỏ thoát có bị rỉ tới mức không ép kín được gioăng không.
- Chỗ ống cắm vào ống thoát trên tường có còn kín không.
- Phần gỗ đáy tủ đã hỏng tới đâu, và cần xử lý thế nào.
- Ống xả của máy lọc nước hoặc máy rửa bát nối vào bẫy có kín không, nếu nhà có.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Rỉ sét, mục giỏ thoát** — `faults/SINK_DRAIN_CORRODED.md`

- Giỏ thoát thay thế có đúng đường kính lỗ chậu và đủ chiều dài ren không, nhất là với chậu đá nhân tạo hoặc chậu sứ dày.
- Giỏ có cần cửa phụ để nối ống xả của máy lọc nước hoặc máy rửa bát không.
- Đai ốc cũ có tháo ra được không, nếu đã rỉ chặt.
- Mặt chậu quanh lỗ thoát có còn phẳng để ép gioăng không, nếu đã bị ăn mòn.
- Bẫy nước có nên thay cùng lúc không.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Hôi cống, khô bẫy nước** — `faults/SINK_SMELL.md`

- Bồn rửa có bẫy nước không, và lắp đúng chiều không. Câu hỏi quyết định của mã này.
- Ống thông hơi của hệ thoát có thông không, nếu có nhánh bẫy bị hút cạn.
- Mùi đến từ bồn rửa hay từ khoang tủ ẩm do rò.
- Đoạn ống sau bẫy có bám cặn dày không, nếu mùi vẫn còn sau khi đã rửa bẫy.
- Sự cố thuộc phần của căn hộ hay phần chung của toà nhà, với chung cư.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
**Bồn rửa** — `devices/sink.md`

- Bẫy nước thuộc loại nào, và phụ kiện thay thế có tương thích không.
- Có bẫy nước hay không, và nếu có thì lắp đúng chiều không.
- Giỏ thoát thay thế có đúng đường kính lỗ thoát của chậu không.
- Nghẹt nằm ở bẫy hay ở đường ống phía sau.
- Phần gỗ đáy tủ đã hỏng tới đâu, nếu đã rò lâu.
- Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.

## chung — 5 mục

**Khu vực FixHome nhận sửa** — `system/khu-vuc-phuc-vu.md`

- Có phụ phí đi xa cho đơn ở quận xa trung tâm hay không, và ngưỡng tính từ đâu. Khách ở Bình Tân hay Thủ Đức hay hỏi câu này ngay sau khi biết là có phục vụ.
- Khung giờ nhận đơn thực tế của đội thợ, vì khách hỏi khu vực thường hỏi luôn giờ, và hiện tài liệu này không trả lời được vế sau.
- Có nhận đơn gấp trong ngày ở mọi quận không, hay chỉ ở một số quận có đủ thợ trực. Đây là thứ quyết định câu trả lời cho các ca khẩn như rò gas hay kẹt ngoài cửa, và hiện đang bỏ trống.
**Những thiết bị nhìn ảnh không phân biệt được, và cách hỏi lại** — `system/thiet-bi-de-nhin-nham.md`

- Máy rửa bát âm tủ có mặt nạ gỗ trùng với cánh tủ bếp thì trong ảnh gần như không thấy được gì — có dấu hiệu nào khách nhìn thấy được để tách nó khỏi máy giặt không, ngoài việc hỏi máy dùng làm gì.
- Bếp hồng ngoại nên xếp cùng nhóm với bếp từ hay tách riêng, vì mặt bếp nhìn giống nhau nhưng bếp hồng ngoại vẫn nóng mặt kính sau khi tắt và đó là một cảnh báo an toàn khác.

