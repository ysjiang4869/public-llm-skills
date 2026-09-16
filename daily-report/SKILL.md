---
name: daily-report
description: "Fetch raw daily-report entries (member name + original text) by date for a given team from a Tencent Docs online spreadsheet. 中文：读取腾讯文档在线表格，按日期提取指定小组各成员的日报原文；当用户要求拉取/汇总/查看某天日报时使用，如“帮我拉一下今天的日报”“查 5.21 日报”。"
---

# 日报提取（腾讯文档）

读取腾讯文档在线表格中指定日期日报，输出指定小组各成员的原始日报内容（姓名 + 日报原文）。

## 参数

| 参数 | 说明 |
|---|---|
| `<DATE>` | 日期，格式 `M.DD`（如 `5.21`）；未指定则默认今天 |
| `--group` | 小组名；未指定时回退环境变量 `REPORT_GROUP`，仍无则报错 |
| 环境变量 `REPORT_GROUP` | 默认小组名 |

## 使用方式

用户提供 **腾讯文档链接**、**日期**，以及（可选）**小组名**：
- "帮我拉一下今天的日报 https://docs.qq.com/sheet/xxxx?tab=xxxx"
- "查一下运营组5.21的日报 https://docs.qq.com/sheet/xxxx?tab=xxxx"

对话中没有链接且环境变量也未提供小组名时，先向用户询问再执行。

## 执行步骤

1. 从 URL 解析参数（对话中没有链接则向用户询问）：
   - `file_id`：URL path 部分，即 `https://docs.qq.com/sheet/<file_id>`
   - `sheet_id`：URL 的 `tab=` 参数值

2. 调用 mcporter（需已安装并配置 tencent-docs MCP 服务）拉取表格数据，保存到临时文件，再执行本技能目录下的解析脚本：

```bash
mcporter call tencent-docs sheet.get_cell_data \
  --args "{\"file_id\":\"<file_id>\",\"sheet_id\":\"<sheet_id>\",\"return_csv\":true,\"start_row\":0,\"end_row\":200,\"start_col\":0,\"end_col\":15}" \
  > /tmp/daily_report.json

python3 scripts/parse_daily.py "<DATE>" [--group="<GROUP>"] < /tmp/daily_report.json
```

`--group` 在对话或环境变量明确了小组名时传入。

## 输出格式

脚本输出原始数据，每位成员一段：

```
张三
1. xxx
2. xxx

李四
今日完成：...
```

不对内容做任何加工，输出原文供后续处理。

## 注意

- 跳过请假/调休成员（值为 `调休`、`请假`、`休假`、`—`、`--`）
- 若指定日期列不存在，自动选取最近列
