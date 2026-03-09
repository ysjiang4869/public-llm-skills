---
name: worklog-filler
description: Fill a monthly R&D support workload statistics report from a daily work log Excel file. Use this skill when the user provides a daily report Excel (工作日报) and a statistics/workload report Excel (工作量统计表), and wants to extract their daily work items, split them by requirement type, and fill in the stats report automatically. Triggered by phrases like "填写工作量统计表", "从日报填写量表", "拆解工作量记录" etc.
---

# Worklog Filler

## Overview

Extract a named person's daily work entries from a structured daily report Excel file, intelligently split and categorize each work item into allowed requirement types (读取下拉限制), then write the resulting records into the monthly workload statistics report.



## Workflow

### Step 1: Gather inputs

To run this skill, require the following from the user if not already provided:
- `daily_report_path`: path to the daily report Excel (e.g. xxx部门工作日报.xlsx)
- `stats_report_path`: path to the statistics report Excel (e.g. 26年2月-研发支撑工作量统计表.xlsx)
- `person_name`: the person's Chinese name (e.g. 张三)
- `year_month`: the month to process, e.g. `2026-02` (infer from filename or ask)
- `stats_sheet`: sheet name in the stats report (default: detect automatically — look for a sheet containing "研发支撑")

### Step 2: Extract daily work entries

Run the extraction script to get all non-holiday work entries for the person:

```bash
python3 ~/.claude/skills/worklog-filler/scripts/extract_worklog.py \
  "<daily_report_path>" "<person_name>" "<year_month>"
```

The script outputs a JSON array of objects:
```json
[
  {
    "date": "2026-02-02",
    "sheet": "0202-0206",
    "items": ["quic协议开发：开发进度30%", "版本延期情况对齐", "1.22.2版本发布准备"],
    "raw": "..."
  }
]
```

### Step 3: Read stats report metadata

Run the metadata script to get the allowed requirement type options and existing data:

```bash
python3 ~/.claude/skills/worklog-filler/scripts/read_stats_meta.py \
  "<stats_report_path>" "<stats_sheet>"
```

Output:
```json
{
  "req_types": ["线上问题定位", "需求评审", "功能优化", ...],
  "groups": ["运营平台组", "业务平台组", ...],
  "first_empty_row": 2
}
```

### Step 4: Categorize and split work items

For each day's items, group them by requirement type and assign time (人天). Follow these rules:

**Grouping**: Items of the same type on the same day → merge into one record. Different types → separate records.

**Time allocation**: Each working day = 1.0 person-day total. Split proportionally among records for that day based on item count and complexity. Use increments of 0.1. Sum per day must equal 1.0.

**Requirement type mapping** — map work content to the closest allowed type from `req_types`:

| Work content keywords | Map to |
|----------------------|--------|
| 开发、实现、重构、编码、自测 | 功能优化 |
| 需求评审、需求讨论、接口评审、方案讨论 | 需求评审 / 接口设计及评审 / 需求及方案讨论 |
| 版本发布、上线、发版、发布准备 | 上线准备 |
| 问题排查、定位、bug、异常、修复 | 线上问题定位 / bug修复 |
| 脚本、工具开发 | 工具脚本开发 |
| 运维、资源申请、环境搭建 | 其他 |
| 周报、月报、年会、日常管理 | 其他 |
| 技术调研、方案调研 | 技术调研 |
| 测试、用例 | 测试支撑 / 测试用例评审 |
| 演示、支撑 | 演示支撑 |

Always choose from the actual `req_types` list returned in Step 3. Never invent new types.

**Output format** — produce a JSON array of records:
```json
[
  {"date": "2026-02-02", "req_type": "功能优化", "description": "quic协议开发：调整为rpc对接，开发进度30%", "hours": 0.5},
  {"date": "2026-02-02", "req_type": "需求及方案讨论", "description": "四足版本延期情况对齐；1.22.2版本发布准备", "hours": 0.5}
]
```

### Step 5: Write records to stats report

Save the JSON array to a temp file, then run:

```bash
python3 ~/.claire/skills/worklog-filler/scripts/write_records.py \
  "<stats_report_path>" /tmp/worklog_records.json "<stats_sheet>"
```

Or pass JSON inline as second argument if small enough.

### Step 6: Verify and report

After writing, read back the stats sheet with pandas to verify:
```python
import pandas as pd
df = pd.read_excel(stats_path, sheet_name=sheet)
print(df[['报表年月','需求类型','具体工作任务描述','实际花费时间（人天）']].to_string())
print(f"合计人天: {df['实际花费时间（人天）'].sum():.1f}")
```

Report to the user:
- Total records written
- Total person-days
- Breakdown by requirement type
- Note any days with missing data (holidays, etc.)

## Notes

- The stats report columns filled are: A (报表年月), G (需求类型), H (具体工作任务描述), I (实际花费时间（人天）)
- Other columns (部门, 团队, 产品名称, 工号, 所属小组) are left for the user to fill manually
- Daily report sheet names are date ranges like `0202-0206`; the script handles year inference automatically
- Days marked 休假 or 调休 are skipped
- If the stats sheet already has data, new records are appended after existing rows
