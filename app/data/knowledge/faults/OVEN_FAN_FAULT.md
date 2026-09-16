---
doc_id: KB_FAULT_OVEN_FAN_FAULT
doc_type: fault
device_type: oven
fault_code: OVEN_FAN_FAULT
name_vi: Hỏng quạt đối lưu
urgency: LOW
confusable_with: [OVEN_HEATING_ELEMENT, OVEN_THERMOSTAT, OVEN_DOOR_GLASS]
price_policy: Không ghi giá trong tài liệu này. Giá lấy từ bảng giá của hệ thống.
last_reviewed: 2026-09-17
needs_technician_review:
  - Quạt nào đang hỏng, quạt đối lưu hay quạt làm mát vỏ
---

# Hỏng quạt đối lưu

## Hai cái quạt khác nhau, và khách gọi chung là quạt

Điều đầu tiên phải tách, vì hai cái quạt này làm hai việc khác nhau và hỏng thì hậu quả khác
hẳn.

**Quạt đối lưu.** Nằm ở thành sau bên trong khoang lò, thường có một vòng thanh nhiệt quanh
nó.

Việc của nó: thổi khí nóng vòng quanh khoang để nhiệt phân bố đều.

Hỏng thì món chín không đều và nướng lâu hơn. Phiền, nhưng lò vẫn dùng được.

**Quạt làm mát vỏ.** Nằm ở phần sau của lò, ngoài khoang nướng.

Việc của nó: thổi khí qua vách lò để vỏ, cửa, và các linh kiện điện bên trong không quá nóng.

Hỏng thì vỏ lò nóng bất thường, và quan trọng hơn, **các linh kiện điện bên trong chạy ở
nhiệt độ cao hơn thiết kế**.

Nghĩa là quạt làm mát hỏng thì nó âm thầm phá những thứ khác, trong khi quạt đối lưu hỏng thì
chỉ làm bánh chín không đều.

Câu hỏi tách: **"tiếng quạt có phát ra từ trong lò khi đang nướng, hay từ phía sau lò và vẫn
chạy sau khi đã tắt lò ạ?"**

Quạt còn chạy sau khi tắt lò là quạt làm mát. Đó là thiết kế, không phải lỗi.

## Nhánh không phải hỏng: lò vốn không có quạt

Phải loại trước tiên, vì nó chiếm nhiều ca và vì nó không sửa được.

Không phải lò nướng nào cũng có quạt đối lưu. Lò để bàn cỡ nhỏ và lò giá rẻ thường không có.

Lò không có quạt thì **vốn dĩ nướng không đều**. Khí nóng bốc lên tự nhiên, nên phần trên
khoang nóng hơn phần dưới, và phần gần thanh nhiệt nóng hơn phần xa.

Đây là đặc tính, không phải bệnh.

Cách nhận ra: nhìn thành sau bên trong khoang lò. Lò có quạt thì có một nắp tròn hoặc một
lưới che quạt ở đó.

Hoặc nhìn núm chỉnh chế độ: lò có quạt thường có một biểu tượng hình quạt trong các chế độ.

Nếu lò vốn không có quạt, cách xử lý không phải là sửa mà là dùng khác đi:

**Xoay khay một trăm tám mươi độ vào giữa thời gian nướng.**

**Đặt khay ở tầng giữa**, trừ khi công thức nói khác.

**Nướng một khay một lần**, đừng hai khay cùng lúc.

**Dùng công thức viết cho lò không quạt**, hoặc tăng thời gian và giảm nhiệt so với công thức
của lò có quạt.

Bốn việc đó giải quyết phần lớn than phiền, và chúng không tốn gì.

## Câu hỏi vàng: nghe và nhìn

**"Khi lò đang nướng, anh chị có nghe tiếng quạt chạy trong lò không ạ, và nhìn qua cửa kính
có thấy cánh quạt ở thành sau quay không?"**

Quạt đối lưu nằm sau một tấm chắn có lỗ, nên có khi không nhìn thấy cánh trực tiếp. Nhưng
tiếng thì nghe được.

Ba kết quả:

**Nghe tiếng quạt và tiếng đều:** quạt còn chạy. Không phải mã này.

**Không nghe tiếng gì từ trong khoang:** quạt đối lưu không chạy, hoặc lò không có quạt.

**Nghe tiếng nhưng tiếng lạ: rít, lạo xạo, hoặc va đập:** quạt còn chạy nhưng có vấn đề.

Câu hỏi bổ sung để tách nhánh cuối: **"tiếng đó đều hay có nhịp va đập ạ?"**

