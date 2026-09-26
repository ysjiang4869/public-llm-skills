#!/usr/bin/env python3
"""
Parse tencent-docs sheet CSV, output raw daily text per member.

Usage:
  mcporter call tencent-docs sheet.get_cell_data \
    --args '...' | python3 parse_daily.py [DATE] [--group=GROUP]

  DATE format: M.DD (e.g. 5.21), defaults to today.
  --group overrides the group for this run (e.g. when the user names a
  different group in conversation).

Group resolution order: --group flag > REPORT_GROUP env var. Error out with
guidance when neither is given.
"""

import argparse, csv, io, json, os, re, sys
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('date', nargs='?', help='M.DD, defaults to today')
    parser.add_argument('--group', help='override the configured group for this run')
    args = parser.parse_args()

    date_arg = args.date
    if date_arg:
        m = re.match(r'^(\d{1,2})\.(\d{1,2})$', date_arg)
        if not m:
            print(f"ERROR: Invalid date '{date_arg}', use M.DD (e.g. 5.21)", file=sys.stderr)
            sys.exit(1)
        month, day = int(m.group(1)), int(m.group(2))
    else:
        today = datetime.now()
        month, day = today.month, today.day

    raw = sys.stdin.buffer.read().decode('utf-8', errors='replace')
    csv_text = None
    jm = re.search(r'\{[\s\S]*\}', raw)
    if jm:
        try:
            d = json.loads(jm.group())
            csv_text = d.get("csv_data", "")
        except:
            pass
    if not csv_text:
        csv_text = raw
    if not csv_text.strip():
        print("ERROR: Empty data", file=sys.stderr)
        sys.exit(1)

    group = args.group or os.environ.get("REPORT_GROUP")
    if not group:
        print(
            "ERROR: 未指定小组名。请通过 --group 参数或环境变量 REPORT_GROUP 指定。",
            file=sys.stderr,
        )
        sys.exit(1)

    rows = list(csv.reader(io.StringIO(csv_text)))
    if not rows:
        print("ERROR: No rows", file=sys.stderr)
        sys.exit(1)

    # Find header row
    hdr, hi = None, 0
    for i, r in enumerate(rows):
        if any('姓名' in c for c in r):
            hdr, hi = r, i
            break
    if not hdr:
        print("ERROR: No header row with '姓名'", file=sys.stderr)
        sys.exit(1)

    # Locate columns
    name_col = None
    group_col = None
    day_cols = {}
    for j, c in enumerate(hdr):
        c = c.strip().replace('\n', '')
        if c == '姓名':
            name_col = j
        elif c == '小组':
            group_col = j
        else:
            m = re.match(r'^(\d{1,2})\.?(\d{2})$', c)
            if m:
                day_cols[int(m.group(1)) * 100 + int(m.group(2))] = j

    if name_col is None or not day_cols:
        print("ERROR: Bad header format", file=sys.stderr)
        sys.exit(1)

    # If no explicit 小组 column, fall back to column before name
    if group_col is None:
        group_col = name_col - 1

    tn = month * 100 + day
    if tn not in day_cols:
        print(f"ERROR: {month}.{day:02d} 日期列不存在", file=sys.stderr)
        sys.exit(1)
    day_col = day_cols[tn]

    print(f"实际日期：{month}月{day}日")

    in_group = False
    for i in range(hi + 1, len(rows)):
        row = rows[i]
        if not row or all(not c.strip() for c in row):
            continue

        # Check 小组 column to track which group we're in
        grp_val = row[group_col].strip().replace('\n', '') if group_col < len(row) else ''

        if grp_val == group:
            in_group = True
            # Fall through — first member of the group is on this same row
        elif grp_val and in_group:
            # Entered a different sub-group, stop
            break

        if not in_group:
            continue

        # Extract member name
        name = None
        if name_col < len(row):
            nc = row[name_col].strip().replace('\n', '')
            if re.match(r'^[一-鿿]{2,5}$', nc):
                name = nc
        if not name:
            continue

        daily = row[day_col].strip() if day_col < len(row) else ''
        if not daily or daily in ('调休', '请假', '休假', '—', '--'):
            continue

        print(name)
        print(daily)
        print()


if __name__ == "__main__":
    main()
