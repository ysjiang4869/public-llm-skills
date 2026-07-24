#!/usr/bin/env python3
"""把 Markdown 大纲转换成思绪思维导图的 .smm 文件。

层级规则（与 simple-mind-map 自带的 markdown 导入一致）：
  - `#`/`##`/... 标题按 depth 嵌套，第一个标题作为根节点
  - `-`/`*`/`+` 列表按缩进嵌套，挂在最近的标题下
  - 行尾 `{key:value, key:value}` 为内联标注

用法：
  python3 outline_to_smm.py outline.md -o out.smm --theme classic4 --layout logicalStructure
  cat outline.md | python3 outline_to_smm.py - -o out.smm
"""

import argparse
import json
import re
import sys
import uuid

ANNOTATION_RE = re.compile(r"\s*\{((?:[^{}\\]|\\.)*)\}\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")

# 简单标注 -> data 字段
SCALAR_KEYS = {
    "note": "note",
    "link": "hyperlink",
    "linktitle": "hyperlinkTitle",
    "image": "image",
    "imagetitle": "imageTitle",
    "fill": "fillColor",
    "color": "color",
    "border": "borderColor",
    "shape": "shape",
    "font": "fontFamily",
    "align": "textAlign",
}
NUMBER_KEYS = {
    "size": "fontSize",
    "borderwidth": "borderWidth",
    "radius": "borderRadius",
}
LIST_KEYS = {"icon": "icon", "tag": "tag"}
BOOL_KEYS = {"bold": "fontWeight", "italic": "fontStyle"}


def unescape(s):
    return re.sub(r"\\(.)", r"\1", s)


def split_annotations(raw):
    """拆出 (纯文本, 标注 dict)。"""
    m = ANNOTATION_RE.search(raw)
    if not m:
        return raw.strip(), {}
    text = raw[: m.start()].strip()
    body = m.group(1)
    pairs = {}
    # 按未转义的逗号切分
    for part in re.split(r"(?<!\\),", body):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        pairs[k.strip().lower()] = unescape(v.strip())
    return text, pairs


def apply_annotations(data, ann, strict):
    summary = None
    for key, val in ann.items():
        if key in LIST_KEYS:
            data[LIST_KEYS[key]] = [p.strip() for p in re.split(r"(?<!\\)\|", val) if p.strip()]
        elif key in SCALAR_KEYS:
            data[SCALAR_KEYS[key]] = val
        elif key in NUMBER_KEYS:
            try:
                data[NUMBER_KEYS[key]] = float(val) if "." in val else int(val)
            except ValueError:
                warn(f"标注 {key} 的值 {val!r} 不是数字，已忽略", strict)
        elif key in BOOL_KEYS:
            truthy = val.lower() not in ("false", "0", "no", "")
            if key == "bold":
                data["fontWeight"] = "bold" if truthy else "normal"
            else:
                data["fontStyle"] = "italic" if truthy else "normal"
        elif key == "collapse":
            data["expand"] = val.lower() in ("false", "0", "no")
        elif key == "summary":
            summary = val
        else:
            warn(f"未知标注 {key!r}，已忽略", strict)
    return summary


def warn(msg, strict):
    if strict:
        raise SystemExit(f"错误: {msg}")
    print(f"警告: {msg}", file=sys.stderr)


def make_node(text, ann, with_uid, strict):
    data = {"text": text, "expand": True}
    if with_uid:
        data["uid"] = uuid.uuid4().hex[:16]
    summary = apply_annotations(data, ann, strict)
    if summary is not None:
        g = {"text": summary, "expand": True}
        if with_uid:
            g["uid"] = uuid.uuid4().hex[:16]
        data["generalization"] = [g]
    return {"data": data, "children": []}


def parse_outline(lines, with_uid=True, strict=False):
    """返回根节点。标题栈 + 列表缩进栈混合处理。"""
    root = None
    # 栈元素: (level, node)。标题 level 用负数区间保证永远高于列表项
    stack = []

    def push(level, node):
        while stack and stack[-1][0] >= level:
            stack.pop()
        if not stack:
            return False
        stack[-1][1]["children"].append(node)
        stack.append((level, node))
        return True

    in_code_fence = False
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if line.strip().startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or not line.strip():
            continue

        m = HEADING_RE.match(line)
        if m:
            depth = len(m.group(1))
            text, ann = split_annotations(m.group(2))
            if not text:
                continue
            node = make_node(text, ann, with_uid, strict)
            if root is None:
                root = node
                stack = [(depth, node)]
                continue
            level = depth
            if not push(level, node):
                # 比根标题还浅的标题：挂到根下
                root["children"].append(node)
                stack = [(stack[0][0], root), (level, node)]
            continue

        m = LIST_RE.match(line)
        if m:
            indent = len(m.group(1).expandtabs(4))
            text, ann = split_annotations(m.group(2))
            if not text:
                continue
            node = make_node(text, ann, with_uid, strict)
            if root is None:
                root = node
                stack = [(0, node)]
                continue
            # 列表项永远排在标题之后：level = 100 + 缩进层数
            level = 100 + indent // 2
            if not push(level, node):
                root["children"].append(node)
                stack = [(stack[0][0] if stack else 1, root), (level, node)]
            continue

        # 普通段落：作为上一个节点的备注补充
        text, ann = split_annotations(line.strip())
        if not text or root is None:
            continue
        node = make_node(text, ann, with_uid, strict)
        if not push(1000, node):
            root["children"].append(node)

    return root


def main():
    p = argparse.ArgumentParser(description="Markdown 大纲 -> .smm 思维导图文件")
    p.add_argument("input", help="输入 Markdown 文件，- 表示标准输入")
    p.add_argument("-o", "--output", required=True, help="输出 .smm 文件路径")
    p.add_argument("--theme", default="classic4", help="主题名，默认 classic4")
    p.add_argument("--layout", default="logicalStructure", help="布局，默认 logicalStructure")
    p.add_argument("--config", help="theme.config 的 JSON 字符串或 .json 文件路径")
    p.add_argument("--no-uid", action="store_true", help="不生成 uid")
    p.add_argument("--minify", action="store_true", help="压缩输出，不缩进")
    p.add_argument("--strict", action="store_true", help="遇到未知标注即报错")
    args = p.parse_args()

    if args.input == "-":
        lines = sys.stdin.read().splitlines()
    else:
        with open(args.input, encoding="utf-8") as f:
            lines = f.read().splitlines()

    root = parse_outline(lines, with_uid=not args.no_uid, strict=args.strict)
    if root is None:
        raise SystemExit("错误: 大纲为空，没有解析出任何节点")

    theme_config = {}
    if args.config:
        try:
            theme_config = json.loads(args.config)
        except json.JSONDecodeError:
            with open(args.config, encoding="utf-8") as f:
                theme_config = json.load(f)

    doc = {
        "layout": args.layout,
        "root": root,
        "theme": {"template": args.theme, "config": theme_config},
        "config": {},
    }

    with open(args.output, "w", encoding="utf-8") as f:
        if args.minify:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    count = 0
    stack = [root]
    while stack:
        n = stack.pop()
        count += 1
        stack.extend(n.get("children", []))
    print(f"已生成 {args.output}：{count} 个节点，主题 {args.theme}，布局 {args.layout}")


if __name__ == "__main__":
    main()
