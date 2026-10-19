#!/usr/bin/env python3
"""RAM-DIAG: terminal-only RAM inventory; no HTML, no disk testing."""
import argparse
import csv
import pathlib
import re
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent
CATALOG_FILES = [
    ("CURATED", BASE / "catalog" / "models.csv"),
    ("COMMUNITY", BASE / "catalog" / "observed_linuxhw.csv"),
    ("COMMUNITY", BASE / "catalog" / "observed_oem.csv"),
]

def normalize(value):
    return re.sub(r"\s+", "", str(value or "")).upper()

def number(value):
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group()) if m else None

def size_gb(value):
    m = re.search(r"^\s*(\d+(?:\.\d+)?)\s*(GB|MB|TB)\b", str(value or ""), re.I)
    if not m:
        return None
    qty, unit = float(m.group(1)), m.group(2).upper()
    return qty / 1024 if unit == "MB" else qty * 1024 if unit == "TB" else qty

def parse_dmi(text):
    result = []
    for chunk in re.split(r"(?=^Handle\s+0x[\da-fA-F]+,\s+DMI type 17,)", text, flags=re.M):
        if not re.search(r"^Handle\s+0x[\da-fA-F]+,\s+DMI type 17,", chunk, flags=re.M):
            continue
        fields = dict((k.strip(), v.strip()) for k, v in re.findall(
            r"^\s{2,}([A-Za-z][A-Za-z0-9 /()_-]+):\s*(.*?)\s*$", chunk, flags=re.M))
        cap = size_gb(fields.get("Size"))
        if cap is None:
            continue
        result.append({
            "slot": fields.get("Locator", "?"),
            "part": fields.get("Part Number", "").strip(),
            "manufacturer": fields.get("Manufacturer", "?"),
            "capacity_gb": cap,
            "type": fields.get("Type", "?"),
            "form_factor": fields.get("Form Factor", "?"),
            "speed": number(fields.get("Speed")),
            "configured_speed": number(fields.get("Configured Memory Speed")),
            "ranks": number(fields.get("Rank")),
        })
    return result

def load_catalog():
    db = {}
    counts = {"CURATED": 0, "COMMUNITY": 0}
    for tier, path in CATALOG_FILES:
        if not path.is_file():
            continue
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                part = normalize(row.get("part_number"))
                if not part or part in db:
                    continue
                db[part] = (tier, row)
                counts[tier] += 1
    return db, counts

def guess_brand(mod):
    vendor = mod["manufacturer"].upper()
    if vendor.startswith("80CE"):
        return "Samsung"
    names = ("Kingston", "Samsung", "SK hynix", "Hynix", "Crucial", "Micron",
             "Corsair", "G.Skill", "ADATA", "XPG", "Transcend", "TeamGroup",
             "Patriot", "PNY", "Nanya", "Apacer", "Ramaxel", "Kingbank")
    for name in names:
        if name.upper() in vendor:
            return name
    return "Unknown"

def assess(mod, db):
    hit = db.get(normalize(mod["part"]))
    if hit is None:
        return "CHUA CO TRONG DB", "Chua xac minh hang that; khong co ma khong nghia la RAM gia", []
    tier, row = hit
    disagreements = []
    expected = number(row.get("capacity_gb"))
    if expected is not None and abs(expected - mod["capacity_gb"]) > 0.01:
        disagreements.append(f"Dung luong: {mod['capacity_gb']:g} vs catalog {expected:g} GB")
    mem_type = normalize(row.get("memory_type"))
    if mem_type and normalize(mod["type"]) not in (mem_type, "UNKNOWN"):
        disagreements.append("Loai RAM khac catalog")
    if tier == "CURATED":
        rated = number(row.get("rated_mt_s"))
        if rated and mod["speed"] and abs(rated - mod["speed"]) > rated * 0.02:
            disagreements.append(f"Toc do danh dinh {mod['speed']:g} vs catalog {rated:g} MT/s")
    # Community data are observations, not manufacturer certifications.
    label = "CURATED CODE" if tier == "CURATED" else "COMMUNITY OBSERVED"
    if disagreements:
        label = "CAN KIEM TRA THEM"
    return label, f"Nguon: {tier}; CHUA XAC MINH CHINH HANG", disagreements

def scan(fixture=None):
    if fixture:
        raw = pathlib.Path(fixture).read_text(encoding="utf-8")
    else:
        if not shutil.which("dmidecode"):
            print("Thieu dmidecode. Ubuntu: sudo apt install dmidecode", file=sys.stderr)
            return 1
        p = subprocess.run(["dmidecode", "-t", "17"], text=True, capture_output=True)
        if p.returncode:
            print("Khong doc duoc SMBIOS. Hay chay: sudo python3 ramdiag.py scan", file=sys.stderr)
            print(p.stderr.strip(), file=sys.stderr)
            return 1
        raw = p.stdout
    modules = parse_dmi(raw)
    db, counts = load_catalog()
    print("\n========== RAM-DIAG | NHAN DANG RAM ==========")
    print(f"So thanh: {len(modules)} | Tong: {sum(x['capacity_gb'] for x in modules):g} GB")
    print(f"Database offline: {len(db)} ma ({counts['CURATED']} curated, {counts['COMMUNITY']} observed)\n")
    if not modules:
        print("Khong thay DIMM tren SMBIOS. May co the chan thong tin RAM.")
        return 2
    for i, m in enumerate(modules, 1):
        tag, detail, issues = assess(m, db)
        hit = db.get(normalize(m["part"]))
        brand = hit[1].get("brand") if hit else guess_brand(m)
        print(f"[{i}] Khe {m['slot']} | {brand} | {m['capacity_gb']:g} GB | {m['type']}")
        print(f"    Model: {m['part'] or '?'}")
        print(f"    SPD/BIOS: {m['manufacturer']} | rated {m['speed'] or '?'} | active {m['configured_speed'] or '?'} MT/s")
        print(f"    Danh muc: {tag} | {detail}")
        for issue in issues:
            print(f"    ! BAT THUONG: {issue}")
    print("\nXAC THUC: CHUA THE KET LUAN RAM CHINH HANG QUA SMBIOS.")
    print("SUC KHOE: CHUA TEST O DAY. Chon Memtester/Memtest86+ tren menu de kiem tra loi.")
    print("Khong tao file HTML/JSON va khong ghi vao SSD.")
    return 0

def main():
    ap = argparse.ArgumentParser(description="RAM-DIAG CLI-only")
    ap.add_argument("action", nargs="?", default="scan", choices=("scan", "stats", "catalog"))
    ap.add_argument("--fixture", help="DMI text fixture for development/testing")
    args = ap.parse_args()
    if args.action == "scan":
        return scan(args.fixture)
    db, counts = load_catalog()
    print(f"Total offline part numbers: {len(db)}")
    print(f"Curated: {counts['CURATED']} | Community: {counts['COMMUNITY']}")
    if args.action == "catalog":
        for part, (tier, data) in sorted(db.items()):
            print(f"[{tier}] {data.get('brand','?'):12} {part:30} {data.get('capacity_gb','?')} GB")
    print("Unlisted != counterfeit. Listed != authenticated.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
