# RAM-DIAG v0.3 — Offline RAM Diagnostic

Bộ công cụ kiểm tra thông tin RAM trên Ubuntu/SystemRescue (Linux Live), tra mã RAM Kingston/OEM và các hãng khác bằng dữ liệu offline, kiểm tra RAM bằng memtester/stressapptest và lưu báo cáo HTML/JSON.

**Lưu ý:** Đây là v0.3 starter, chưa phải USB boot hoàn chỉnh và **chưa có toàn bộ mã RAM**. Tra được mã RAM không chứng minh hàng chính hãng; thiếu mã trong DB không có nghĩa là RAM giả.

## Tải và chạy trên Ubuntu 24.04

```bash
sudo apt update
sudo apt install -y git python3 dmidecode i2c-tools memtester stressapptest xz-utils
git clone https://github.com/hanguyentqlx/ram-diag.git
cd ram-diag
bash extract-source.sh
python3 -m unittest discover -s tests -v
python3 ramdiag.py stats
sudo bash menu.sh
```

`extract-source.sh` giải nén mã nguồn v0.3 từ `release/ramdiag-v0.3.tar.xz` vào thư mục repo. Script kiểm tra SHA-256 trước khi giải nén. Đừng chạy updater với sudo.

Để mở rộng danh mục offline khi có Internet:

```bash
bash update-catalog.sh
python3 ramdiag.py stats
```

Để làm USB: dùng Ventoy chứa SystemRescue ISO cùng thư mục RAM-DIAG đã giải nén. Xem `README-VI.md` sau khi giải nén. **Cài Ventoy sẽ xóa dữ liệu trên USB được chọn.**

Nguồn mã tham khảo: bộ RAM-DIAG v0.3 đã chạy 11/11 unit tests trên Python 3.
