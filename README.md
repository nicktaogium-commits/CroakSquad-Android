# Croak Squad Android — bản nguồn thử nghiệm từ V17

**Đây chưa phải file APK và chưa phải bản Android hoàn thiện.** Dự án này là bản Kivy thử nghiệm dựa trên `Croak_Squad_V17_9_Levels_Unlock.zip` trong cuộc trò chuyện. Game Windows gốc **không bị thay đổi**.

## Đã chuyển
- Dữ liệu **9 map V17** ở `maps.py`, cùng khoảng trống, bậc, cưa, máy ép, gai, nền chuyển động và checkpoint.
- 6 ảnh nhân vật thực từ `assets/frog_0.png` ... `frog_5.png`.
- Camera, vật lý cơ bản, hồi sinh, mở khóa màn và lưu tiến trình.
- Điều khiển cảm ứng ngang: trái/phải, nhảy, hút/bắn; offline có nút đổi P1/P2 để thử hai nhân vật.
- TCP cổng 5056 theo thông điệp của `server.py` V17, có tạo phòng, vào phòng, bắt đầu phòng, trạng thái vị trí, hút/bắn.
- `server_pc.py` là bản sao server V17; **chạy trên PC**, không cần đưa server vào APK.

## Giới hạn cần sửa/kiểm thử
- Chưa chạy thực tế trên Kivy/Android, chỉ kiểm tra cú pháp và sinh 9 map. Chưa xác nhận build APK thành công.
- Hiển thị là bản dựng lại tối giản, **chưa có toàn bộ hoạt ảnh đẹp** và hiệu ứng của Windows.
- Offline trên điện thoại điều khiển **luân phiên** 2 nhân vật bằng nút đổi P1/P2, không phải hai người cùng chạm cùng lúc.
- Đồng bộ online và va chạm chưa được kiểm thử trên nhiều thiết bị, server V17 tin vào dữ liệu vị trí từ client.
- Hiện máy khách online có thể bị khác nhịp các bẫy vì thời gian chuyển động chưa đồng bộ theo server. Cần sửa trước khi công bố trò chơi.
- Quá trình kiểm thử gameplay hoàn chỉnh, điều khiển đa điểm, font tiếng Việt và kích thước màn hình chưa thực hiện.

## Chạy thử trên PC (không dùng Pygame)
```
python -m pip install kivy
python main.py
```

## Build Android (trên Ubuntu/WSL2)
Dùng WSL2 Ubuntu, công cụ JDK/Android build theo tài liệu Buildozer, tạo virtualenv rồi `pip install buildozer cython`. Đặt project ở thư mục Linux (ví dụ `~/CroakSquad_Android_Source`) và chạy:
```
buildozer -v android debug
```
APK nếu build thành công sẽ nằm trong `bin/`. Yêu cầu Java SDK, Android SDK/NDK và dependencies có thể thay đổi; xem https://buildozer.readthedocs.io/en/latest/installation.html

## Online chung PC + Android
Trên PC chạy `python server_pc.py`. PC Windows chạy V17 client với IP 127.0.0.1, điện thoại kết nối bằng IP PC có thể truy cập (nếu chung Wi-Fi dùng IP LAN; nếu khác mạng cần server có địa chỉ công khai hoặc VPN hỗ trợ điện thoại). Điện thoại không kết nối được đến 127.0.0.1 của PC.

## Cấu trúc
- `main.py`: ứng dụng Android Kivy
- `maps.py`: dữ liệu V17 và va chạm độc lập Pygame
- `server_pc.py`: server V17 cho PC
- `assets/`: sprite gốc
- `buildozer.spec`: cấu hình build thử APK
