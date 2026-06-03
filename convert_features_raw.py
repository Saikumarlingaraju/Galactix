from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from markitdown import MarkItDown
except ImportError:  # pragma: no cover - optional dependency check
    MarkItDown = None


def coerce_value(raw_value: str):
    value = raw_value.strip()
    if value == "":
        return None

    try:
        number = float(value)
    except ValueError:
        return value

    if number.is_integer():
        return int(number)

    return number


def read_csv_rows(csv_path: Path):
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        headers = [header.strip() for header in headers if header and header.strip()]

        rows = []
        for row in reader:
            parsed_row = {}
            for index, header in enumerate(headers):
                parsed_row[header] = coerce_value(row[index]) if index < len(row) else None
            rows.append(parsed_row)

    return headers, rows


def export_json(csv_path: Path, json_path: Path):
    headers, rows = read_csv_rows(csv_path)
    payload = {
        "source": csv_path.name,
        "columns": headers,
        "row_count": len(rows),
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_markdown_preview(csv_path: Path, markdown_path: Path):
    if MarkItDown is None:
        raise RuntimeError("MarkItDown is not available in the current environment.")

    converter = MarkItDown()
    result = converter.convert_local(str(csv_path))
    markdown_path.write_text(result.text_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Convert features_raw.csv into JSON for downstream AI tools.")
    parser.add_argument("--csv", default="features_raw.csv", help="Input CSV file")
    parser.add_argument("--json", default="features_raw.json", help="Output JSON file")
    parser.add_argument(
        "--markdown-preview",
        default=None,
        help="Optional Markdown preview output generated through MarkItDown",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    json_path = Path(args.json)

    export_json(csv_path, json_path)

    if args.markdown_preview:
        export_markdown_preview(csv_path, Path(args.markdown_preview))

    print(f"Wrote {json_path}")
    if args.markdown_preview:
        print(f"Wrote {args.markdown_preview}")


if __name__ == "__main__":
    main()