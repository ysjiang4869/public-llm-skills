#!/usr/bin/env python3
"""校验 .smm / .json 思维导图文件的结构是否合法。

用法: python3 validate_smm.py file.smm [--quiet]
退出码: 0 = 通过（可能有警告），1 = 有错误
"""

import argparse
import json
import sys

LAYOUTS = {
    "logicalStructure", "logicalStructureLeft", "mindMap", "organizationStructure",
    "catalogOrganization", "timeline", "timeline2", "fishbone", "fishbone2",
    "rightFishbone", "rightFishbone2", "verticalTimeline", "verticalTimeline2",
    "verticalTimeline3",
}

SHAPES = {
    "rectangle", "diamond", "parallelogram", "roundedRectangle", "octagonalRectangle",
    "outerTriangularRectangle", "innerTriangularRectangle", "ellipse", "circle",
}

THEMES = {
    "default",
    # dark
    "classic", "blackHumour", "lateNightOffice", "blackGold", "orangeJuice",
    "neonLamp", "darkNightLceBlade", "dark", "dark2", "dark3", "dark4", "dark5",
    "dark6", "dark7",
    # light
    "skyGreen", "classicGreen", "classicBlue", "blueSky", "brainImpairedPink",
    "earthYellow", "freshGreen", "freshRed", "romanticPurple", "pinkGrape", "mint",
    "gold", "vitalityOrange", "greenLeaf", "minions", "simpleBlack", "courseGreen",
    "coffee", "redSpirit", "avocado", "autumn", "oreo", "shallowSea", "lemonBubbles",
    "rose", "seaBlueLine", "morandi", "cactus", "classic2", "classic3", "classic4",
    "classic5", "classic6", "classic7", "classic8", "classic9", "classic10",
    "classic11", "classic12", "classic13", "classic14", "classic15",
}

ICON_RANGES = {"priority": 10, "progress": 8, "expression": 20, "sign": 23}

NON_STYLE_KEYS = {
    "text", "image", "imageTitle", "imageSize", "icon", "tag", "hyperlink",
    "hyperlinkTitle", "note", "expand", "isActive", "generalization", "richText",
    "resetRichText", "uid", "activeStyle", "associativeLineTargets",
    "associativeLineTargetControlOffsets", "associativeLinePoint",
    "associativeLineText", "attachmentUrl", "attachmentName", "notation",
    "outerFrame", "number", "range", "customLeft", "customTop", "customTextWidth",
    "checkbox", "dir", "needUpdate", "imgMap", "nodeLink", "smmVersion",
}

errors = []
warnings = []


def err(path, msg):
    errors.append(f"{path}: {msg}")


def warn(path, msg):
    warnings.append(f"{path}: {msg}")


def check_icons(icons, path):
    if not isinstance(icons, list):
        err(path + ".icon", "必须是数组")
        return
    for i in icons:
        if not isinstance(i, str) or "_" not in i:
            warn(f"{path}.icon", f"{i!r} 不是 '<type>_<n>' 形式")
            continue
        t, _, n = i.partition("_")
        if t not in ICON_RANGES:
            warn(f"{path}.icon", f"未知图标类型 {t!r}（可用: {', '.join(ICON_RANGES)}）")
        elif not n.isdigit() or not (1 <= int(n) <= ICON_RANGES[t]):
            warn(f"{path}.icon", f"{i!r} 序号超出范围（{t} 为 1-{ICON_RANGES[t]}）")


