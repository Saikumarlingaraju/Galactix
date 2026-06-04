from pathlib import Path
import json

try:
    from markitdown import MarkItDown
except Exception:
    MarkItDown = None

try:
    import pandas as pd
except Exception as e:
    raise SystemExit("pandas is required to run this script: %s" % e)


def convert_xlsx_to_json(xlsx_path: Path, json_path: Path):
    if not xlsx_path.exists():
        raise FileNotFoundError(f"{xlsx_path} not found")

    # Optional: instantiate MarkItDown to ensure the tool is present
    if MarkItDown is None:
        print("Warning: markitdown not importable; proceeding with pandas conversion.")
    else:
        try:
            _ = MarkItDown()
        except Exception:
            print("Warning: markitdown could not be instantiated; proceeding with pandas conversion.")

    sheets = pd.read_excel(xlsx_path, sheet_name=None, engine="openpyxl")

    payload = {"source": xlsx_path.name, "sheets": {}}
    for sheet_name, df in sheets.items():
        cols = [str(c) for c in df.columns.tolist()]
        # Convert NaN to None for JSON compatibility
        rows = df.where(pd.notnull(df), None).to_dict(orient="records")
        payload["sheets"][sheet_name] = {
            "columns": cols,
            "row_count": len(rows),
            "rows": rows,
        }

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    xlsx = Path("user_a.xlsx")
    out = Path("user_a.json")
    convert_xlsx_to_json(xlsx, out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