Rít đều: bạc trục khô.

Va đập theo nhịp: cánh quạt chạm vào cái gì đó, hoặc cánh cong.

Lạo xạo: bạc mòn.

## Chín không đều: đọc hướng để tách nhánh

Hướng của sự không đều là dữ liệu chẩn đoán tốt, và khách mô tả được nếu hỏi đúng.

**Không đều theo chiều trên dưới:** cháy mặt sống ruột, hoặc cháy đáy nhợt mặt.

Đây là nhánh thanh nhiệt, không phải quạt. Chuyển sang OVEN_HEATING_ELEMENT.

**Không đều theo chiều trước sau:** phía trong cùng chín hơn, phía gần cửa sống hơn.

Nghiêng về quạt, hoặc về cửa không kín.

**Không đều theo chiều trái phải:** một bên chín hơn bên kia.

Nghiêng mạnh về quạt: nó thổi lệch, hoặc nó không chạy và khí nóng phân bố tự nhiên theo
hình dạng khoang.

**Không đều giữa hai khay khi nướng hai tầng:** khay trên chín nhiều hơn.

Với lò có quạt, đây là dấu hiệu quạt yếu. Với lò không quạt, đây là bình thường và không nên
nướng hai khay cùng lúc.

Câu hỏi đáng hỏi: **"chỗ nào chín và chỗ nào chưa, theo hướng nào ạ?"**

Nghe như câu hỏi về nấu ăn, nhưng nó là câu hỏi chẩn đoán và nó tách được ba mã khác nhau.

## Vì sao quạt đối lưu hỏng

Bốn nguyên nhân, và chúng phản ánh môi trường mà nó làm việc.

**Bạc trục khô.** Quạt đối lưu làm việc trong khoang nóng, ở nhiệt độ cao hơn nhiều so với
mọi quạt khác trong nhà.

Mỡ bôi trơn trong bạc bay hơi và biến chất nhanh hơn. Sau đủ nhiều giờ, bạc khô và quạt kêu
rít, rồi nặng dần, rồi kẹt.

**Mỡ và muội bám lên cánh.** Hơi mỡ trong lò bám lên cánh quạt và cháy thành muội.

Lớp muội làm cánh mất cân bằng, nên quạt rung và kêu. Nó cũng làm cánh nặng hơn, nên mô tơ
làm việc nặng hơn.

Đây là nguyên nhân phổ biến nhất ở bếp Việt.

**Cánh cong hoặc chạm.** Do va đập khi vệ sinh, hoặc do khay đặt quá sát thành sau.

**Cuộn dây mô tơ hỏng.** Nhiệt là nguyên nhân chính, và nó là kết cục của ba nguyên nhân
trên nếu để lâu.

Nguyên nhân thứ hai đáng nói riêng vì nó phòng được hoàn toàn: vệ sinh khoang lò và vệ sinh
cánh quạt định kỳ thì quạt bền hơn nhiều.

## Nhánh quạt làm mát vỏ

Nhánh quan trọng hơn về hậu quả, dù nó ít được khách để ý.

Quạt làm mát chạy khi lò hoạt động, và nó **tiếp tục chạy một lúc sau khi tắt lò** để hạ
nhiệt.

Điều đó là bình thường, và nó đáng nói vì nhiều khách tưởng lò hỏng khi nghe tiếng quạt sau
khi đã tắt.

Có một lời khuyên đi kèm và nó thực tế: **đừng rút điện lò ngay sau khi tắt**. Để quạt chạy
hết chu kỳ làm nguội.

Rút điện ngay nghĩa là nhiệt còn lại trong lò không được đẩy ra, và nó ngấm vào các linh
kiện bên trong.

Dấu hiệu quạt làm mát hỏng:

**Vỏ lò và cửa nóng hơn hẳn bình thường.**

**Không nghe tiếng quạt ở phía sau khi lò chạy.**

**Quạt không chạy thêm sau khi tắt lò**, trong khi trước đây có.

**Vùng quanh lò nóng lên**, và với lò âm tủ thì mặt tủ bếp quanh đó nóng.

**Mùi nhựa nóng.**

Hậu quả: bo điều khiển, rơ le, dây dẫn, và các tiếp điểm bên trong đều chạy ở nhiệt độ cao
hơn thiết kế.

Chúng không hỏng ngay, nhưng chúng già nhanh hơn nhiều.

Vì vậy quạt làm mát hỏng đáng xử lý sớm hơn quạt đối lưu hỏng, dù triệu chứng thì ít phiền
hơn.

## Nhánh lò âm tủ và khe thoáng

