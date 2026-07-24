# .smm 文件结构完整参考

来源：simple-mind-map 源码（`index.js#getData`、`src/constants/constant.js`、`src/core/render/node/*`）。

## 顶层结构

`.smm` = JSON。导出时 `withConfig=true` 得到完整结构，`false` 时只有节点树（即直接是 `root` 那个对象）。**两种都能被导入**，但生成时一律用完整结构。

```jsonc
{
  "layout": "logicalStructure",   // 布局，见下
  "root": { "data": {}, "children": [] },  // 节点树，单个根对象
  "theme": {
    "template": "classic4",       // 主题名
    "config": {}                  // 覆盖主题的自定义配置，可为 {}
  },
  "view": {                       // 视图变换，可省略；省略则打开时自动居中
    "transform": {
      "scaleX": 1, "scaleY": 1, "shear": 0, "rotate": 0,
      "translateX": 0, "translateY": 0, "originX": 0, "originY": 0,
      "a": 1, "b": 0, "c": 0, "d": 1, "e": 0, "f": 0
    },
    "state": { "scale": 1, "x": 0, "y": 0, "sx": 0, "sy": 0 }
  },
  "config": {}                    // 保留字段，通常为 {}
}
```

导出的文件里 `root.data` 上还会带 `smmVersion`（库版本号字符串）。**生成时不需要写**，导入不校验它。

## 节点结构

```jsonc
{
  "data": { "text": "文字", "expand": true, "uid": "xxx" },
  "children": [ /* 同样结构，递归 */ ]
}
```

- 叶子节点写 `"children": []`。
- 没有独立的"节点类型"字段——根节点 / 二级 / 三级以下的样式差异由**深度**决定（主题里的 `root` / `second` / `node` 三组配置）。

## data 字段全表

### 内容类

| 字段 | 类型 | 说明 |
|---|---|---|
| `text` | string | 节点文字。`richText: true` 时是 HTML 片段 |
| `richText` | boolean | 文字是否为富文本。为 true 时 `text` 必须是 HTML |
| `resetRichText` | boolean | 重建富文本内容、丢弃原有内联样式 |
| `image` | string | 图片 URL 或 base64 data URI |
| `imageTitle` | string | 图片 title（悬浮提示） |
| `imageSize` | object | `{ width, height, custom }`，`custom: true` 表示用户手动调过尺寸 |
| `imgMap` | object | base64 图片映射表，配合 NodeBase64ImageStorage 插件 |
| `icon` | string[] | 内置图标 ID 数组，如 `["priority_1", "sign_4"]` |
| `tag` | array | 标签。旧格式 `["P0"]`；v0.10.3+ 支持对象形式 `[{ text: "P0", style: {...} }]`。style 可用字段：`fill`（背景色）、`fontSize`(12)、`radius`(3)、`height`(20)、`paddingX`(8)、`width`（设了就忽略 paddingX）。**标签文字颜色固定为白色，不可配**，所以 `fill` 必须用深色 |
| `hyperlink` | string | 超链接 URL |
| `hyperlinkTitle` | string | 超链接提示文字 |
| `note` | string | 备注，悬浮显示 |
| `attachmentUrl` / `attachmentName` | string | 附件（客户端功能） |
| `notation` | string | 数学公式（需 Formula 插件） |
| `nodeLink` | - | 节点双向链接（客户端功能） |
| `number` / `checkbox` | - | 编号 / 待办（客户端功能，开源库不渲染） |

### 状态类

| 字段 | 类型 | 说明 |
|---|---|---|
| `expand` | boolean | 是否展开子节点。**建议每个节点显式写 true** |
| `isActive` | boolean | 是否选中。生成时一律写 `false` 或省略 |
| `uid` | string | 节点唯一 ID。关联线 / 外框依赖它，必须全局唯一 |
| `dir` | string | 节点方向（`mindMap` 等左右布局中标记在左还是右），一般不手写 |
| `needUpdate` | boolean | 内部渲染标记，不要写 |
| `customLeft` / `customTop` | number | 自由节点的绝对坐标（拖拽后产生） |
| `customTextWidth` | number | 手动调整过的文本宽度 |
| `activeStyle` | object | 激活态样式覆盖 |

### 结构类

| 字段 | 类型 | 说明 |
|---|---|---|
| `generalization` | object 或 array | 概要节点，见下 |
| `associativeLineTargets` | string[] | 关联线目标节点的 uid 数组 |
| `associativeLinePoint` | array | 关联线起止点坐标，见下 |
| `associativeLineTargetControlOffsets` | array | 关联线控制点偏移 |
| `associativeLineText` | object | 关联线上的文字，`{ [targetUid]: "文字" }` |
| `outerFrame` | object | 外框样式，见下 |
| `range` | array | 概要覆盖的子节点索引范围（写在 generalization 项里） |

### 样式类

