#!/usr/bin/env python3
"""RAM-DIAG SPD reader: read-only comparison of decode-dimms with SMBIOS."""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

from ramdiag import parse_dmi, normalize, usable_serial


def fields_from_block(block):
    """decode-dimms aligns key and value with two or more spaces."""
    fields = {}
    for line in block.splitlines():
        match = re.match(r"^\s*(\S.*?)\s{2,}(\S.*?)\s*$", line)
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def parse_spd(text):
    """Read one record for each SPD EEPROM that decode-dimms decoded."""
    result = []
    for block in re.split(r"(?=^Decoding EEPROM:\s*)", text, flags=re.M):
        found = re.search(r"^Decoding EEPROM:\s*(\S+)", block, re.M)
        if not found:
            continue
        f = fields_from_block(block)
        serial = f.get("Assembly Serial Number", "").strip()
        if serial.lower().startswith("0x"):
            serial = serial[2:]
        crc = [(key, value) for key, value in f.items()
               if key.startswith("EEPROM CRC of bytes")]
        def status(value):
            value = value.strip().upper()
            if value.startswith("OK"):
                return "OK"
            if any(word in value for word in ("FAIL", "BAD", "ERROR", "INVALID")):
                return "FAIL"
            return "UNKNOWN"
        result.append({
            "path": found.group(1),
            "serial": serial,
            "part": f.get("Part Number", ""),
            "module_manufacturer": f.get("Module Manufacturer", ""),
            "dram_manufacturer": f.get("DRAM Manufacturer", ""),
            "date": f.get("Manufacturing Date", ""),
            "size": f.get("Size", ""),
            "memory_type": f.get("Fundamental Memory type", ""),
            "module_type": f.get("Module Type", ""),
            "speed": f.get("Maximum module speed", ""),
            "ranks": f.get("Ranks", ""),
            "crc": [(k, status(v)) for k, v in crc],
        })
    return result


def run_readonly(command):
    if not shutil.which(command[0]):
        return None, f"Missing tool: {command[0]}"
    try:
        p = subprocess.run(command, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if p.returncode:
        return None, (p.stderr or p.stdout).strip()[:400]
    return p.stdout, None


def show(spds, modules, spd_error=None):
    print("\n========== RAM-DIAG | SPD EEPROM ==========")
    print(f"SMBIOS: {len(modules)} thanh | SPD doc duoc: {len(spds)} EEPROM")
    if spd_error:
        print(f"SPD KHONG DOC DUOC: {spd_error}")
    seen_slots = set()
    for index, spd in enumerate(spds, 1):
        serial = usable_serial(spd["serial"])
        candidates = [m for m in modules if serial and
                      normalize(usable_serial(m.get("serial_number"))) == normalize(serial)]
        if len(candidates) == 1:
            slot = candidates[0].get("slot", "?")
            seen_slots.add(slot)
            match_info = f"DA DOI CHIEU SMBIOS: {slot} (theo serial)"
            bios_part = candidates[0].get("part", "")
            if bios_part and spd["part"] and normalize(bios_part) != normalize(spd["part"]):
                match_info += " | ! MODEL KHAC NHAU"
        elif len(candidates) > 1:
            match_info = "KHONG XAC DINH: serial BIOS trung lap"
        else:
            match_info = "CHUA GAN DUOC KHE: khong suy doan theo 'bank'"
        print(f"\n[{index}] EEPROM: {spd['path']}")
        print(f"    {match_info}")
        print(f"    Module brand: {spd['module_manufacturer'] or 'UNKNOWN'}")
        print(f"    DRAM chip brand: {spd['dram_manufacturer'] or 'UNKNOWN'}")
        print(f"    Part number: {spd['part'] or 'UNKNOWN'}")
        print(f"    Serial SPD: {spd['serial'] or 'UNKNOWN'}")
        print(f"    Date: {spd['date'] or 'UNKNOWN'}")
        print(f"    Type: {spd['memory_type'] or 'UNKNOWN'} / {spd['module_type'] or '?'}")
        print(f"    Capacity: {spd['size'] or 'UNKNOWN'} | Max speed: {spd['speed'] or 'UNKNOWN'}")
        print(f"    Ranks: {spd['ranks'] or 'UNKNOWN'}")
        if spd["crc"]:
            print("    CRC: " + " | ".join(f"{label}: {state}" for label, state in spd["crc"]))
            if any(state == "FAIL" for _, state in spd["crc"]):
                print("    ! SPD CRC FAIL: can kiem tra lai tren may/khe khac.")
        else:
            print("    CRC: KHONG CO DU LIEU (khong phai PASS)")
    for mod in modules:
        if mod["slot"] not in seen_slots:
            print(f"\n! {mod['slot']}: BIOS nhan RAM {mod['part'] or '?'} "
                  f"(serial {mod.get('serial_number') or '?'}), nhung CHUA DOI CHIEU DUOC SPD.")
    if len(spds) < len(modules):
        print("\nLuu y: Thieu SPD khong co nghia RAM gia/hong. Firmware/driver co the chan doc.")
    print("CRC OK khong chung minh RAM chinh hang. Cong cu chi doc, khong ghi EEPROM.")


def main():
    parser = argparse.ArgumentParser(description="Read and compare SPD/SMBIOS from terminal")
    parser.add_argument("--spd-fixture", help="Offline test data from decode-dimms")
    parser.add_argument("--dmi-fixture", help="Offline test data from dmidecode -t 17")
    args = parser.parse_args()
    if args.dmi_fixture:
        dmi_text = pathlib.Path(args.dmi_fixture).read_text(encoding="utf-8")
    else:
        dmi_text, err = run_readonly(["dmidecode", "-t", "17"])
        if err:
            print("SMBIOS: " + err, file=sys.stderr)
            dmi_text = ""
    if args.spd_fixture:
        spd_text = pathlib.Path(args.spd_fixture).read_text(encoding="utf-8")
        spd_error = None
    else:
        spd_text, spd_error = run_readonly(["decode-dimms"])
        if spd_error:
            spd_text = ""
    modules = parse_dmi(dmi_text)
    spds = parse_spd(spd_text)
    show(spds, modules, spd_error)
    return 0 if spds else 2


if __name__ == "__main__":
    sys.exit(main())
