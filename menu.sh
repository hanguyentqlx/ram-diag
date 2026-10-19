#!/usr/bin/env bash
# RAM-DIAG text UI for bootable SystemRescue; no SSD/HDD test operations.
set -u
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

available_mb() {
    awk '/^MemAvailable:/{print int($2 / 1024)}' /proc/meminfo
}
test_size_mb() {
    local avail max
    avail=$(available_mb)
    # Use at most half available RAM and reserve extra 512MiB for Linux.
    max=$(( (avail - 512) / 2 ))
    (( max > 4096 )) && max=4096
    if (( max < 256 )); then
        echo "Khong du RAM trong de test an toan." >&2
        return 1
    fi
    printf '%d\n' "$max"
}
ask() {
    local answer
    read -r -p 'Bat dau kiem tra? [y/N] ' answer || return 1
    [[ "$answer" =~ ^[yY]$ ]]
}
run_memtester() {
    local loops="$1" size
    if (( EUID != 0 )); then
        echo 'Hay chay voi quyen root: sudo bash menu.sh'
        return
    fi
    if ! command -v memtester >/dev/null 2>&1; then
        echo 'Khong tim thay memtester.'
        return
    fi
    size=$(test_size_mb) || return
    echo "Memtester: ${size} MiB x ${loops} luot; khong test toan bo RAM."
    ask && memtester "${size}M" "$loops"
}
run_stress() {
    local size
    if (( EUID != 0 )); then
        echo 'Hay chay voi quyen root: sudo bash menu.sh'
        return
    fi
    if ! command -v stressapptest >/dev/null 2>&1; then
        echo 'Khong tim thay stressapptest.'
        return
    fi
    size=$(test_size_mb) || return
    echo "Stressapptest: ${size} MiB, 15 phut. Cam sac, giu may mat."
    ask && stressapptest -M "$size" -s 900 -W
}
show_spd() {
    if [[ -f "$ROOT/spdcheck.py" ]]; then
        python3 "$ROOT/spdcheck.py"
    else
        echo "Thieu spdcheck.py: hay cap nhat repo va build lai ISO."
    fi
}
while :; do
    clear 2>/dev/null || true
    printf '%s\n' '===================================='
    printf '%s\n' '           RAM-DIAG USB'
    printf '%s\n' '          RAM TEST TOOL'
    printf '%s\n' '===================================='
    printf '%s\n' '1. Nhan dang RAM va tra ma OEM offline'
    printf '%s\n' '2. Doc thong tin SPD/SMBIOS'
    printf '%s\n' '3. Test RAM nhanh (memtester x2)'
    printf '%s\n' '4. Test RAM dai (memtester x5)'
    printf '%s\n' '5. Stress test RAM 15 phut'
    printf '%s\n' '6. Thong ke catalog RAM offline'
    printf '%s\n' '0. Thoat menu'
    echo
    read -r -p 'Chon [0-6]: ' selection || exit 0
    echo
    case "$selection" in
        1) python3 "$ROOT/ramdiag.py" scan ;;
        2) show_spd ;;
        3) run_memtester 2 ;;
        4) run_memtester 5 ;;
        5) run_stress ;;
        6) python3 "$ROOT/ramdiag.py" stats ;;
        0) exit 0 ;;
        *) echo 'Hay chon so tu 0 den 6.' ;;
    esac
    echo
    read -r -p 'Nhan Enter de quay lai menu...' _ || exit 0
done
