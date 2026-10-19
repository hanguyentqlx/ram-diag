#!/usr/bin/env bash
# Build standalone SystemRescue ISO with RAM-DIAG menu on tty1.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-$HOME/ramdiag-usb/systemrescue-13.02-amd64.iso}"
OUTPUT="${2:-$HOME/ramdiag-usb/RAM-DIAG-AUTO.iso}"
[[ -f "$ISO" ]] || { echo "Khong tim thay ISO: $ISO"; exit 1; }
[[ ! -e "$OUTPUT" ]] || { echo "Output da ton tai, khong ghi de: $OUTPUT"; exit 1; }
for tool in xorriso mksquashfs curl python3; do
    command -v "$tool" >/dev/null || { echo "Thieu $tool. Cai: sudo apt install xorriso squashfs-tools curl python3"; exit 1; }
done
[[ -f "$ROOT/menu.sh" && -f "$ROOT/ramdiag.py" && -d "$ROOT/catalog" ]] || { echo "Thieu file RAM-DIAG."; exit 1; }
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/recipe/iso_add/sysrescue.d" "$WORK/recipe/build_into_srm/usr/local/share/ram-diag" "$WORK/recipe/build_into_srm/usr/local/bin"
cat > "$WORK/recipe/iso_add/sysrescue.d/900-ramdiag.yaml" <<'EOF'
---
autoterminal:
  tty1: "/bin/bash /usr/local/bin/ramdiag-launch"
EOF
cp "$ROOT/menu.sh" "$ROOT/ramdiag.py" "$WORK/recipe/build_into_srm/usr/local/share/ram-diag/"
cp -a "$ROOT/catalog" "$WORK/recipe/build_into_srm/usr/local/share/ram-diag/"
cat > "$WORK/recipe/build_into_srm/usr/local/bin/ramdiag-launch" <<'EOF'
#!/usr/bin/env bash
set -u
export TERM="${TERM:-linux}"
cd /usr/local/share/ram-diag || exit 1
while true; do
    /bin/bash ./menu.sh
    printf '\nMenu da dong. Nhan Enter de khoi dong lai menu...'
    read -r _ || sleep 2
done
EOF
chmod 755 "$WORK/recipe/build_into_srm/usr/local/bin/ramdiag-launch"
# SRM is embedded inside ISO; no USB mount required after boot.
curl -fL --retry 3 'https://gitlab.com/systemrescue/systemrescue-sources/-/raw/main/airootfs/usr/share/sysrescue/bin/sysrescue-customize?inline=false' -o "$WORK/sysrescue-customize"
head -n 1 "$WORK/sysrescue-customize" | grep -q '^#!' || { echo "Tai customize khong dung dinh dang"; exit 1; }
chmod +x "$WORK/sysrescue-customize"
echo "Building: $OUTPUT"
bash "$WORK/sysrescue-customize" --auto --source="$ISO" --dest="$OUTPUT" --recipe-dir="$WORK/recipe"
echo "Xong: $OUTPUT"
sha256sum "$OUTPUT"
echo "Chep file RAM-DIAG-AUTO.iso len USB Ventoy, boot ISO do."
