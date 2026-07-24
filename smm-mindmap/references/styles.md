# 主题与样式参考

## 内置主题（theme.template）

`default` 由核心库提供；其余来自 `simple-mind-map-plugin-themes`，web 版和客户端默认全部内置。

### 浅色

`skyGreen` `classicGreen` `classicBlue` `blueSky` `brainImpairedPink` `earthYellow`
`freshGreen` `freshRed` `romanticPurple` `pinkGrape` `mint` `gold` `vitalityOrange`
`greenLeaf` `minions` `simpleBlack` `courseGreen` `coffee` `redSpirit` `avocado`
`autumn` `oreo` `shallowSea` `lemonBubbles` `rose` `seaBlueLine` `morandi` `cactus`
`classic2` `classic3` `classic4` `classic5` `classic6` `classic7` `classic8` `classic9`
`classic10` `classic11` `classic12` `classic13` `classic14` `classic15`

### 深色

`classic`（注意：无数字后缀的 `classic` 属于深色组）`blackHumour` `lateNightOffice`
`blackGold` `orangeJuice` `neonLamp` `darkNightLceBlade`
`dark` `dark2` `dark3` `dark4` `dark5` `dark6` `dark7`

### 极简（web 版归为"简约"分组，均为浅色）

`default` `skyGreen` `classic2` `classic3` `classicGreen` `classicBlue` `blueSky`
`brainImpairedPink` `earthYellow` `freshGreen` `freshRed` `romanticPurple` `pinkGrape` `mint`

### 选型建议

| 场景 | 推荐 |
|---|---|
| 通用 / 不确定 | `classic4` |
| 商务汇报 | `classicBlue`、`simpleBlack`、`morandi` |
| 深色演示 / 夜间 | `dark`、`blackGold`、`lateNightOffice` |
| 学习笔记 | `freshGreen`、`courseGreen`、`avocado` |
| 活泼 / 头脑风暴 | `vitalityOrange`、`minions`、`lemonBubbles` |

## theme.config 全局配置项

所有字段可选，写进 `theme.config` 即覆盖所选主题。取值示例是 `default` 主题的默认值。

### 画布 / 背景

| 字段 | 默认 | 说明 |
|---|---|---|
| `backgroundColor` | `#fafafa` | 背景色 |
| `backgroundImage` | `none` | 背景图 URL |
| `backgroundRepeat` | `no-repeat` | |
| `backgroundPosition` | `center center` | |
| `backgroundSize` | `cover` | |

### 节点通用

| 字段 | 默认 | 说明 |
|---|---|---|
| `paddingX` / `paddingY` | 15 / 5 | 节点内边距 |
| `imgMaxWidth` / `imgMaxHeight` | 200 / 100 | 图片最大显示尺寸 |
| `iconSize` | 20 | 图标尺寸 |
| `nodeUseLineStyle` | false | 节点改为"只有底边横线"的样式，仅支持 `logicalStructure`/`mindMap`/`catalogOrganization`/`organizationStructure` |

### 连线

| 字段 | 默认 | 说明 |
|---|---|---|
| `lineWidth` | 1 | 粗细 |
| `lineColor` | `#549688` | 颜色 |
| `lineDasharray` | `none` | 虚线，如 `"6,4"` |
| `lineStyle` | `straight` | `curve`（曲线）/ `straight`（直线）/ `direct`（直连）。`curve` 仅支持 `logicalStructure`/`mindMap`/`verticalTimeline`；`direct` 另外还支持 `organizationStructure` |
| `lineRadius` | 5 | 直线连接时的圆角，0 为直角 |
| `showLineMarker` | false | 显示箭头 |
| `rootLineKeepSameInCurve` | true | 曲线模式下根节点连线与其他节点保持一致 |
| `rootLineStartPositionKeepSameInCurve` | false | 根节点连线起点也放在节点侧边 |
| `lineFlow` | false | 虚线流动动画（需 LineFlow 插件） |
| `lineFlowDuration` | 1 | 流动周期（秒） |
| `lineFlowForward` | true | 流动方向父→子 |

### 概要连线