Đáng tách vì nó phổ biến ở căn hộ mới và vì nó không phải hỏng quạt.

Lò âm tủ được lắp vào một hốc trong tủ bếp. Nhà sản xuất quy định khoảng hở tối thiểu quanh
lò để quạt làm mát có đường thoát khí.

Nếu hốc quá khít, hoặc nếu phía sau bị bịt kín, thì quạt vẫn chạy nhưng khí nóng quẩn trong
hốc.

Kết quả giống hệt quạt hỏng: vỏ nóng, linh kiện chạy nóng, và tủ bếp quanh đó nóng.

Dấu hiệu tách: **quạt vẫn nghe chạy bình thường nhưng vỏ vẫn nóng**.

Cách kiểm: xem có khe thoáng ở đâu không, thường là ở chân tủ hoặc ở phía sau.

Cách xử lý: mở khe thoáng, hoặc khoét lỗ thông ở đáy hốc hoặc ở phía sau.

Đây là việc của thợ mộc chứ không phải thợ điện, và nói rõ điều đó thì khách không gọi nhầm
người.

Nhánh này cũng áp dụng cho lò để bàn kê sát tường hoặc nhét vào góc kệ, và với lò để bàn thì
cách xử lý chỉ là kéo nó ra.

## Nhánh tiếng ồn

Khách hay báo mã này bằng tiếng chứ không bằng kết quả nướng.

**Rít đều theo vòng quay:** bạc trục khô. Giai đoạn sớm.

**Lạo xạo hoặc rào rào:** bạc mòn. Giai đoạn sau.

**Va đập theo nhịp:** cánh quạt chạm vào tấm chắn, hoặc cánh cong, hoặc có vật lạ trong đó.

Nhánh cuối đáng kiểm ngay vì nó có thể chỉ là một mẩu thức ăn hoặc một miếng giấy bạc bị hút
vào.

**Tiếng to hẳn lên so với trước:** thường là muội bám làm cánh mất cân bằng.

**Tiếng ù to bất thường:** mô tơ làm việc nặng, có thể do cánh nặng hoặc do bạc kẹt một phần.

Có một tiếng không phải bệnh và đáng trấn an: **tiếng quạt làm mát chạy sau khi tắt lò**. Nó
thường to hơn lúc lò đang chạy vì lúc đó không có tiếng khác át đi.

Câu hỏi tách: tiếng đó có ngừng khi lò nguội hẳn không. Có thì là quạt làm mát và nó bình
thường.

## Việc khách tự làm được

**Nghe và nhìn khi lò đang chạy**, để xác định quạt nào và tình trạng ra sao.

**Kiểm xem lò có quạt đối lưu không.** Nhìn thành sau khoang lò, hoặc nhìn biểu tượng trên
núm chế độ.

**Vệ sinh khoang lò và tấm chắn quạt**, khi lò nguội hẳn và đã rút điện.

Lau muội bám trên tấm chắn và trên phần cánh nhìn thấy được, nhẹ tay.

**Kiểm có vật lạ kẹt trong quạt không**, với nhánh tiếng va đập.

**Kéo lò ra khỏi tường**, với lò để bàn.

**Kiểm khe thoáng của hốc tủ**, với lò âm tủ.

**Xoay khay giữa chừng và đặt khay tầng giữa**, với lò không có quạt.

**Đừng rút điện ngay sau khi tắt lò**, để quạt làm mát chạy hết chu kỳ.

Việc khách không nên tự làm: tháo tấm chắn quạt; tháo cánh quạt; thay mô tơ quạt.

Lý do: tấm chắn thường bắt bằng vít chịu nhiệt và tháo ra thì phải lắp lại đúng, và phía sau
nó là vòng thanh nhiệt mang điện áp lưới.

## Sửa hay thay

Mã ưu tiên thấp nhất của cụm lò nướng, và phần lớn ca rẻ.

**Vệ sinh cánh và tấm chắn:** miễn phí, và nó giải quyết nhánh muội bám.

**Lấy vật lạ ra:** rẻ nhất trong nhóm cần thợ.

**Tra dầu hoặc thay bạc quạt:** rẻ về linh kiện, có công.

**Thay mô tơ quạt đối lưu:** chi tiết rời và thay được. Với lò cỡ vừa trở lên thì không đắt
so với giá lò.

**Thay quạt làm mát:** tương tự.

**Mở khe thoáng cho hốc tủ:** việc của thợ mộc, và nó không thuộc phần sửa lò.

Điểm cần nói với lò âm tủ: **công tháo lò ra khỏi hốc là phần lớn chi phí**.