def walk(node, path, uids, links):
    if not isinstance(node, dict):
        err(path, "节点必须是对象")
        return
    data = node.get("data")
    if not isinstance(data, dict):
        err(path, "缺少 data 对象")
        return
    if not isinstance(data.get("text"), str) or not data.get("text", "").strip():
        if not data.get("image"):
            warn(path + ".data.text", "文本为空且没有图片")

    uid = data.get("uid")
    if uid is not None:
        if not isinstance(uid, str):
            err(path + ".data.uid", "uid 必须是字符串")
        elif uid in uids:
            err(path + ".data.uid", f"uid {uid!r} 重复（首次出现于 {uids[uid]}）")
        else:
            uids[uid] = path

    if "icon" in data:
        check_icons(data["icon"], path + ".data")

    tag = data.get("tag")
    if tag is not None and not isinstance(tag, list):
        err(path + ".data.tag", "必须是数组")

    shape = data.get("shape")
    if shape is not None and shape not in SHAPES:
        warn(path + ".data.shape", f"未知形状 {shape!r}")

    if "expand" in data and not isinstance(data["expand"], bool):
        err(path + ".data.expand", "必须是布尔值")

    targets = data.get("associativeLineTargets")
    if targets is not None:
        if not isinstance(targets, list):
            err(path + ".data.associativeLineTargets", "必须是数组")
        else:
            if not uid:
                warn(path + ".data", "有关联线但本节点没有 uid")
            for t in targets:
                links.append((path, t))

    children = node.get("children", [])
    if not isinstance(children, list):
        err(path + ".children", "必须是数组")
        children = []

    gen = data.get("generalization")
    if gen is not None:
        items = gen if isinstance(gen, list) else [gen]
        for gi, g in enumerate(items):
            gpath = f"{path}.data.generalization[{gi}]"
            if not isinstance(g, dict):
                err(gpath, "概要项必须是对象")
                continue
            if not isinstance(g.get("text"), str):
                warn(gpath + ".text", "概要没有文本")
            rng = g.get("range")
            if rng is not None:
                if not (isinstance(rng, list) and len(rng) == 2 and all(isinstance(x, int) for x in rng)):
                    err(gpath + ".range", "必须是两个整数组成的数组")
                elif rng[0] > rng[1]:
                    err(gpath + ".range", f"起始索引 {rng[0]} 大于结束索引 {rng[1]}")
                elif rng[1] > len(children) - 1:
                    err(gpath + ".range", f"索引 {rng[1]} 越界（该节点有 {len(children)} 个子节点），该概要会被忽略")
            guid = g.get("uid")
            if isinstance(guid, str):
                if guid in uids:
                    err(gpath + ".uid", f"uid {guid!r} 重复")
                else:
                    uids[guid] = gpath

    unknown_style = [
        k for k in data
        if k not in NON_STYLE_KEYS and not k.startswith("_")
    ]
    for k in unknown_style:
        if k not in STYLE_KEYS:
            warn(path + ".data", f"{k!r} 不是已知字段，会被当作样式属性处理（自定义字段请加 _ 前缀）")

    for i, c in enumerate(children):
        walk(c, f"{path}.children[{i}]", uids, links)


STYLE_KEYS = {
    "shape", "fillColor", "color", "fontFamily", "fontSize", "fontWeight",
    "fontStyle", "textDecoration", "textAlign", "borderColor", "borderWidth",
    "borderDasharray", "borderRadius", "gradientStyle", "startColor", "endColor",
    "startDir", "endDir", "marginX", "marginY", "lineMarkerDir", "hoverRectColor",
    "hoverRectRadius", "imgPlacement", "tagPlacement", "paddingX", "paddingY",
    "lineWidth", "lineColor", "lineDasharray", "lineFlow", "lineFlowDuration",
    "lineFlowForward",
}


def main():
    p = argparse.ArgumentParser(description="校验 .smm 思维导图文件")
    p.add_argument("file")
    p.add_argument("--quiet", action="store_true", help="只输出错误，不输出警告")
    args = p.parse_args()

    try:
        with open(args.file, encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 — {e}")
        return 1
    except OSError as e:
        print(f"错误: 无法读取文件 — {e}")
        return 1

    if not isinstance(doc, dict):
        print("错误: 顶层必须是对象")
        return 1

    # 兼容只有节点树的文件
    if "root" in doc:
        root = doc["root"]
        layout = doc.get("layout")
        if layout is not None and layout not in LAYOUTS:
            err("layout", f"未知布局 {layout!r}")
        theme = doc.get("theme")
        if theme is not None:
            if not isinstance(theme, dict):
                err("theme", "必须是对象")
            else:
                tpl = theme.get("template")
                if tpl is not None and tpl not in THEMES:
                    warn("theme.template", f"未知主题 {tpl!r}（可能是扩展主题）")
                if "config" in theme and not isinstance(theme["config"], dict):
                    err("theme.config", "必须是对象")
    elif "data" in doc:
        root = doc
        warn("", "这是纯节点树文件（没有 layout/theme），导入时会沿用编辑器当前设置")
    else:
        print("错误: 顶层既没有 root 也没有 data，不是有效的 .smm 文件")
        return 1

    uids = {}
    links = []
    walk(root, "root", uids, links)

    for src, target in links:
        if target not in uids:
            err(f"{src}.data.associativeLineTargets", f"目标 uid {target!r} 在树中不存在，该关联线会被丢弃")

    if not args.quiet:
        for w in warnings:
            print(f"警告  {w}")
    for e in errors:
        print(f"错误  {e}")

    node_count = len(uids)
    if errors:
        print(f"\n校验失败：{len(errors)} 个错误，{len(warnings)} 个警告")
        return 1
    print(f"\n校验通过：{node_count} 个带 uid 的节点，{len(warnings)} 个警告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
