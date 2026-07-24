---
name: smm-mindmap
description: 生成思绪思维导图（simple-mind-map）的 .smm / .json 文件，支持节点树、主题、布局、样式、图标、标签、备注、概要、关联线、外框等。当用户要求"生成思维导图""做一张脑图""导出 smm 文件""mind map""导入到思绪思维导图/sxmind"时使用。
---

# SMM 思维导图生成

把文本内容转换成 `.smm` 文件（思绪思维导图 / simple-mind-map 的原生格式），可直接被 [web.sxmind.cn](https://web.sxmind.cn/)、客户端或任何嵌入 simple-mind-map 库的应用导入。

`.smm` 本质就是 **UTF-8 的 JSON 文本**，扩展名不同而已。同一份内容存成 `.json` 也能导入。

## 工作流程

1. **理解内容层级** —— 先把用户素材整理成一棵树：一个根节点 + 多层子节点。层级控制在 4~5 层以内，单个节点文本尽量 ≤ 20 字。
2. **选布局和主题** —— 见下面"快速决策"。用户没说就用默认推荐。
3. **生成文件** —— 两种方式：
   - **推荐**：写一份带内联标注的 Markdown 大纲，用 `scripts/outline_to_smm.py` 转换。快、不易出错。
   - **手写 JSON**：需要关联线、概要 range、外框、渐变等复杂结构时，直接构造 JSON（参考 `references/schema.md`）。
4. **校验** —— 一律跑 `scripts/validate_smm.py` 确认结构合法、uid 唯一、关联线指向存在。
5. **交付** —— 告诉用户文件路径和导入方式（web 版：左侧「导入」→ 选择 `.smm` 文件）。

## 快速决策

**布局**（`layout` 字段）：

| 内容形态 | 用 |
|---|---|
| 通用、条目多、层级深（默认） | `logicalStructure` 逻辑结构图（右侧展开） |
| 分支均衡、想要经典脑图观感 | `mindMap` 思维导图（左右对称） |
| 组织架构、自上而下的分解 | `organizationStructure` |
| 目录、章节大纲 | `catalogOrganization` |
| 时间顺序、流程步骤 | `timeline` / `verticalTimeline` |
| 因果分析、问题归因 | `fishbone` |

**主题**（`theme.template`）：不确定时用 `classic4`（浅色、干净）。深色场景用 `dark`。完整清单见 `references/styles.md`。

## 最小可用文件

```json
{
  "layout": "logicalStructure",
  "theme": { "template": "classic4", "config": {} },
  "root": {
    "data": { "text": "根节点", "expand": true, "uid": "root" },
    "children": [
      { "data": { "text": "分支一", "expand": true, "uid": "n1" }, "children": [] }
    ]
  }
}
```

三个要点：
- `root` 是**单个对象**，不是数组；每个节点都是 `{ data: {...}, children: [...] }`。
- `data.text` 必填；`expand: true` 建议每个节点都写，否则默认折叠行为依赖实现。
- `uid` 只要用到关联线 / 外框就必须有且全局唯一；平时写上也无害。

## 大纲转换（推荐路径）

写一份 Markdown，标题层级和列表缩进共同决定树结构（`#` 是根，列表项挂在最近的标题下）：

```markdown
# 项目复盘

## 做得好的
- 需求评审前置 {icon:priority_1}
- 自动化测试覆盖到 80% {tag:已完成}

## 待改进
- 联调排期太晚 {icon:sign_4, note:下个迭代提前一周}
  - 责任人：张三
- 文档滞后 {fill:#ffe0e0, color:#c00}
```

转换：

```bash
python3 ~/.claude/skills/smm-mindmap/scripts/outline_to_smm.py outline.md -o 复盘.smm \
  --theme classic4 --layout logicalStructure
```

**内联标注**写在行尾的 `{...}` 里，逗号分隔 `key:value`：

| 标注 | 作用 | 示例 |
|---|---|---|
| `icon` | 内置图标，多个用 `\|` 分隔 | `{icon:priority_1\|sign_4}` |
| `tag` | 标签，多个用 `\|` 分隔 | `{tag:P0\|后端}` |
| `note` | 备注（悬浮显示） | `{note:见需求文档第3节}` |
| `link` | 超链接 | `{link:https://example.com}` |
| `image` | 图片 URL | `{image:https://../a.png}` |
| `fill` | 填充色 | `{fill:#e8f5e9}` |
| `color` | 文字颜色 | `{color:#c62828}` |
| `border` | 边框色 | `{border:#4caf50}` |
| `size` | 字号 | `{size:18}` |
| `bold` | 加粗 | `{bold:true}` |
| `shape` | 节点形状 | `{shape:roundedRectangle}` |
| `collapse` | 该节点默认折叠 | `{collapse:true}` |
| `summary` | 给该节点加一个概要节点 | `{summary:小结文字}` |

值里如果要用逗号或 `}`，用反斜杠转义：`{note:先做 A\, 再做 B}`。

跑 `python3 scripts/outline_to_smm.py --help` 看全部参数（`--no-uid`、`--minify`、`--config` 注入自定义主题等）。

## 校验

```bash
python3 ~/.claude/skills/smm-mindmap/scripts/validate_smm.py 复盘.smm
```

会检查：JSON 合法性、`root` 结构、`data.text` 存在、uid 唯一、`associativeLineTargets` 指向的 uid 存在、`generalization.range` 索引越界、主题/布局/形状/图标名是否为已知值。未知主题名只警告不报错（用户可能装了扩展主题）。

## 样式怎么加

三个层次，**从上往下优先级递增**：

1. `theme.template` —— 选一个内置主题，管全局配色。
2. `theme.config` —— 覆盖主题的部分字段，如 `{ "lineWidth": 2, "root": { "fillColor": "#333" } }`。作用于全图。
3. 节点 `data` 里的样式字段 —— 只影响该节点，如 `fillColor`、`color`、`fontSize`、`borderColor`、`shape`。

**关键规则**：节点 `data` 里，凡是不在"非样式字段白名单"（`text`/`icon`/`tag`/`note`/`expand`/`uid`/`image` 等，完整列表见 `references/schema.md`）中、且不以 `_` 开头的键，都会被当作样式属性直接应用。所以别在 `data` 里塞自定义业务字段，要塞就加 `_` 前缀。

配色建议：同一层级的兄弟节点保持同色系；用颜色区分「状态/优先级」而不是随机上色；深色主题下不要硬编码深色文字。

## 参考文档

- `references/schema.md` —— 完整字段表：顶层结构、节点 data 全部字段、概要 / 关联线 / 外框 / 富文本的数据形态、版本兼容注意事项。**要用关联线、概要 range、外框、图片、富文本时先读它。**
- `references/styles.md` —— 全部内置主题名（含深浅色分组）、主题配置项全表、节点形状、内置图标 ID、布局取值。**用户指定主题/配色/图标时先读它。**
