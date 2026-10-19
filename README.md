# RAM-DIAG — RAM inventory and verification starter

Bộ công cụ đọc RAM bằng SMBIOS trên Linux, tra cứu một số mã RAM offline và xuất báo cáo HTML/JSON. Repo hiện chứa **bản bootstrap tối giản**, không phải bộ v0.3 đầy đủ, không chứa toàn bộ mã Kingston/OEM và chưa phải USB tự boot.

## Chạy trên Ubuntu (máy hiện tại)

```bash
sudo apt update
sudo apt install -y git python3 dmidecode
git clone https://github.com/hanguyentqlx/ram-diag.git
cd ram-diag
sudo python3 ramdiag.py
```

Báo cáo lưu trong `reports/YYYYMMDD-HHMMSS/report.html` và `report.json`.

## Kiểm tra RAM bằng memtester (riêng biệt)

```bash
sudo apt install -y memtester
free -h
sudo memtester 1G 3
```

Thử 1 GiB chỉ kiểm tra vùng RAM được cấp phát. Muốn kiểm tra gần toàn bộ RAM, boot Memtest86+ từ USB (ví dụ Ventoy + SystemRescue/Memtest86+). Cài Ventoy lên USB sẽ xóa dữ liệu USB, không được chọn nhầm ổ SSD.

## Giới hạn nhận dạng

Ví dụ danh mục gồm Kingston OEM `ACR32D4S2S1ME-8`, Samsung `M471A5244CB0-CWE`. Tên hãng/mã từ BIOS chỉ là dữ liệu báo cáo; có thể bị sai/giả mạo. **Tra được mã KHÔNG phải chứng nhận hàng thật; không tra được mã KHÔNG phải chứng nhận hàng giả.** Cần thêm dữ liệu SPD, kiểm tra vật lý và hãng sản xuất để xác minh.

Repo này được khởi tạo để vượt qua lỗi tải file từ ChatGPT. Mã nguồn v0.3 đầy đủ vẫn chưa được đăng lên GitHub.