Vì vậy nếu đã tháo ra thì đáng kiểm luôn các thứ khác: thanh nhiệt, rơ le, gioăng cửa, và
quạt còn lại.

Nghiêng về thay lò khi lò đã rẻ và đã cũ, hoặc khi cả hai quạt cùng hỏng cùng với thứ khác.

Có một điều đáng nói khi khách hỏi có đáng sửa quạt đối lưu không: **lò vẫn dùng được không
có quạt**, chỉ là nướng không đều và lâu hơn.

Với lò cũ và với khách nướng ít, sống chung cộng với việc xoay khay là lựa chọn hợp lý, và
không nên đẩy họ khỏi nó.

Nhưng với quạt làm mát thì khác: nó ảnh hưởng tới các linh kiện khác, và nó đáng sửa.

## Khách nói thế nào

"quạt lò không chạy", "lò nướng không đều", "một bên chín một bên sống", "lò nướng kêu to",
"quạt trong lò kêu rít", "vỏ lò nóng quá", "quạt vẫn chạy sau khi tắt lò", "nướng hai khay
thì khay dưới không chín", "lò nướng lâu hơn".

Không dấu: quat lo khong chay, lo nuong khong deu, mot ben chin mot ben song, lo nuong keu
to, vo lo nong qua, quat van chay sau khi tat lo.

Cách nói khác: "lò nhà em nướng chỗ chín chỗ sống", "bánh một bên cháy một bên trắng", "lò
kêu ầm ầm", "sờ vỏ lò nóng rát".

Câu "quạt vẫn chạy sau khi tắt lò" cần trấn an ngay, vì đó là quạt làm mát và nó bình thường.

Câu "một bên chín một bên sống" cần hỏi thêm về hướng, vì trên dưới thì là thanh nhiệt còn
trái phải thì là quạt.

Câu "vỏ lò nóng quá" thuộc nhánh quạt làm mát, và nó đáng xử lý hơn khách nghĩ.

## Đọc ảnh

Ảnh thành sau bên trong khoang lò. Cho biết lò có quạt đối lưu không, và cho biết tấm chắn
có bám muội không.

Ảnh khoang lò nhìn chung. Mức độ bẩn là bối cảnh của nhánh muội bám.

Ảnh món ăn sau khi nướng. **Có giá trị thật với mã này**: chỗ chín và chỗ sống cho biết hướng
không đều, và hướng thì tách được ba mã.

Ảnh khay đặt trong lò. Cho biết tầng đặt và cho biết khay có quá to chặn luồng khí không.

Ảnh núm chọn chế độ. Có biểu tượng quạt thì lò có chế độ đối lưu.

Ảnh mặt sau lò và khe thoáng, cùng khoảng cách tới tường.

Ảnh hốc tủ chứa lò, với lò âm tủ. Cho biết có khe thoáng không.

Video có tiếng khi lò đang chạy. Có giá trị hơn ảnh với nhánh tiếng ồn, vì các loại tiếng
khó tách bằng lời.

## Lẫn với bệnh nào

**OVEN_HEATING_ELEMENT.** Cặp quan trọng nhất phải tách, và tách bằng hướng không đều.

Trên dưới thì là thanh nhiệt. Trái phải hoặc trước sau thì là quạt.

Nhầm hướng này làm khách thay quạt cho một cái lò chỉ cần thay thanh nhiệt, hoặc ngược lại.

**OVEN_THERMOSTAT.** Cả hai làm lò nướng lâu hơn. Tách bằng việc món có chín đều không: rơ
le sai thì chín đều nhưng sai nhiệt; quạt hỏng thì chín không đều.

**OVEN_DOOR_GLASS.** Cửa không kín làm phần gần cửa nguội, và nó giống hệt quạt hỏng ở nhánh
không đều theo chiều trước sau.

Tách bằng phép thử tờ giấy ở cửa.

Và với nhánh vỏ nóng, cả hai mã đều có thể: mất một lớp kính, hay quạt làm mát không chạy.

Có hai nhánh không phải bệnh và cả hai đáng loại trước: **lò vốn không có quạt**, và **quạt
làm mát chạy sau khi tắt lò**.

Cộng lại chúng chiếm nhiều ca, và không cái nào cần sửa gì.

## Phòng cho lần sau

**Vệ sinh khoang lò và tấm chắn quạt định kỳ**, nhất là sau khi nướng đồ nhiều mỡ.

Muội trên cánh quạt là nguyên nhân số một, và nó phòng được hoàn toàn.

**Đậy hoặc che món nhiều mỡ khi nướng.**

