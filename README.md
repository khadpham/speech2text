# Smart Voice AI Assistant (Windows)

Ứng dụng nhập liệu bằng giọng nói và trợ lý AI chạy ở Windows system tray.

## Cài đặt cho phát triển

Yêu cầu Windows 10/11 và Python 3.11+:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python smart_voice_typing.py
```

Mở biểu tượng ở system tray, chọn **Bảng điều khiển**, nhập Groq API key rồi lưu. Key được mã hóa bằng Windows DPAPI và lưu trong `%LOCALAPPDATA%\SmartVoiceAI\app_settings.json`; chỉ Windows user hiện tại giải mã được. Có thể dùng biến môi trường `GROQ_API_KEY` thay thế.

## Sử dụng

- `Ctrl+Alt+F8`: nhấn một lần, nghe tiếng báo rồi nói; app tự dừng sau khoảng 2 giây im lặng và dán bản chép lời vào cửa sổ hiện hành.
- `Ctrl+Alt+F9`: ghi yêu cầu AI; nếu đang bôi đen văn bản, nội dung đó được dùng làm đầu vào.
- `Esc` hoặc nhấn lại hotkey: dừng ghi ở chế độ rảnh tay.

Trong **Dashboard → CÀI ĐẶT**, F8 có ba cách xử lý:

- Để **Chế độ Dịch = Tắt** và tắt **AI Tự sửa lỗi & Thêm dấu câu**: chép lời nguyên bản, chỉ áp dụng Từ điển.
- Chọn **Việt → Anh** hoặc **Anh → Việt**: chép lời rồi dịch trước khi dán.
- Bật **AI Tự sửa lỗi & Thêm dấu câu**: giữ nguyên từ vựng và chuẩn hóa viết hoa/dấu câu trước khi dán.

Nếu bật cả Dịch và Thêm dấu câu, ứng dụng ưu tiên Dịch để tránh hai lần AI viết lại cùng một kết quả.

Ứng dụng nhập Unicode trực tiếp nên không thay đổi clipboard khi trả kết quả.
Nếu bạn chuyển sang cửa sổ khác trong lúc API đang xử lý, kết quả không bị dán
nhầm mà được giữ tại **Dashboard → Kết quả gần nhất**. Mỗi lần ghi mặc định tối
đa 300 giây và đoạn không có giọng nói sẽ không được gửi lên API.

Nếu thiếu API key, Dashboard sẽ tự mở. Nhập key tại **CÀI ĐẶT → API Groq** rồi bấm **LƯU TẤT CẢ THIẾT LẬP**.

Ứng dụng lưu log chẩn đoán tại `%LOCALAPPDATA%\SmartVoiceAI\smart_voice_ai.log`.

Hướng dẫn chi tiết: [docs/USER_MANUAL.md](docs/USER_MANUAL.md). Kế hoạch sửa lỗi và nâng cấp: [ROADMAP.md](ROADMAP.md).

## Kiểm thử và đóng gói

```powershell
python -m unittest discover -s tests -v
pyinstaller --clean --noconfirm Smart_Voice_AI_Assistant.spec
```

Không phân phối `app_settings.json`, file quota, virtual environment hoặc output build cũ. Nếu một API key từng được commit hay nhúng vào `.exe`, hãy thu hồi key đó trong Groq Console và tạo key mới.

Repository: <https://github.com/khadpham/speech2text>
