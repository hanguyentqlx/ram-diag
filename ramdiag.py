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
    ("COMMUNITY", BASE / "catalog" / "linuxhw_ddr4_top250.csv"),
    ("COMMUNITY", BASE / "catalog" / "observed_ddr4_full.csv"),
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
    """Read DMI Type 17 records line-by-line with relaxed whitespace."""
    modules = []
    fields = None

    def finish():
        if fields is None:
            return
        capacity = size_gb(fields.get("Size"))
        if capacity is None:
            return
        modules.append({
            "slot": fields.get("Locator", "?"),
            "part": fields.get("Part Number", "").strip(),
            "manufacturer": fields.get("Manufacturer", "?"),
            "manufacturer_id": fields.get("Module Manufacturer ID", ""),
            "serial_number": fields.get("Serial Number", ""),
            "module_product_id": fields.get("Module Product ID", ""),
            "capacity_gb": capacity,
            "type": fields.get("Type", "?"),
            "form_factor": fields.get("Form Factor", "?"),
            "speed": number(fields.get("Speed")),
            "configured_speed": number(fields.get("Configured Memory Speed")),
            "ranks": number(fields.get("Rank")),
        })

    for line in text.splitlines():
        header = re.match(r"^\s*Handle\s+0x[0-9a-fA-F]+\s*,\s*DMI\s+type\s+(\d+)\b",
                          line, re.I)
        if header:
            finish()
            fields = {} if header.group(1) == "17" else None
            continue
        if fields is None or not line[:1].isspace() or ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        fields[key.strip()] = value.strip()
    finish()
    return modules


PLACEHOLDER_SERIALS = {
    "", "NOT SPECIFIED", "UNKNOWN", "NONE", "N/A", "NOT PROVIDED",
    "TO BE FILLED BY O.E.M.", "00000000", "FFFFFFFF", "0000000000000000",
}

def usable_serial(serial):
    """Firmware-provided serial, not a manufacturer authentication token."""
    value = str(serial or "").strip()
    cleaned = normalize(value).replace("-", "")
    if cleaned in {normalize(v).replace("-", "") for v in PLACEHOLDER_SERIALS}:
        return ""
    if not re.fullmatch(r"[A-Z0-9-]{4,64}", value, re.I):
        return ""
    return value

def duplicate_serial_groups(modules):
    """Return duplicate serials for distinct reported slots; only a warning."""
    from collections import defaultdict
    by_serial = defaultdict(list)
    for module in modules:
        serial = usable_serial(module.get("serial_number"))
        if serial:
            by_serial[normalize(serial)].append(str(module.get("slot") or "?"))
    return {serial: slots for serial, slots in by_serial.items()
            if len(set(slots)) > 1}

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

# SMBIOS numeric vendor strings come from JEDEC module manufacturer IDs.
# Decode only observed, unambiguous identifiers. This is not proof of authenticity.
JEDEC_PREFIXES = {
    "0198": "Kingston",
    "80CE": "Samsung",
    "802C": "Micron",
    "80AD": "SK hynix",
    "04CB": "ADATA",
}
JEDEC_BANK_HEX = {
    (2, "98"): "Kingston",
    (1, "CE"): "Samsung",
    (1, "2C"): "Micron",
    (1, "AD"): "SK hynix",
    (5, "CB"): "ADATA",
}


def recognized_brand(mod):
    raw = mod["manufacturer"].strip()
    v = raw.upper().replace(" ", "")
    for code, brand in JEDEC_PREFIXES.items():
        if re.fullmatch(re.escape(code) + r"(?:0{0,12})", v):
            return brand, f"SMBIOS numeric ID {code}"
    m = re.search(r"Bank\s+(\d+)\s*,\s*Hex\s+0x([A-Fa-f0-9]{2})",
                  mod.get("manufacturer_id", ""), re.I)
    if m:
        brand = JEDEC_BANK_HEX.get((int(m[1]), m[2].upper()))
        if brand:
            return brand, "SMBIOS Module Manufacturer ID"
    aliases = (
        ("KINGSTON", "Kingston"), ("SAMSUNG", "Samsung"),
        ("SK HYNIX", "SK hynix"), ("SKHYNIX", "SK hynix"),
        ("HYNIX", "SK hynix"), ("MICRON", "Micron"),
        ("CRUCIAL", "Crucial"), ("CORSAIR", "Corsair"),
        ("G.SKILL", "G.Skill"), ("ADATA", "ADATA"),
        ("TEAMGROUP", "TeamGroup"), ("TRANSCEND", "Transcend"),
        ("NANYA", "Nanya"), ("APACER", "Apacer"), ("RAMAXEL", "Ramaxel"),
    )
    for key, brand in aliases:
        if key in raw.upper():
            return brand, "SMBIOS manufacturer text"
    return "", ""