**Đừng đặt khay sát thành sau**, vì nó chặn luồng khí từ quạt và có khi chạm vào tấm chắn.

**Đừng để giấy bạc rời trong lò khi có quạt chạy.** Nó bị hút vào và kẹt trong cánh.

**Kéo lò ra khỏi tường**, với lò để bàn.

**Đảm bảo hốc tủ có khe thoáng đúng yêu cầu**, với lò âm tủ. Nói với thợ lắp tủ ngay từ đầu.

**Đừng rút điện ngay sau khi tắt lò.** Để quạt làm mát chạy hết chu kỳ.

**Xử lý sớm khi quạt bắt đầu kêu.** Ở giai đoạn rít thì có thể chỉ cần vệ sinh hoặc tra dầu;
để tới lúc kẹt thì mô tơ đã chịu tải nặng lâu.

## Kịch bản mẫu

Khách nhắn "lò nướng không đều". Hỏi hướng không đều trước, vì nó tách ba mã.

Khách nhắn "một bên chín một bên sống". Nhánh quạt. Hỏi lò có quạt không và có nghe tiếng
quạt chạy không.

Khách nhắn "cháy mặt mà sống ruột". Không phải mã này. Chuyển sang nhánh thanh nhiệt.

Khách nhắn "lò em không có quạt thì sao". Nói rõ đó là đặc tính chứ không phải bệnh, và
hướng dẫn bốn việc: xoay khay, đặt tầng giữa, nướng một khay, dùng công thức phù hợp.

Khách nhắn "quạt trong lò kêu rít". Nhánh bạc khô. Gợi ý vệ sinh trước, và nói rõ xử lý sớm
thì rẻ hơn.

Khách nhắn "vỏ lò nóng rát". Nhánh quạt làm mát. Hỏi có nghe tiếng quạt ở phía sau không, và
hỏi lò có kê sát tường hay nhét trong hốc kín không.

Khách nhắn "quạt vẫn chạy sau khi tắt lò". Trấn an: đó là quạt làm mát và nó bình thường. Và
nhắc đừng rút điện ngay.

Khách nhắn "nướng hai khay thì khay dưới không chín". Hỏi lò có quạt không. Nếu không thì
nướng một khay một lần.

## Nền tri thức của tài liệu này

Toàn bộ nội dung được viết lại bằng lời của dự án, không sao chép nguyên văn từ nguồn
nào.

Phân biệt quạt đối lưu trong khoang nướng với quạt làm mát vỏ đặt ngoài khoang, cùng vai trò
khác nhau của chúng: tài liệu kỹ thuật của các hãng lò nướng có mặt tại Việt Nam, đối chiếu
nội dung mô đun thực hành thiết bị gia dụng trong chương trình đào tạo nghề.

Nguyên lý đối lưu cưỡng bức giúp nhiệt phân bố đều, và đặc tính phân tầng nhiệt tự nhiên ở lò
không có quạt: kiến thức truyền nhiệt phổ thông.

Khác biệt về nhiệt độ và thời gian nướng giữa lò có quạt và lò không quạt: hướng dẫn sử dụng
của nhà sản xuất.

Chế độ quạt làm mát chạy thêm sau khi tắt lò, và khuyến cáo không ngắt nguồn ngay: hướng dẫn
sử dụng của nhà sản xuất.

Yêu cầu về khoảng hở lắp đặt cho lò âm tủ để bảo đảm thoát khí: hướng dẫn lắp đặt của nhà sản
xuất.

Cơ chế khô dầu ở bạc trục quạt làm việc trong môi trường nhiệt độ cao, và cơ chế muội bám làm
cánh mất cân bằng: kiến thức cơ khí và truyền nhiệt phổ thông.

Yêu cầu an toàn với thiết bị nấu nướng dùng trong gia đình: tham chiếu TCVN 5699-1 về an toàn
thiết bị điện gia dụng. Cần cập nhật khi hệ thống chạy thật.

## Chỗ cần thợ xác nhận

Quạt nào đang hỏng, quạt đối lưu hay quạt làm mát vỏ.

Lò có quạt đối lưu không, nếu khách không chắc.

Mô tơ quạt còn tốt không, hay chỉ là bạc khô và muội bám.

Hốc tủ có đủ khe thoáng theo yêu cầu lắp đặt không, với lò âm tủ.

Các linh kiện bên trong đã bị ảnh hưởng chưa, nếu quạt làm mát đã hỏng một thời gian.

Chi phí. Mọi con số tiền lấy từ bảng giá của hệ thống, không lấy từ tài liệu này.
