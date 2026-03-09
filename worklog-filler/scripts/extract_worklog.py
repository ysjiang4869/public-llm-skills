#!/usr/bin/env python3
"""
Extract a person's daily work entries from the daily report Excel file.
Usage: python extract_worklog.py <daily_report.xlsx> <person_name> [year_month]
  year_month: optional filter like "2026-02"
Output: JSON to stdout
"""
import sys
import json
import pandas as pd

def extract(report_path, person_name, year_month=None):
    xl = pd.ExcelFile(report_path)
    results = []
    year = year_month[:4] if year_month else "2026"

    for sheet_name in xl.sheet_names:
        if not sheet_name[0].isdigit():
            continue

        df = pd.read_excel(report_path, sheet_name=sheet_name, header=None)
        if df.shape[1] < 4:
            continue

        header = [str(v) for v in df.iloc[0]]
        date_cols = header[3:]

        for _, row in df.iterrows():
            if str(row.iloc[2]) != person_name:
                continue

            for col_idx, date_label in enumerate(date_cols, start=3):
                if col_idx >= len(row):
                    continue
                content = str(row.iloc[col_idx]).strip()
                if content in ('nan', 'None', '', '休假', '调休'):
                    continue

                raw = date_label.strip()
                if len(raw) == 4 and raw.isdigit():
                    date_str = f"{year}-{raw[:2]}-{raw[2:]}"
                else:
                    date_str = raw

                if year_month and not date_str.startswith(year_month):
                    continue

                lines = content.split('\n')
                items = []
                for line in lines:
                    line = line.strip().lstrip('0123456789').lstrip('.').lstrip('、').strip()
                    if line:
                        items.append(line)

                results.append({
                    "date": date_str,
                    "sheet": sheet_name,
                    "items": items,
                    "raw": content
                })
            break

    results.sort(key=lambda x: x["date"])
    return results

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: extract_worklog.py <daily_report.xlsx> <person_name> [year_month]")
        sys.exit(1)

    data = extract(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(json.dumps(data, ensure_ascii=False, indent=2))
