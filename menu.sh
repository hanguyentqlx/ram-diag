#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1
available_mb() { awk '/^MemAvailable:/{print int($2 / 1024)}' /proc/meminfo; }
while true; do
  echo; echo '=== RAM-DIAG USB | CLI ==='
  echo '1. Nhan dang RAM / tra ma offline'
  echo '2. Thong ke co so du lieu'
  echo '3. Memtester (2 vong, RAM dang trong)'
  echo '4. Stressapptest (15 phut)'
  echo '5. Huong dan Memtest86+'
  echo '0. Thoat'
  read -r -p 'Chon: ' opt || exit 0
  case "$opt" in
    1) python3 "$ROOT/ramdiag.py" scan ;;
    2) python3 "$ROOT/ramdiag.py" stats ;;
    3|4)
      [[ $EUID -eq 0 ]] || { echo 'Hay chay: sudo bash menu.sh'; continue; }
      tool=memtester
      [[ $opt == 4 ]] && tool=stressapptest
      command -v "$tool" >/dev/null || { echo "Thieu $tool trong Linux Live."; continue; }
      avail=$(available_mb); size=$((avail / 2))
      (( size > 4096 )) && size=4096
      (( size >= 256 )) || { echo 'Khong du bo nho trong'; continue; }
      if [[ $opt == 3 ]]; then
        echo "Se test $size MiB x 2 vong."; read -r -p 'Bat dau? [y/N] ' yes
        [[ $yes =~ ^[yY]$ ]] && memtester "${size}M" 2
      else
        echo "Stress $size MiB trong 900 giay. Cam sac, dam bao tan nhiet."
        read -r -p 'Bat dau? [y/N] ' yes
        [[ $yes =~ ^[yY]$ ]] && stressapptest -M "$size" -s 900 -W
      fi ;;
    5) echo 'Memtest86+ phai boot rieng tu Ventoy/SystemRescue. Chay >=4 passes. CLI Linux khong test duoc toan bo RAM.' ;;
    0) exit 0 ;;
    *) echo 'Khong hop le.' ;;
  esac
done
