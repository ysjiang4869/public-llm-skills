---
name: gitlab-issue
description: "拉取指定 GitLab Issue 及其全部评论，按创建时间排序并标注每条评论中的附件链接（图片、/uploads/ 文件）。当用户要求查看 issue 详情、拉取 issue 评论、检查评论附件时使用，如“看一下 issue 123 的评论”。"
---

# GitLab Issue 处理

拉取指定 GitLab Issue 的详情和全部评论，按创建时间排序，并提取每条评论中的附件链接。

## 参数

| 参数 | 说明 |
|---|---|
| `<ISSUE_ID>` | issue 编号（数字） |
| `--base-url` | GitLab 实例地址；未指定时回退环境变量 `GITLAB_BASE_URL` |
| `--owner` | 项目所属 namespace；未指定时回退环境变量 `GITLAB_OWNER` |
| `--repo` | 项目名；未指定时回退环境变量 `GITLAB_REPO` |
| 环境变量 `GITLAB_TOKEN` | **必需**。GitLab 个人访问令牌。令牌属于敏感信息，只能通过环境变量传入，不要写进任何文件 |

`base_url` / `owner` / `repo` 最终无值时脚本报错。

## 使用方式

用户提供 issue ID，例如：
- "看一下 issue 123 的评论"
- "拉取 issue #456 的内容，有没有附件"
- "查一下 OTHER/another-repo 仓库 issue 5 的评论"（指定了仓库）

## 执行步骤

```bash
python3 scripts/process_issue.py <ISSUE_ID> [--owner=<OWNER> --repo=<REPO>] [--base-url=<URL>]
```

`--owner` / `--repo` / `--base-url` 在对话中明确了实例/仓库时传入，否则依赖环境变量。

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