`generalizationLineWidth`(1) `generalizationLineColor`(`#549688`) `generalizationLineMargin`(0) `generalizationNodeMargin`(20)

### 关联线

`associativeLineWidth`(2) `associativeLineColor`(`rgb(51,51,51)`)
`associativeLineActiveWidth`(8) `associativeLineActiveColor`(`rgba(2,167,240,1)`)
`associativeLineDasharray`(`6,4`)
`associativeLineTextColor`(`rgb(51,51,51)`) `associativeLineTextFontSize`(14)
`associativeLineTextLineHeight`(1.2) `associativeLineTextFontFamily`

## 节点分组样式

`theme.config` 里有四个分组对象，分别对应不同深度的节点：

| 分组 | 作用范围 |
|---|---|
| `root` | 根节点 |
| `second` | 二级节点 |
| `node` | 三级及以下 |
| `generalization` | 概要节点 |

每组支持的字段（也可以直接写在某个节点的 `data` 上，只影响该节点）：

| 字段 | 说明 |
|---|---|
| `shape` | 节点形状，见下 |
| `fillColor` | 填充色 |
| `color` | 文字颜色 |
| `fontFamily` | 字体，默认 `微软雅黑, Microsoft YaHei` |
| `fontSize` | 字号（root 16 / second 16 / node 14） |
| `fontWeight` | `normal` / `bold` |
| `fontStyle` | `normal` / `italic` |
| `textDecoration` | `none` / `underline` / `line-through` |
| `textAlign` | `left` / `center` / `right` / `justify` |
| `borderColor` | 边框色 |
| `borderWidth` | 边框粗细 |
| `borderDasharray` | 边框虚线 |
| `borderRadius` | 圆角 |
| `gradientStyle` | true 时启用渐变填充 |
| `startColor` / `endColor` | 渐变起止色 |
| `startDir` / `endDir` | 渐变方向，如 `[0,0]` → `[1,0]` |
| `marginX` / `marginY` | 与兄弟/父节点的间距（`second` 100/40，`node` 50/0；`root` 无） |
| `lineMarkerDir` | 箭头位置 `start` / `end`（需 `showLineMarker`） |
| `hoverRectColor` / `hoverRectRadius` | hover 边框颜色 / 圆角 |
| `imgPlacement` | 图片位置 `top`/`bottom`/`left`/`right` |
| `tagPlacement` | 标签位置 `right`（文字右侧）/ `bottom`（内容下方） |
| `paddingX` / `paddingY` | 覆盖全局内边距 |
| `lineWidth` / `lineColor` / `lineDasharray` / `lineFlow` 等 | 覆盖该节点出边的连线样式 |

### 示例：加粗根节点 + 二级节点圆角胶囊

```json
"theme": {
  "template": "classic4",
  "config": {
    "lineWidth": 2,
    "lineStyle": "curve",
    "root": { "fontSize": 22, "fillColor": "#2c3e50", "color": "#fff" },
    "second": { "shape": "roundedRectangle", "borderWidth": 2, "paddingX": 18 }
  }
}
```

## 节点形状（shape）

`rectangle`（矩形，默认）`roundedRectangle`（圆角矩形）`ellipse`（椭圆）`circle`（圆）
`diamond`（菱形）`parallelogram`（平行四边形）`octagonalRectangle`（八角矩形）
`outerTriangularRectangle`（外三角矩形）`innerTriangularRectangle`（内三角矩形）

## 内置图标（data.icon）

格式 `"<type>_<序号>"`，序号从 1 开始：

| type | 范围 | 含义 |
|---|---|---|
| `priority` | 1–10 | 优先级（数字徽标 1~10） |
| `progress` | 1–8 | 进度（空 → 1/8 → … → 满） |
| `expression` | 1–20 | 表情 |
| `sign` | 1–23 | 标记（对勾、叉、星、旗、问号等） |

例：`"icon": ["priority_1", "progress_8", "sign_1"]`

超出范围的名字不报错，但不会渲染出任何图标。自定义图标需要通过实例化选项 `iconList` 注册，`.smm` 文件本身带不了。

## 布局取值

见 `schema.md` 的"布局取值"表。
