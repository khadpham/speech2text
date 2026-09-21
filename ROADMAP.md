# Roadmap chất lượng và nâng cấp

Điểm số từ 1 đến 5; `5` là quan trọng nhất, khả thi nhất, thực dụng nhất hoặc dễ
triển khai nhất. Thứ tự ưu tiên không chỉ dựa trên độ dễ: lỗi có nguy cơ mất dữ
liệu hoặc sai hành vi được làm trước tính năng mới.

## A. Lỗi cần sửa

| Thứ tự | Hạng mục | Quan trọng | Khả thi | Thực dụng | Dễ triển khai | Trạng thái |
|---:|---|---:|---:|---:|---:|---|
| 1 | Làm cho Dịch/Thêm dấu câu của F8 thực sự hoạt động | 5 | 5 | 5 | 5 | Hoàn thành: unit test, clean build và startup smoke test |
| 2 | Không ghi nguyên văn lời nói và prompt vào log mặc định | 5 | 5 | 5 | 5 | Chưa làm |
| 3 | Giới hạn thời lượng/kích thước ghi âm và báo khi không có tiếng nói | 5 | 5 | 5 | 4 | Chưa làm |
| 4 | Dán đúng cửa sổ bắt đầu và bảo toàn đầy đủ clipboard | 5 | 4 | 5 | 2 | Chưa làm |
| 5 | Phân loại lỗi API/mic/hotkey, hướng dẫn người dùng cách khắc phục | 4 | 5 | 5 | 4 | Chưa làm |
| 6 | Chờ nhả tổ hợp F9 trước khi gửi Ctrl+C lấy selection | 4 | 5 | 5 | 4 | Chưa làm |
| 7 | Loại bỏ race condition UI, timer và shutdown | 4 | 4 | 4 | 3 | Chưa làm |
| 8 | Health check và fallback cho TTS/SAPI | 3 | 4 | 3 | 3 | Chưa làm |

## B. Cải tiến được xếp hạng

| Hạng | Cải tiến | Quan trọng | Khả thi | Thực dụng | Dễ triển khai | Lý do |
|---:|---|---:|---:|---:|---:|---|
| 1 | Chọn microphone, nút thử mic và tự fallback sample rate | 5 | 5 | 5 | 3 | Giải quyết phần lớn lỗi “bấm mà không hoạt động” trên máy Windows khác nhau |
| 2 | VAD tin cậy hơn, hiệu chỉnh noise floor và pre-roll | 5 | 4 | 5 | 3 | Giảm cắt mất âm đầu/cuối và ghi mãi trong phòng ồn |
| 3 | Structured Outputs và xác nhận trước hành động AI | 5 | 5 | 5 | 3 | Tăng độ ổn định và giảm prompt injection/hành động ngoài ý muốn |
| 4 | Preview, Copy, Paste, Undo và Cancel request | 4 | 5 | 5 | 3 | Người dùng kiểm soát kết quả và tránh dán nhầm |
| 5 | Đọc quota thật từ response headers, tính tối thiểu 10 giây STT | 4 | 4 | 4 | 3 | Dashboard phản ánh giới hạn/chi phí thực tế hơn |
| 6 | Tách module và state machine có kiểm thử tích hợp | 5 | 5 | 5 | 2 | Nền tảng để phát triển lâu dài, nhưng cần thực hiện theo từng lát nhỏ |
| 7 | Windows CI, installer, metadata phiên bản và ký số | 4 | 4 | 5 | 2 | Cần thiết trước khi phát hành công khai |
| 8 | Chunking cho bản ghi dài và phục hồi request lỗi | 4 | 4 | 4 | 2 | Hữu ích cho ghi dài, nhưng không quan trọng bằng độ ổn định cơ bản |
| 9 | Profile theo ứng dụng và từ điển theo ngữ cảnh | 3 | 4 | 4 | 3 | Tăng độ “thông minh” sau khi luồng cốt lõi đã ổn định |
| 10 | Auto-update có chữ ký và rollback | 3 | 4 | 4 | 2 | Có giá trị sau khi đã có installer và quy trình ký phát hành |

## C. Cổng kiểm định bắt buộc cho mỗi hạng mục

Một hạng mục chỉ được đánh dấu hoàn thành khi:

1. Có test tái hiện lỗi cũ hoặc kiểm tra hành vi mới.
2. Toàn bộ unit test và `pip check` đạt.
3. Build sạch bằng PyInstaller thành công.
4. Smoke test trên EXE đóng gói xác nhận startup, hotkey và đường đi liên quan.
5. README/manual được cập nhật nếu hành vi người dùng thay đổi.
6. Không có API key, cấu hình cá nhân, log, quota hoặc từ điển cá nhân trong Git.
7. Mỗi thay đổi có commit riêng để có thể rollback.
