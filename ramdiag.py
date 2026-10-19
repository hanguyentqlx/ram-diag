#!/usr/bin/env python3
"""RAM-DIAG bootstrap: inventory read-only SMBIOS data on Linux."""
import argparse
import datetime
import html
import json
import pathlib
import re
import shutil
import subprocess

KNOWN = {
    "ACR32D4S2S1ME-8": {"brand": "Kingston OEM", "size_gb": 8, "speed_mt": 3200, "source": "Community-observed OEM code"},
    "M471A5244CB0-CWE": {"brand": "Samsung", "size_gb": 4, "speed_mt": 3200, "source": "Samsung module part number"},
}

def parse(text):
    modules = []
    for block in re.split(r"(?=^Handle 0x[0-9A-Fa-f]+, DMI type 17,)", text, flags=re.M):
        if "Memory Device" not in block:
            continue
        fields = dict(re.findall(r"^\s+([^:\n]+):\s*(.*)$", block, flags=re.M))
        if fields.get("Size", "").strip().lower() in ("", "no module installed", "not installed", "unknown"):
            continue
        code = fields.get("Part Number", "").strip().upper()
        catalog = KNOWN.get(code)
        notes = []
        if catalog:
            try:
                observed_size = int(re.search(r"\d+", fields.get("Size", ""))[0])
                if observed_size != catalog["size_gb"]:
                    notes.append("CAPACITY_CONFLICT")
            except (TypeError, ValueError):
                pass
        modules.append({"slot": fields.get("Locator", "unknown"), "manufacturer": fields.get("Manufacturer", "unknown"),
                        "part_number": code or "unknown", "capacity": fields.get("Size", "unknown"),
                        "speed": fields.get("Speed", "unknown"), "configured_speed": fields.get("Configured Memory Speed", "unknown"),
                        "catalog": catalog or "NOT_IN_OFFLINE_CATALOG", "issues": notes,
                        "authenticity": "NOT_VERIFIED"})
    return modules

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", help="Use dmidecode sample text instead of reading hardware")
    p.add_argument("--output", default="reports")
    args = p.parse_args()
    if args.fixture:
        raw = pathlib.Path(args.fixture).read_text()
    else:
        if not shutil.which("dmidecode"):
            p.error("Install dmidecode: sudo apt install dmidecode")
        result = subprocess.run(["dmidecode", "-t", "17"], capture_output=True, text=True)
        if result.returncode:
            p.error("Cannot read DMI: run sudo python3 ramdiag.py")
        raw = result.stdout
    modules = parse(raw)
    out = pathlib.Path(args.output) / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps({"modules": modules, "disclaimer": "PART_NUMBER IS NOT PROOF OF AUTHENTICITY"}, ensure_ascii=False, indent=2))
    rows = "".join("<tr>" + "".join("<td>" + html.escape(str(m.get(k, ""))) + "</td>" for k in ("slot","manufacturer","part_number","capacity","speed","authenticity")) + "</tr>" for m in modules)
    (out / "report.html").write_text("<!doctype html><meta charset='utf-8'><title>RAM-DIAG</title><h1>RAM-DIAG Report</h1><p>Part number does not prove genuine hardware.</p><table border='1'><tr><th>Slot</th><th>Manufacturer</th><th>Part</th><th>Capacity</th><th>Rated speed</th><th>Authenticity</th></tr>"+rows+"</table>")
    print(f"RAM modules: {len(modules)} | Saved: {out}/report.html")
    for m in modules:
        print(f"- {m['slot']}: {m['manufacturer']} {m['part_number']} {m['capacity']} {m['catalog']} {m['issues']}")

if __name__ == "__main__":
    main()
