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

Nếu thiếu API key, Dashboard sẽ tự mở. Nhập key tại **CÀI ĐẶT → API Groq** rồi bấm **LƯU TẤT CẢ THIẾT LẬP**.

Ứng dụng lưu log chẩn đoán tại `%LOCALAPPDATA%\SmartVoiceAI\smart_voice_ai.log`.

## Kiểm thử và đóng gói

```powershell
python -m unittest discover -s tests -v
pyinstaller --clean --noconfirm Smart_Voice_AI_Assistant.spec
```

Không phân phối `app_settings.json`, file quota, virtual environment hoặc output build cũ. Nếu một API key từng được commit hay nhúng vào `.exe`, hãy thu hồi key đó trong Groq Console và tạo key mới.
