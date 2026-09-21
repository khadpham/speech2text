# Hướng dẫn sử dụng Smart Voice AI Assistant

## 1. Khởi động và API key

1. Chạy `Smart_Voice_AI_Assistant.exe`.
2. Mở biểu tượng ứng dụng trong khay hệ thống và chọn **Bảng điều khiển**.
3. Tại **CÀI ĐẶT → API Groq**, nhập API key rồi chọn **LƯU TẤT CẢ THIẾT LẬP**.

API key được mã hóa bằng Windows DPAPI và lưu tại
`%LOCALAPPDATA%\SmartVoiceAI\app_settings.json`. Bản phát hành không được chứa
`app_settings.json`, `dictionary.json` hoặc file quota của người phát triển.

## 2. Chuyển giọng nói thành văn bản bằng F8

1. Đặt con trỏ tại nơi cần nhập văn bản.
2. Nhấn `Ctrl+Alt+F8` một lần.
3. Chờ tiếng báo bắt đầu rồi nói.
4. Ngừng nói khoảng 2 giây để ứng dụng tự kết thúc, hoặc nhấn `Esc`/nhấn lại
   `Ctrl+Alt+F8`.
5. Chờ trạng thái **ĐANG XỬ LÝ** kết thúc. Văn bản sẽ được dán tại vị trí con trỏ.

### Các chế độ F8

- **Chép lời nguyên bản:** tắt Dịch và tắt AI thêm dấu câu. Chế độ này nhanh nhất.
- **Dịch:** chọn `Việt → Anh` hoặc `Anh → Việt` trong Dashboard. Kết quả dịch sẽ
  được dán thay cho bản chép lời.
- **Thêm dấu câu:** bật `AI Tự sửa lỗi & Thêm dấu câu`. AI chỉ được yêu cầu thêm
  viết hoa và dấu câu, không thay đổi ý nghĩa.
- Khi bật đồng thời Dịch và Thêm dấu câu, Dịch được ưu tiên.

## 3. Trợ lý AI bằng F9

- Không chọn văn bản: nhấn `Ctrl+Alt+F9` và nói yêu cầu trực tiếp.
- Có chọn văn bản: bôi đen đoạn cần xử lý, nhấn `Ctrl+Alt+F9`, rồi nói yêu cầu
  như “viết lại trang trọng hơn” hoặc “tóm tắt đoạn này”.
- Có thể dừng bằng `Esc` hoặc nhấn lại hotkey.

## 4. Chế độ ghi âm

- **Rảnh tay:** nhấn một lần để bắt đầu; VAD tự dừng khi im lặng.
- **Nhấn giữ:** giữ hotkey trong khi nói và thả để kết thúc.
- Có thể đổi hai hotkey trong Dashboard. Hai tổ hợp phải khác nhau.

## 5. Xử lý sự cố nhanh

- **Không có phản ứng khi bấm hotkey:** kiểm tra app còn trong system tray và
  hotkey có bị ứng dụng khác sử dụng hay không.
- **Ứng dụng yêu cầu API key:** mở Dashboard, nhập key và lưu lại.
- **Không nhận mic:** kiểm tra microphone mặc định và quyền Microphone trong
  Windows Settings.
- **Kết quả chưa được dán:** không đổi cửa sổ khi ứng dụng đang xử lý. Cơ chế
  khóa đúng cửa sổ nhận kết quả nằm trong lộ trình sửa lỗi tiếp theo.
- **Cần chẩn đoán:** xem `%LOCALAPPDATA%\SmartVoiceAI\smart_voice_ai.log`. Không
  chia sẻ file log công khai trước khi kiểm tra dữ liệu riêng tư.

## 6. Thoát ứng dụng

Nhấp phải biểu tượng trong system tray và chọn **Thoát**. Đóng Dashboard không
đồng nghĩa với thoát ứng dụng.
