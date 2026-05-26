---
name: check-daily-report
description: "检查业务平台组当日日报填写情况，输出未填写成员名单。腾讯文档地址从 config.json 读取。"
allowed-tools: ["exec"]
user-invocable: true
---

# 业务平台组日报填写检查

检查业务平台组指定日期日报填写情况，输出未填写成员名单。有任何内容均视为已填写。

## 配置

编辑技能目录下的 `config.json`：

```json
{
  "url": "https://docs.qq.com/sheet/<file_id>?tab=<sheet_id>",
  "group": "业务平台组",
  "exclude": ["张三"]
}
```

- `url`：腾讯文档链接
- `group`：要检查的小组名称
- `exclude`：不参与检查的成员列表

## 使用方式

用户说明要检查的日期（不说则默认今天）：
- "检查今天的日报"
- "看看5.21谁没填日报"
- "日报填写情况"

## 执行步骤

```bash
python3 "$(dirname "$0")/scripts/check_daily.py" "<DATE>"
```

`<DATE>` 为用户指定日期，格式 `M.DD`（如 `5.21`）；未指定则不传参，脚本默认使用今天。

脚本会自动读取 `config.json`，调用 mcporter 获取数据并完成检查。

## 输出格式

```
5月21日 业务平台组 未填写日报（共 N 人）：
- 张三
- 李四
```

若全员已填写：

```
5月21日 业务平台组 未填写日报（共 0 人）：
全员已填写
```
