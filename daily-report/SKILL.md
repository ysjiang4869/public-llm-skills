---
name: daily-report
description: "读取腾讯文档日报表格，按日期提取指定组成员的原始日报内容。"
allowed-tools: ["exec"]
user-invocable: true
---

# 具身智能产品部日报提取

读取腾讯文档在线表格中指定日期日报，输出指定组各成员原始日报内容（姓名 + 日报原文）。

## 配置

**腾讯文档链接** 和 **小组名** 都可以在对话中临时指定，也可以在用户级配置文件 `~/.claude/skill-config/daily-report.json` 中持久化为默认值（该文件不在本技能目录内、不随仓库分发，每个用户在本机维护一份）：

```json
{
  "url": "https://docs.qq.com/sheet/<file_id>?tab=<sheet_id>",
  "group": "业务平台组"
}
```

- **链接**解析优先级：对话中提供的链接 > 此配置中的 `url`（都没有则向用户询问）
- **小组名**解析优先级：对话中指定（如"帮我拉一下运营组的日报"，传 `--group=运营组`）> 环境变量 `REPORT_GROUP` > 此配置中的 `group` > 内置默认值 `"业务平台组"`

## 使用方式

用户需要提供：
1. **腾讯文档链接**：对话中给出则用对话中的；没给则查用户级配置文件里的 `url`；都没有再询问用户
2. **日期**，如"5.21"、"今天"、"5月21号"
3. （可选）**小组名**：对话中提到则用对话中的，否则按上面优先级解析

示例：
- "帮我拉一下今天的日报 https://docs.qq.com/sheet/DTk1jaXdLS2N0TmpU?tab=3fzlqq"
- "查5.21日报"（链接从用户级配置读取）
- "查一下运营组5.21的日报 https://docs.qq.com/sheet/DTk1jaXdLS2N0TmpU?tab=3fzlqq"

如果用户没有在对话中提供链接，且用户级配置文件里也没有 `url`，再主动询问："请提供日报腾讯文档的链接"。

## 执行步骤

1. 确定要使用的链接：优先用对话中提供的 URL；若用户未提供，读取 `~/.claude/skill-config/daily-report.json` 的 `url` 字段；都没有则向用户询问。再从最终确定的 URL 中解析参数：
   - `file_id`：URL path 部分，即 `https://docs.qq.com/sheet/<file_id>`
   - `sheet_id`：URL 的 `tab=` 参数值

2. 执行以下命令：

```bash
SKILL_DIR="$(dirname "$0")"
TMP=$(mktemp /tmp/daily_report_XXXX.json)

mcporter call tencent-docs sheet.get_cell_data \
  --args "{\"file_id\":\"<file_id>\",\"sheet_id\":\"<sheet_id>\",\"return_csv\":true,\"start_row\":0,\"end_row\":200,\"start_col\":0,\"end_col\":15}" \
  > "$TMP"

python3 "$SKILL_DIR/scripts/parse_daily.py" "<DATE>" [--group="<GROUP>"] < "$TMP"
rm -f "$TMP"
```

其中 `<DATE>` 为用户指定日期，格式 `M.DD`（如 `5.21`）；未指定则用今天日期。`--group` 仅在用户对话中明确指定了小组名时才传入，否则省略，让脚本按配置/默认值解析。

## 输出格式

脚本输出原始数据，每位成员一段：

```
张三
1. xxx
2. xxx

李四
今日完成：...
```

不对内容做任何加工，由 Claude 后续处理。

## 注意

- 跳过请假/调休成员（值为 `调休`、`请假`、`休假`、`—`、`--`）
- 若指定日期列不存在，自动选取最近列