**规则**：`data` 中任何**不在上面三张表里**、且**不以 `_` 开头**的键，都被判定为样式属性，直接覆盖主题对该节点的设置。可用的样式键就是主题里 `root`/`second`/`node` 三组的全部字段（`fillColor`、`color`、`fontSize`、`fontWeight`、`fontStyle`、`fontFamily`、`borderColor`、`borderWidth`、`borderRadius`、`borderDasharray`、`shape`、`textAlign`、`textDecoration`、`gradientStyle`、`startColor`、`endColor`、`paddingX`、`paddingY`、`lineColor`、`lineWidth`、`lineDasharray`、`imgPlacement`、`tagPlacement` 等），详见 `styles.md`。

自定义业务字段务必加 `_` 前缀（如 `_sourceId`），否则会被当样式处理。

## 概要（generalization）

给一个节点的部分或全部子节点加一个"小结"。写在**父节点**的 data 上。

```jsonc
"generalization": [
  {
    "text": "以上三点是前提",
    "range": [0, 2],        // 覆盖 children 索引 0..2（闭区间）；省略/null = 覆盖该节点本身
    "expand": true,
    "uid": "g1"
    // 也可带任意样式字段
  }
]
```

- 单个概要可以直接写成对象（不套数组），库内部会归一化。多个概要必须用数组。
- `range` 的两个索引都必须 `<= children.length - 1`，否则该概要被忽略。
- 概要节点自己也可以有 `children`。
- 概要节点的默认样式来自主题的 `generalization` 组。

## 关联线（associativeLine）

从 A 节点拉一条线指向 B 节点。写在**起点节点**上，需要 AssociativeLine 插件（web 版默认已注册）。

```jsonc
{
  "data": {
    "text": "A", "uid": "uid-a",
    "associativeLineTargets": ["uid-b"],
    "associativeLineText": { "uid-b": "触发" },
    "associativeLinePoint": [
      { "startPoint": { "x": 0, "y": 0 }, "endPoint": { "x": 0, "y": 0 } }
    ],
    "associativeLineTargetControlOffsets": [
      { "startOffset": { "x": 0, "y": 0 }, "endOffset": { "x": 0, "y": 0 } }
    ]
  }
}
```

**最省事的写法**：只写 `associativeLineTargets`，坐标数组全部省略，库会自动计算起止点和控制点。想加文字就补 `associativeLineText`。

目标 uid 必须真实存在于树中，否则那条线被静默丢弃。

## 外框（outerFrame）

把**若干个相邻的兄弟节点**（连同各自子树）圈进一个框，需要 OuterFrame 插件。

**关键**：外框不是写在一个节点上的，而是**范围内每个兄弟节点都要写一份相同的 `outerFrame`，并共享同一个 `groupId`**。库靠 `groupId` 把它们识别成同一个框。只圈一个节点时也一样要有 `groupId`。根节点和概要节点不能加外框。

```jsonc
// 例：把父节点的 children[0] 和 children[1] 圈在一起
// 这两个节点的 data 里都要有完全相同的下面这段
"outerFrame": {
  "groupId": "frame-1",            // 必填，同一个框内所有节点相同
  "text": "第一阶段",               // 框上的标题，可省略
  "radius": 5,
  "strokeWidth": 2,
  "strokeColor": "#f56c6c",
  "strokeDasharray": "5,5",        // "none" 为实线
  "fill": "rgba(245,108,108,0.06)",
  "fontSize": 14,
  "fontFamily": "微软雅黑, Microsoft YaHei",
  "fontWeight": "normal",
  "fontStyle": "normal",
  "color": "#fff",                 // 标题文字颜色
  "lineHeight": 1.2,
  "textFill": "#f56c6c",           // 标题背景色
  "textFillRadius": 5,
  "textFillPadding": [5, 5, 5, 5], // 左上右下
  "textAlign": "left"              // left / center / right
}
```

## 布局取值（layout）

| 值 | 说明 |
|---|---|
| `logicalStructure` | 逻辑结构图（向右）**默认** |
| `logicalStructureLeft` | 逻辑结构图（向左） |
| `mindMap` | 思维导图（左右对称） |
| `organizationStructure` | 组织结构图（自上而下） |
| `catalogOrganization` | 目录组织图 |
| `timeline` / `timeline2` | 水平时间轴 |
| `verticalTimeline` / `verticalTimeline2` / `verticalTimeline3` | 垂直时间轴 |
| `fishbone` / `fishbone2` | 鱼骨图 |
| `rightFishbone` / `rightFishbone2` | 右向鱼骨图 |

注意：部分连线样式只在特定布局下生效（如 `lineStyle: "curve"` 仅支持 `logicalStructure`/`mindMap`/`verticalTimeline`）。

## 版本兼容

- 旧文件的 `tag` 是字符串数组，新版兼容；生成时用对象数组可带样式。
- 顶层没有 `theme`/`layout` 的纯节点树文件也能导入，会用当前编辑器的主题布局。
- `smmVersion` 只是记录，不影响导入。
