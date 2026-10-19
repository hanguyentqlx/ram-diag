# RAM-DIAG USB — CLI

Bản CLI tối giản, **không tạo HTML**, không cần ghi log lên SSD. Mã RAM được đối chiếu offline bằng `catalog/*.csv`. Chưa phải danh mục đầy đủ mọi Kingston/OEM; thiếu mã không có nghĩa là hàng giả. Phần quét SMBIOS không kiểm tra lỗi RAM.

## Ubuntu (thử ngay)

```bash
cd ~/ram-diag
git pull
sudo python3 ramdiag.py scan
sudo bash menu.sh
```

## Tạo USB boot để chạy trên nhiều PC x86

Chuẩn bị USB >= 8 GB, backup dữ liệu USB. **Ventoy sẽ xóa dữ liệu USB khi cài lần đầu.** Kiểm tra chính xác bằng `lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS` trước khi cài Ventoy, không được chọn nhầm SSD `/dev/nvme0n1`.

1. Tải Ventoy tại https://www.ventoy.net/en/download.html và SystemRescue ISO tại https://www.system-rescue.org/Download/.
2. Trên Ubuntu, giải nén Ventoy và chạy `sudo ./VentoyGUI.x86_64`. Chọn **đúng ổ USB**, cài Ventoy. Có thể cần chỉnh Secure Boot/UEFI để boot được trên một số máy.
3. Chép ISO SystemRescue vào phân vùng dữ liệu Ventoy. **Chép cả thư mục `ram-diag` từ GitHub vào cùng phân vùng**. Không cần cài phần mềm vào SSD máy được kiểm tra.
4. Boot máy cần kiểm tra từ USB (Dell thường nhấn F12) > chọn SystemRescue.
5. Trong Terminal SystemRescue, tìm nơi USB đang được mount: `lsblk -f`; nếu chưa mount: `mkdir -p /mnt/ventoy && mount /dev/disk/by-label/Ventoy /mnt/ventoy`. Nếu Ventoy được gắn nhãn khác, dùng đúng đường dẫn phân vùng được `lsblk -f` trả về. Nếu hệ thống đã tự mount, dùng đường dẫn đó thay cho `/mnt/ventoy`.
6. Chạy `cd /mnt/ventoy/ram-diag && bash menu.sh` (Terminal của SystemRescue thường đã là root); nếu không phải root, dùng `sudo bash menu.sh`.

Để kiểm tra gần toàn bộ RAM thay vì một phần RAM còn trống, khởi động Memtest86+ từ menu boot SystemRescue hoặc thêm ISO Memtest86+ riêng vào Ventoy. **Không thể chạy Memtest86+ đầy đủ bên trong phiên Linux Live đang dùng RAM**.

Chức năng menu:
- 1: Nhận dạng RAM, đối chiếu mã offline, chỉ in trên terminal.
- 2: Thống kê các mã offline.
- 3: Chạy memtester trên tối đa 1/2 RAM khả dụng, 2 vòng, xác nhận trước.
- 4: Stressapptest 15 phút, xác nhận trước.
- 5: Hướng dẫn boot Memtest86+.

**Không có công cụ phần mềm nào đảm bảo xác thực 100% RAM Kingston hay RAM OEM chính hãng.** Cần so thông tin SPD với nhãn vật lý và hỏi nhà sản xuất nếu nghi giả.

`ramdiag.py scan` không ghi file và không ghi dữ liệu lên SSD. `memtester` và `stressapptest` kiểm tra trong RAM và tạo tải CPU/RAM.
