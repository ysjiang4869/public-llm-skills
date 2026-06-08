#!/usr/bin/env python3
"""
Fetch a GitLab issue and its comments, sort by creation time, and list
attachment links (markdown images, /uploads/ paths) found in each comment.

Usage: python3 process_issue.py <issue_id> [--base-url URL] [--owner OWNER] [--repo REPO]

base_url/owner/repo resolution order: CLI flag > env var (GITLAB_BASE_URL/
GITLAB_OWNER/GITLAB_REPO) > user config (~/.claude/skill-config/gitlab-issue.json)
> built-in default below. GITLAB_TOKEN must come from the environment — never
persist a token to a config file.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

IMAGE_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
UPLOADS_RE = re.compile(r'/uploads/[^\s)]+')

DEFAULTS = {
    'base_url': 'http://git.komect.net',
    'owner': 'HROBOT',
    'repo': 'robot-common',
}

USER_CONFIG_PATH = os.path.expanduser('~/.claude/skill-config/gitlab-issue.json')


def load_user_config():
    try:
        with open(USER_CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"ERROR: {USER_CONFIG_PATH} 解析失败: {e}", file=sys.stderr)
        sys.exit(1)


def resolve(cli_value, key, env_name, user_config):
    return cli_value or os.environ.get(env_name) or user_config.get(key) or DEFAULTS[key]


def api_get(base_url, token, path):
    url = f"{base_url.rstrip('/')}/api/v4{path}"
    req = urllib.request.Request(url)
    if token:
        req.add_header('PRIVATE-TOKEN', token)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def get_issue(base_url, token, project, issue_id):
    return api_get(base_url, token, f"/projects/{project}/issues/{issue_id}")


def get_comments(base_url, token, project, issue_id):
    comments = []
    page = 1
    while True:
        batch = api_get(base_url, token, f"/projects/{project}/issues/{issue_id}/notes?per_page=100&page={page}")
        if not batch:
            break
        comments.extend(batch)
        page += 1
    return comments


def find_attachments(body):
    attachments = []
    seen = set()
    for line in body.splitlines():
        line = line.strip()
        for m in IMAGE_RE.finditer(line):
            url = m.group(1)
            if url not in seen:
                seen.add(url)
                attachments.append(url)
        m2 = UPLOADS_RE.search(line)
        if m2:
            url = m2.group(0).rstrip(')')
            if url not in seen:
                seen.add(url)
                attachments.append(url)
    return attachments


def format_result(issue, comments):
    if not comments:
        return "No comments found in this issue."

    processed = []
    for c in comments:
        processed.append({
            'id': c['id'],
            'body': c.get('body', ''),
            'author': c.get('author', {}).get('username', ''),
            'created': c.get('created_at', ''),
            'attachments': find_attachments(c.get('body', '')),
        })
    processed.sort(key=lambda c: c['created'])

    lines = [
        f"Issue #{issue['iid']}: {issue['title']}",
        "",
        f"Found {len(processed)} comment(s):",
        "",
    ]
    for i, c in enumerate(processed, 1):
        lines.append(f"--- Comment {i} ---")
        lines.append(f"ID: {c['id']}")
        lines.append(f"Author: {c['author']}")
        lines.append(f"Created: {c['created']}")
        if c['attachments']:
            lines.append(f"Attachments: {', '.join(c['attachments'])}")
        lines.append(f"Content:\n{c['body']}\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('issue_id', help='GitLab issue ID')
    parser.add_argument('--base-url', help='override the GitLab base URL for this run')
    parser.add_argument('--owner', help='override the project owner/namespace for this run')
    parser.add_argument('--repo', help='override the project name for this run')
    args = parser.parse_args()

    user_config = load_user_config()
    base_url = resolve(args.base_url, 'base_url', 'GITLAB_BASE_URL', user_config)
    owner = resolve(args.owner, 'owner', 'GITLAB_OWNER', user_config)
    repo = resolve(args.repo, 'repo', 'GITLAB_REPO', user_config)
    project = urllib.parse.quote(f"{owner}/{repo}", safe='')
    issue_id = args.issue_id

    token = os.environ.get('GITLAB_TOKEN', '')
    if not token:
        print("ERROR: GITLAB_TOKEN environment variable is not set", file=sys.stderr)
        sys.exit(1)

    try:
        issue = get_issue(base_url, token, project, issue_id)
        comments = get_comments(base_url, token, project, issue_id)
    except urllib.error.HTTPError as e:
        print(f"ERROR: GitLab API request failed: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: failed to reach GitLab: {e.reason}", file=sys.stderr)
        sys.exit(1)

    print(format_result(issue, comments))


if __name__ == '__main__':
    main()
