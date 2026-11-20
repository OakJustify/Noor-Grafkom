"""Read-only inventory of the caller-supplied reference; never executes it.

Package table interpretation is a validated hypothesis, not a full file-format
decoder. Output includes identities and selected literal names, NOT assets.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def inspect(root: Path):
    records = []
    pattern = re.compile(rb"physics|joint|gravity|friction|rope|buoy|timestep|BoyGrabState", re.I)
    for name in ("limbo.exe", "limbo_boot.pkg", "limbo_runtime.pkg"):
        path = root / name
        data = path.read_bytes()
        record = {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        if name.endswith(".pkg"):
            count = struct.unpack_from("<I", data)[0]
            payload = 4 + count * 12
            if count == 0 or payload > len(data):
                raise ValueError(f"Unsupported package header: {path}")
            entries = [struct.unpack_from("<III", data, 4 + i * 12) for i in range(count)]
            record["package_table_hypothesis"] = {
                "layout": "uint32 count, count * (uint32 identifier, uint32 offset, uint32 size), payload",
                "count": count, "payload_offset": payload,
                "all_ranges_within_file": all(payload + offset + size <= len(data) for _, offset, size in entries),
                "last_member_ends_at_eof": payload + max(offset + size for _, offset, size in entries) == len(data),
                "limitations": "Member identifiers are opaque; filenames, compression and object serialization not decoded.",
            }
        literals, seen, total = [], set(), 0
        for match in re.finditer(rb"[\x20-\x7e]{6,}", data):
            if pattern.search(match.group()):
                total += 1
                text = match.group().decode("ascii")[:220]
                if text not in seen:
                    literals.append({"offset": match.start(), "text": text})
                    seen.add(text)
        record["matching_literal_count"] = total
        record["unique_matching_literal_count"] = len(literals)
        record["selected_literals"] = literals[:140]
        record["selected_literal_limit"] = 140
        records.append(record)
    settings = (root / "settings.txt").read_text()
    return {"method": "Static byte inventory; no target execution or asset copying.",
            "artifacts": records, "settings_observations": [line for line in settings.splitlines()
            if any(s in line for s in ("action", "up ", "left ", "right ", "backbufferheight", "windowedmode", "use30hz"))],
            "unknowns": ["Exact collision and integration algorithms", "Runtime timestep and physical units",
                         "True defaults of debug parameter ranges", "Exact original puzzle geometry and behavior"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for artifact in report["artifacts"]:
        print(artifact["path"], artifact["sha256"], artifact.get("package_table_hypothesis", {}))
    print("Saved read-only findings:", args.output)


if __name__ == "__main__":
    main()
