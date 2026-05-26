#!/usr/bin/env python3
"""
Check which members haven't filled in their daily report.
Config is read from config.json in the parent directory.

Usage: python3 check_daily.py [DATE]
  DATE format: M.DD (e.g. 5.21), defaults to today
"""

import csv, io, json, os, re, subprocess, sys
from datetime import datetime


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, '..', 'config.json')

    with open(config_path) as f:
        config = json.load(f)

    url = config['url']
    m = re.match(r'https://docs\.qq\.com/sheet/([^?#]+).*[?&]tab=([^&#]+)', url)
    if not m:
        print(f"ERROR: 无法解析 URL: {url}", file=sys.stderr)
        sys.exit(1)
    file_id, sheet_id = m.group(1), m.group(2)
    group = config.get('group', '业务平台组')
    exclude = set(config.get('exclude', []))

    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if date_arg:
        dm = re.match(r'^(\d{1,2})\.(\d{1,2})$', date_arg)
        if not dm:
            print(f"ERROR: 日期格式错误 '{date_arg}'，请用 M.DD（如 5.21）", file=sys.stderr)
            sys.exit(1)
        month, day = int(dm.group(1)), int(dm.group(2))
    else:
        today = datetime.now()
        month, day = today.month, today.day

    args_json = json.dumps({
        "file_id": file_id,
        "sheet_id": sheet_id,
        "return_csv": True,
        "start_row": 0,
        "end_row": 200,
        "start_col": 0,
        "end_col": 15
    })
    import tempfile, shlex
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tf:
        tmp_path = tf.name
    subprocess.run(
        f"mcporter call tencent-docs sheet.get_cell_data --args {shlex.quote(args_json)} > {shlex.quote(tmp_path)}",
        shell=True
    )
    with open(tmp_path, 'rb') as f:
        raw = f.read().decode('utf-8', errors='replace')
    os.unlink(tmp_path)

    csv_text = None
    jm = re.search(r'\{[\s\S]*\}', raw)
    if jm:
        try:
            d = json.loads(jm.group())
            csv_text = d.get('csv_data', '')
        except:
            pass
    if not csv_text:
        csv_text = raw
    if not csv_text.strip():
        print("ERROR: 获取数据为空", file=sys.stderr)
        sys.exit(1)

    rows = list(csv.reader(io.StringIO(csv_text)))

    hdr, hi = None, 0
    for i, r in enumerate(rows):
        if any('姓名' in c for c in r):
            hdr, hi = r, i
            break
    if not hdr:
        print("ERROR: 未找到表头行", file=sys.stderr)
        sys.exit(1)

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
            dm = re.match(r'^(\d{1,2})\.?(\d{2})$', c)
            if dm:
                day_cols[int(dm.group(1)) * 100 + int(dm.group(2))] = j

    if name_col is None or not day_cols:
        print("ERROR: 表头格式错误", file=sys.stderr)
        sys.exit(1)
    if group_col is None:
        group_col = name_col - 1

    tn = month * 100 + day
    if tn in day_cols:
        day_col = day_cols[tn]
    else:
        closest = min(day_cols.keys(), key=lambda k: abs(k - tn))
        day_col = day_cols[closest]
        cm, cd = closest // 100, closest % 100
        print(f"WARN: {month}.{day:02d} 列不存在，使用最近列 {cm}.{cd:02d}", file=sys.stderr)

    in_group = False
    missing = []

    for i in range(hi + 1, len(rows)):
        row = rows[i]
        if not row or all(not c.strip() for c in row):
            continue

        grp_val = row[group_col].strip().replace('\n', '') if group_col < len(row) else ''

        if grp_val == group:
            in_group = True
        elif grp_val and in_group:
            break

        if not in_group:
            continue

        name = None
        if name_col < len(row):
            nc = row[name_col].strip().replace('\n', '')
            if re.match(r'^[一-鿿]{2,5}$', nc):
                name = nc
        if not name or name in exclude:
            continue

        daily = row[day_col].strip() if day_col < len(row) else ''
        if not daily:
            missing.append(name)

    print(f"{month}月{day}日 {group} 未填写日报（共 {len(missing)} 人）：")
    if missing:
        for name in missing:
            print(f"- {name}")
    else:
        print("全员已填写")


if __name__ == '__main__':
    main()
