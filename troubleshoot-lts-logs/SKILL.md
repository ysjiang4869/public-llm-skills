---
name: troubleshoot-lts-logs
description: "Diagnose robot-platform failures by understanding the relevant business code, deriving the CMCC LTS group/node, and querying logs with a self-contained CLI script (no MCP server needed). Use for exceptions, failed requests, signaling, status reporting, incidents, or trace IDs that require code and LTS evidence. 中文：结合项目代码与移动云 LTS 日志定位 robot-platform 故障：先读代码推导日志组/日志流，再用自带脚本查询日志并跨服务关联，不依赖 MCP；当用户要求排查线上/测试环境异常、失败请求、信令、状态上报、TID 问题时使用。"
---

# LTS 日志排查（独立版）

用自带脚本 `scripts/lts_search.py` 直接查询移动云 LTS，本地完成 AK/SK 签名，只读，不依赖任何 MCP Server。以代码和日志为相互独立的证据；两者都可得时，不要仅凭其一猜测根因。

## 安全边界

- AK/SK 只能来自环境变量或凭证文件（见下节），由脚本自行读取。不要让用户把 AK/SK 发到对话中，不要写进命令参数、仓库或日志。
- 查询是只读操作，可以直接执行；本技能没有任何写操作。
- 脚本已对日志消息中的 `Authorization`、`Cookie`、`password`、`secret`、`access_token` 做脱敏，输出中若再遇到凭证类内容也不要复述。
- 不要把任意标识符当作 TID；优先使用明确的 `TID` 字段或已知 TID 格式。
- TID 仅在同一服务/node 内有效，绝不能用 TID 关联不同服务的日志。
- 时间或业务字段的关联只是启发式推断，报告时必须说明，不得声称端到端链路。
- 把行为归因到代码时，引用相关文件路径和行号。

## 凭证

脚本按以下顺序解析（环境变量优先）：

1. 环境变量：`CMCC_AK`、`CMCC_SK`、`CMCC_PROJECT_ID`（可选 `CMCC_LTS_BASE_URL`、`CMCC_X_LANGUAGE`、`CMCC_HTTP_TIMEOUT_SEC`、`CMCC_GROUP_LOG_GROUP_MAP`、`CMCC_NODE_LOG_STREAM_MAP`）。
2. `--config` 或 `LTS_TROUBLESHOOTER_CONFIG` 指向的凭证文件。
3. 默认路径 `~/.config/lts-troubleshooter/credentials.env`（Windows 为 `%APPDATA%\lts-troubleshooter\credentials.env`）。

与 lts-troubleshooter MCP 项目使用同一套凭证，已配置过的成员无需重复配置。缺凭证时脚本会报 `missing CMCC_AK, ...`，此时向用户说明配置方法，不要代替用户编造凭证。

## 工作流

1. 从当前工作区或用户给出的代码位置定位相关代码。不要因为用户没提供 `group`、`node` 或环境就发问。
2. 从描述的症状和代码位置出发，理解足够多的周边业务逻辑，以解释相关路径并选出有用的日志证据；问题局部时不要强行做完整端到端数据流分析。
3. 当相关逻辑到达 Feign/HTTP 客户端、消息、信令边界、回调或其他可部署模块时，跟随证据跨过边界并纳入该服务。不要仅因为架构图中存在就扩展到无关服务。
4. 阅读 [references/robot-platform-routing.md](references/robot-platform-routing.md)，由仓库路径和 `spring.application.name` 推导每个涉及服务的 LTS `group` 和 `node`；包名只作辅助证据。
5. 从相关阶段提取窄检索词：endpoint、固定日志文案、异常类名、错误码、命令/事件类型、设备或业务标识、类与方法。优先使用代码中实际存在的词。
6. 先确认凭证与可用目标：

   ```bash
   python3 scripts/lts_search.py groups
   ```

   输出 `credentialsOk`、可用 `groups` 和 `nodes`。推导出的名字不在列表中时，回头检查第 4 步的路由推导，而不是让用户选。
7. 按因果顺序用小时间窗（Asia/Shanghai）查询各服务。关键词含空格或 LTS 表达式时用单引号包裹：

   ```bash
   python3 scripts/lts_search.py search \
     --group robot-business --node robot-business-device \
     --start '2026-11-06 10:00' --end '2026-11-06 10:30' \
     --keywords 'DeviceReportException AND 861234567890' --limit 100
   ```

   跨服务流程（命令下发、设备状态上报等）只有在 inspected 逻辑支持该边界时才同时查两个服务。
8. 结果为空时每次只变一个维度：简化 `AND`、放宽时间、换一个代码衍生的检索词。不要让用户选择可以从代码推导出的日志目标。
9. 出现可信 TID 时，去掉 `[TID:` 和 `]` 等包装后，仅对同一服务/node 再次查询。TID 是服务局部的，绝不能跨服务使用。
10. 用窄时间窗和共同业务证据（设备 ID、用户 ID、命令/事件类型、请求字段、payload 标识）关联服务，并说明该关联是启发式的。
11. `truncated` 为 true 时收窄时间范围或关键词后再查，不要声称集合完整。
12. 报告症状、相关业务路径、时间线、各服务日志证据、匹配的代码路径、可能根因、置信度和下一步验证或修复。区分事实与推断。

## 输出与错误

脚本输出 JSON：`query`（回显查询参数）、`isQueryComplete`、`count`、`returned`、`truncated`、`logs[]`（time、level、TID、lineNum、containerName、podName、pathFile、message）、`nextAction`。

- `unknown group/node`：名字不在映射里，先跑 `groups` 看可用值并复查路由推导。
- `missing CMCC_AK, ...`：凭证未配置，见「凭证」一节。
- `query range must not exceed 2 hours`：切分时间窗分段查询。
- HTTP 4xx（带 requestId）：多为凭证或权限问题，检查凭证有效性，不要重试轰炸。
- 网络类错误（`LTS request failed`）：确认 `CMCC_LTS_BASE_URL` 与网络可达性后重试一次。
