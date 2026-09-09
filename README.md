# public-llm-skills

个人维护的 [Agent Skills](https://agentskills.io) 集合。每个子目录是一个独立技能（根部含 `SKILL.md`），遵循开放的 Agent Skills 规范，可被 Claude Code 及其他兼容客户端使用。

## 技能一览

| 技能 | 功能 | 依赖 |
|---|---|---|
| [daily-report](daily-report/) | 按日期从腾讯文档在线表格提取指定小组成员的原始日报 | mcporter + tencent-docs MCP |
| [check-daily-report](check-daily-report/) | 检查指定小组某日日报填写情况，输出未填写名单 | mcporter + tencent-docs MCP |
| [gitlab-issue](gitlab-issue/) | 拉取 GitLab Issue 及评论，按时间排序并标注附件链接 | `GITLAB_TOKEN` 环境变量 |
| [smm-mindmap](smm-mindmap/) | 把文本大纲转成思绪思维导图（simple-mind-map）的 `.smm` 文件 | 无（Python 标准库） |
| [worklog-filler](worklog-filler/) | 从日报 Excel 提取工作条目，按需求类型拆分归类并填写工作量统计表 | pandas、openpyxl |

## 安装

技能不绑定安装位置，把需要的技能目录放进客户端的技能目录即可。以 symlink 为例（clone 本仓库后）：

```bash
ln -s ~/Code/public-llm-skills/daily-report   ~/.claude/skills/daily-report
ln -s ~/Code/public-llm-skills/check-daily-report ~/.claude/skills/check-daily-report
ln -s ~/Code/public-llm-skills/gitlab-issue   ~/.claude/skills/gitlab-issue
ln -s ~/Code/public-llm-skills/smm-mindmap    ~/.claude/skills/smm-mindmap
ln -s ~/Code/public-llm-skills/worklog-filler ~/.claude/skills/worklog-filler
```

其他客户端（如 Codex、OpenCode 等）按各自文档，将技能目录放入其对应的 skills 路径。

## 参数与环境变量

技能不读取任何配置文件。参数在运行时从对话中提取，通过 CLI 参数传给脚本；常用默认值可通过环境变量提供（如 `REPORT_GROUP`、`DAILY_REPORT_URL`、`GITLAB_BASE_URL` / `GITLAB_OWNER` / `GITLAB_REPO`），详见各技能 `SKILL.md` 的参数说明。

敏感信息（如 `GITLAB_TOKEN`）只通过环境变量传入，不要写进任何文件。

## License

[MIT](LICENSE)
