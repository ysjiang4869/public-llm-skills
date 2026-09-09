---
name: gitlab-issue
description: "拉取指定 GitLab Issue 及其全部评论，按创建时间排序并标注每条评论中的附件链接（图片、/uploads/ 文件）。当用户要求查看 issue 详情、拉取 issue 评论、检查评论附件时使用，如“看一下 issue 123 的评论”。"
---

# GitLab Issue 处理

拉取指定 GitLab Issue 的详情和全部评论，按创建时间排序，并提取每条评论中的附件链接。

## 配置

GitLab 实例与仓库通过 `base_url` / `owner` / `repo` 指定（三者均必需，无内置默认值），按以下优先级解析：

1. **对话中指定**：用户明确说了要查的仓库/实例时（如“看一下 OTHER/another-repo 的 issue 5”），传 `--owner=OTHER --repo=another-repo`
2. 环境变量：`GITLAB_BASE_URL` / `GITLAB_OWNER` / `GITLAB_REPO`
3. 用户级配置文件 `~/.config/skill-config/gitlab-issue.json`（旧路径 `~/.claude/skill-config/` 仍兼容读取）：
   ```json
   {
     "base_url": "https://gitlab.example.com",
     "owner": "<namespace>",
     "repo": "<project>"
   }
   ```

任一项三层都没有时，脚本会报错并提示配置方式。

> 用户级配置文件不在本技能目录内，不随仓库分发，每个用户按自己的需要在本机维护。

## 环境变量（必需）

需要设置 `GITLAB_TOKEN`（GitLab 个人访问令牌，用于 API 鉴权）。**令牌属于敏感信息，只能通过环境变量传入，不要写进任何配置文件**：

```bash
export GITLAB_TOKEN=your_token_here
```

## 使用方式

用户提供 issue ID，例如：
- "看一下 issue 123 的评论"
- "拉取 issue #456 的内容，有没有附件"
- "查一下 OTHER/another-repo 仓库 issue 5 的评论"（指定了非默认仓库）

## 执行步骤

```bash
python3 scripts/process_issue.py <ISSUE_ID> [--owner=<OWNER> --repo=<REPO>] [--base-url=<URL>]
```

- `<ISSUE_ID>`：用户指定的 issue 编号（数字）
- `--owner` / `--repo` / `--base-url`：仅在用户对话中明确指定了仓库/实例时才传入，否则省略，让脚本按环境变量/配置文件解析

## 输出格式

```
Issue #123: Example Issue Title

Found 2 comment(s):

--- Comment 1 ---
ID: 456
Author: username
Created: 2024-01-01T00:00:00Z
Attachments: /uploads/abc/screenshot.png
Content:
# Feature Request

This is a detailed description...

--- Comment 2 ---
ID: 789
Author: another_user
Created: 2024-01-02T00:00:00Z
Content:
# Bug Report

Steps to reproduce...
```

若 issue 没有评论，输出 `No comments found in this issue.`
