# RAM-DIAG — USB RAM test CLI

RAM-DIAG hien menu chu, chon 1–6, khong tao HTML. Nhận dạng RAM/Kingston OEM bằng cơ sở dữ liệu offline khởi đầu, kiểm tra với memtester/stressapptest. **Chưa có toàn bộ mã RAM của mọi hãng. SPD/SMBIOS không thể xác thực 100% hàng chính hãng.**

## Boot USB: tự hiện menu, không gõ lệnh

ISO gốc SystemRescue 13.02 cần tải từ https://www.system-rescue.org/Download/ vào `~/ramdiag-usb/systemrescue-13.02-amd64.iso`. USB Ventoy phải đã cài và có phân vùng dữ liệu `Ventoy`.

Trên Ubuntu máy chuẩn bị USB:

```bash
cd ~/ram-diag
git pull --ff-only
sudo apt update
sudo apt install -y xorriso squashfs-tools curl python3
bash build-auto-iso.sh
```

Tạo file `~/ramdiag-usb/RAM-DIAG-AUTO.iso` bằng công cụ sysrescue-customize chính thức. Script này **không format USB** và không sửa ISO gốc. Cần vài GB ổ trống để xây dựng ISO.

Sau đó (chỉ khi USB Ventoy đã được nhận diện đúng và có nhãn `Ventoy`):

```bash
findmnt -S /dev/disk/by-label/Ventoy || true
sudo mkdir -p /mnt/ramdiag-usb
# Chỉ mount nếu USB chưa được mount ở nơi khác:
sudo mount /dev/disk/by-label/Ventoy /mnt/ramdiag-usb
sudo cp ~/ramdiag-usb/RAM-DIAG-AUTO.iso /mnt/ramdiag-usb/
sync
```

Nếu USB đã tự mount dưới /media, dùng đường dẫn đó thay vì mount lại. Chọn `RAM-DIAG-AUTO.iso` tại Ventoy. Menu RAM-DIAG được tự chạy trên tty1; các file chương trình nằm bên trong ISO nên không cần mount USB hay gõ lệnh. Nếu tty1 không hiện, có thể chuyển bằng Alt+F1. Hãy thử boot trên Dell trước khi dựa vào USB trên máy khác.

Bài test gần toàn bộ RAM cần boot Memtest86+ riêng vì Linux giữ một phần RAM. Có thể thêm ảnh ISO Memtest86+ vào Ventoy.

## Dùng trên Ubuntu bình thường

```bash
cd ~/ram-diag && git pull --ff-only
sudo bash menu.sh
```

## Mức độ đánh giá

- Listed code: chỉ xác định mã có trong catalog, không chứng minh chính hãng.
- Unknown code: mã chưa có trong database, không có nghĩa RAM giả.
- Memtester/Stressapptest: test vùng RAM Linux cấp phát, không thay thế Memtest86+ boot độc lập.
- Công cụ không ghi đè dữ liệu trên SSD/HDD.


## DDR4 Kingston / Samsung / Micron / Crucial catalog

Danh muc nho `catalog/linuxhw_ddr4_top250.csv` da duoc tich hop vao `ramdiag.py` (45 ma phan biet tu bang RAM pho bien cua linuxhw/DMI). Day la du lieu may tinh cong dong, KHONG phai catalog hang chinh thuc.

De mo rong bang tat ca bao cao cong khai trong linuxhw/DMI tren Ubuntu co Internet (co the can nhieu GB va mat thoi gian):

```bash
cd ~/ram-diag
git pull --ff-only
git clone --depth 1 https://github.com/linuxhw/DMI.git ~/linuxhw-DMI
python3 catalog_tools/import_ddr4_dmi.py --root ~/linuxhw-DMI --out catalog/observed_ddr4_full.csv
python3 ramdiag.py stats
```

Sau khi nhap xong, ban phai **tao lai RAM-DIAG-AUTO.iso** va chep ISO moi len USB Ventoy, vi co so du lieu duoc nhung vao ISO khi build. Do not overwrite active ISO in place while booted from it.

Gioi han: DMI reports khong bao phu tat ca ma OEM; ma OEM nhu ACR... chi duoc gan hang Kingston neu bao cao co ten hang, khong duoc suy dien qua tien to. Khong doc/luu serial tung may trong catalog, khong xac nhan chinh hang.
