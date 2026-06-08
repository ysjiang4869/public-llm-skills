---
name: gitlab-issue
description: "拉取 GitLab Issue 及其全部评论，按时间排序并标注每条评论中的附件链接（图片、/uploads/ 文件）。"
allowed-tools: ["exec"]
user-invocable: true
---

# GitLab Issue 处理

拉取指定 GitLab Issue 的详情和全部评论，按创建时间排序，并提取每条评论中的附件链接。

## 配置

`base_url` / `owner` / `repo` 按以下优先级解析（不需要时可全部省略，使用内置默认值）：

1. 环境变量：`GITLAB_BASE_URL` / `GITLAB_OWNER` / `GITLAB_REPO`
2. 用户级配置文件 `~/.claude/skill-config/gitlab-issue.json`：
   ```json
   {
     "base_url": "http://git.komect.net",
     "owner": "HROBOT",
     "repo": "robot-common"
   }
   ```
3. 内置默认值（`http://git.komect.net` / `HROBOT` / `robot-common`）

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

## 执行步骤

```bash
python3 "$(dirname "$0")/scripts/process_issue.py" <ISSUE_ID>
```

`<ISSUE_ID>` 为用户指定的 issue 编号（数字）。

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
