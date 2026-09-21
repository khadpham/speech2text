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

Ứng dụng ghi Unicode trực tiếp và không dùng clipboard để dán kết quả. Nếu bạn
đổi sang cửa sổ khác trong lúc chờ API, app sẽ không dán nhầm: kết quả được giữ
trong **Dashboard → Kết quả gần nhất**, nơi bạn có thể chủ động sao chép.

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
- Khi đọc văn bản đang chọn, ứng dụng giữ và khôi phục nguyên clipboard OLE cũ,
  bao gồm các định dạng không phải text khi ứng dụng nguồn hỗ trợ.
- Có thể dừng bằng `Esc` hoặc nhấn lại hotkey.

## 4. Chế độ ghi âm

- **Rảnh tay:** nhấn một lần để bắt đầu; VAD tự dừng khi im lặng.
- **Nhấn giữ:** giữ hotkey trong khi nói và thả để kết thúc.
- Có thể đổi hai hotkey trong Dashboard. Hai tổ hợp phải khác nhau.
- Mỗi lần ghi mặc định tối đa 300 giây. Có thể đặt từ 10 đến 600 giây tại
  **CÀI ĐẶT → Tối đa ghi**. Khi không phát hiện giọng nói, app không gửi API.

## 5. Xử lý sự cố nhanh

- **Không có phản ứng khi bấm hotkey:** kiểm tra app còn trong system tray và
  hotkey có bị ứng dụng khác sử dụng hay không.
- **Ứng dụng yêu cầu API key:** mở Dashboard, nhập key và lưu lại.
- **Không nhận mic:** kiểm tra microphone mặc định và quyền Microphone trong
  Windows Settings.
- **API key không hợp lệ/không có quyền:** app sẽ nêu đúng nguyên nhân; mở
  Dashboard để cập nhật key hoặc chọn model được cấp quyền.
- **429/giới hạn Groq:** chờ theo hạn mức tài khoản rồi thử lại; app không coi
  đây là lỗi microphone.
- **TTS không hoạt động:** khi bật TTS và lưu cài đặt, app kiểm tra Windows SAPI.
  Nếu SAPI không dùng được, app thử pyttsx3; nếu cả hai lỗi thì TTS được tắt và
  phần nhập liệu/AI vẫn tiếp tục hoạt động.
- **Hotkey bị chiếm:** thông báo sẽ hiển thị Windows error và yêu cầu đóng ứng
  dụng dùng cùng tổ hợp hoặc đổi hotkey.
- **Kết quả chưa được dán:** không đổi cửa sổ khi ứng dụng đang xử lý. Cơ chế
  khóa đúng cửa sổ nhận kết quả nằm trong lộ trình sửa lỗi tiếp theo.
- **Cần chẩn đoán:** xem `%LOCALAPPDATA%\SmartVoiceAI\smart_voice_ai.log`. Log mặc
  định chỉ ghi trạng thái, độ dài và lỗi kỹ thuật, không ghi nguyên văn lời nói
  hoặc prompt. Dù vậy vẫn nên kiểm tra trước khi chia sẻ công khai.

## 6. Thoát ứng dụng

Nhấp phải biểu tượng trong system tray và chọn **Thoát**. Đóng Dashboard không
đồng nghĩa với thoát ứng dụng.