def guess_brand(mod):
    """Backward-compatible brand guess; otherwise return Unknown."""
    return recognized_brand(mod)[0] or "Unknown"


def kingston_family(part):
    """Classify Kingston module identifiers conservatively; never authenticate by prefix."""
    p = normalize(part)
    if p.startswith("KVR"):
        return "ValueRAM (KVR)"
    if p.startswith("KSM"):
        return "Server Premier (KSM)"
    if p.startswith("KF"):
        return "FURY (KF)"
    if p.startswith(("KHX", "HX4")):
        return "HyperX legacy (KHX/HX4)"
    if p.startswith("CBD"):
        return "Design-In (CBD)"
    if p.startswith("ACR"):
        return "OEM-style ACR (Acer family; unverified)"
    if p.startswith("HP"):
        return "OEM-style HP (association unverified)"
    if p.startswith("MSI"):
        return "OEM-style MSI (association unverified)"
    if p.startswith(("LV", "RB", "SW", "TF")):
        return "OEM-style other (unverified)"
    if p.startswith("99"):
        return "99*-style module/reference ID"
    if p.startswith(("KTH", "KTD", "KTL", "KCP", "KTP")):
        return "System-specific style (unverified)"
    return "Other / needs review"

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
        print("Khong nhan duoc DIMM tu dmidecode. Hay kiem tra: sudo dmidecode -t 17")
        return 2
    for i, m in enumerate(modules, 1):
        tag, detail, issues = assess(m, db)
        hit = db.get(normalize(m["part"]))
        catalog_brand = str(hit[1].get("brand") or "").strip() if hit else ""
        reported_brand, evidence = recognized_brand(m)
        if reported_brand:
            brand = reported_brand
            source = evidence
        elif catalog_brand:
            brand = catalog_brand
            source = "offline catalog ONLY (not verified by BIOS/SPD)"
        else:
            brand = "UNKNOWN"
            source = "No supported manufacturer ID or matching catalog"
        print(f"[{i}] Khe {m['slot']} | {brand} | {m['capacity_gb']:g} GB | {m['type']}")
        print(f"    Nguon nhan dang hang: {source}")
        print(f"    Module Manufacturer ID (SMBIOS): {m['manufacturer_id'] or 'Khong co'}")
        print(f"    Serial Number (SMBIOS): {m['serial_number'] or 'Khong co'}")
        if not usable_serial(m['serial_number']):
            print("    ! Serial Number: thieu/placeholder, chua the doi chieu")
        print(f"    Module Product ID (SMBIOS): {m['module_product_id'] or 'Khong co'}")
        if reported_brand and catalog_brand and reported_brand.casefold() != catalog_brand.casefold():
            # Micron-made Crucial modules are a legitimate special case.
            if {reported_brand.casefold(), catalog_brand.casefold()} != {"micron", "crucial"}:
                print(f"    ! KHAI BAO MAU THUAN: SMBIOS={reported_brand}, catalog={catalog_brand}")
        print(f"    Model: {m['part'] or '?'}")
        if str(brand).strip().lower() == "kingston":
            print(f"    Kingston family: {kingston_family(m['part'])}")
        print(f"    SMBIOS: {m['manufacturer']} | rated {m['speed'] or '?'} | active {m['configured_speed'] or '?'} MT/s")
        print(f"    Danh muc: {tag} | {detail}")
        for issue in issues:
            print(f"    ! BAT THUONG: {issue}")
    duplicates = duplicate_serial_groups(modules)
    for serial, slots in duplicates.items():
        print(f"\n! SERIAL TRUNG NHAU: {serial} tai {', '.join(slots)}")
        print("  CAN KIEM TRA SPD/TEM. Serial trung lap khong chung minh RAM gia.")
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
    if args.action == "stats":
        from collections import Counter
        groups = Counter(kingston_family(part) for part, (_, row) in db.items()
                         if str(row.get("brand", "")).strip().lower() == "kingston")
        print("\nKingston groups (classification by code pattern, not product verification):")
        for group, count in groups.most_common():
            print(f"  {group:48} {count:5}")
    print("Unlisted != counterfeit. Listed != authenticated.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
