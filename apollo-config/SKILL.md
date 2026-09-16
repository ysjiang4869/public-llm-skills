---
name: apollo-config
description: "Manage Apollo (ApolloConfig) via the Portal Open API: list namespaces, query, edit and release configs, distinguish draft vs published state, with preview, confirmation and post-release checks before external writes. 中文：查询/修改/发布 Apollo 配置，区分编辑态与已发布态；当用户要求查询 Apollo 配置、修改配置项、查看待发布差异或发布 Namespace 时使用。"
---

# Apollo 配置管理

通过 Apollo Portal 的正式 Open API 管理配置。不要模拟 Portal 登录，也不要直接调用内部 AdminService。

本技能当前以 Apollo 2.2.x 的 Consumer Token 接口为兼容基线。详细接口和 Token 创建方式见 [references/apollo-2.2-openapi.md](references/apollo-2.2-openapi.md)。

## 安全边界

- Token 只能从环境变量 `APOLLO_OPENAPI_TOKEN` 读取。不要让用户把 Token 发到对话中，不要把它写入仓库、配置文件、命令参数或日志。
- Portal 地址允许使用 HTTP 或 HTTPS，包括经过来源 IP 限制的公网 HTTP 地址。HTTP 会明文传输 Consumer Token；仅在网络边界可信且访问范围已受控时使用，条件允许时仍优先使用 HTTPS、`kubectl port-forward` 或 SSH 隧道。
- 查询是只读操作，可以直接执行。
- 修改和发布是两个独立写操作。每个操作都必须先运行不带 `--apply` 的预览，向用户展示目标与 diff，取得明确确认后才能加 `--apply`。
- 发布前重新查询待发布差异和 Namespace 锁。发现目标、锁或配置内容变化时停止，不沿用旧确认。
- 不把完整 Namespace 值默认打印出来。列表和 diff 默认只显示 key 与值摘要；只有用户明确要求查看值时才使用 `--show-values`。
- 用户在对话中明确给出普通配置值时，可以通过 `set --value` 传入。该值会出现在命令参数和工具记录中；敏感值仍使用 `--value-stdin`、`--value-env` 或 `--value-file`，不要在对话中回显。
- 非 properties Namespace 的配置 key 固定为 `content`，Namespace 名需带 `.json`、`.yml`、`.yaml` 或 `.xml` 后缀。

## 连接参数

脚本优先使用命令行参数，其次使用环境变量：

| 参数 | 环境变量 | 说明 |
|---|---|---|
| `--portal-url` | `APOLLO_PORTAL_URL` | HTTP 或 HTTPS Portal 地址 |
| `--app` | `APOLLO_APP_ID` | 被管理应用的 AppId |
| `--env` | `APOLLO_ENV` | 环境，如 `DEV`、`FAT`、`UAT`、`PRO` |
| `--cluster` | `APOLLO_CLUSTER` | 集群，默认 `default` |
| `--namespace` | `APOLLO_NAMESPACE` | Namespace，默认 `application` |
| `--operator` | `APOLLO_OPERATOR` | Portal 用户名，写操作必需 |
| `--ca-file` | `APOLLO_CA_FILE` | 自签 HTTPS 的 CA 文件；不要用跳过证书校验替代 |

所有全局参数放在子命令之前。

## 工作流

### 1. 检查连接和权限

```bash
python3 scripts/apollo_config.py \
  --portal-url "$APOLLO_PORTAL_URL" \
  --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" \
  doctor
```

`doctor` 只执行读取，确认 Token 能看到目标 App、环境、Namespace 和锁信息。

### 2. 查询配置

列出目标 App、环境和集群下的 Namespace：

```bash
python3 scripts/apollo_config.py --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" namespaces
```

输出包含 Namespace 名称、格式、是否公共、配置项数量和 key 列表，但不包含配置值。

查询编辑态单个 key：

```bash
python3 scripts/apollo_config.py --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" \
  get timeout
```

查询已发布值：

```bash
python3 scripts/apollo_config.py --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" \
  get timeout --view published
```

列出配置或查看待发布差异：

```bash
python3 scripts/apollo_config.py --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" list
python3 scripts/apollo_config.py --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" diff
```

只有用户明确要求值时，才在 `list`、`diff` 或 `get` 后增加 `--show-values`。

### 3. 修改配置

对于用户在对话中明确给出的普通值，可以直接通过命令行传入。先预览：

```bash
python3 scripts/apollo_config.py \
  --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" --operator "$APOLLO_OPERATOR" \
  set timeout --value '3000' --comment "调整超时时间"
```

空字符串使用 `--value ''`。如果值属于密码、密钥、Token 等敏感信息，或包含复杂换行和 shell 特殊字符，改用 `--value-stdin`、`--value-env` 或 `--value-file`。

确认预览目标和摘要后，以完全相同的参数增加 `--apply`。执行后脚本会读回编辑态值进行校验。修改成功不等于已经发布。

### 4. 发布 Namespace

先预览：

```bash
python3 scripts/apollo_config.py \
  --app "$APOLLO_APP_ID" --env "$APOLLO_ENV" --operator "$APOLLO_OPERATOR" \
  publish --title "change-timeout" --comment "调整超时时间"
```

预览会显示新增、修改、删除数量、key 摘要和 Namespace 锁。用户确认后增加 `--apply`。发布成功后脚本会重新读取 `releases/latest`，核对 Release。

若 diff 为空，脚本返回 no-op，不创建空发布。

## 输出与错误

脚本输出 JSON，便于 Agent 精确读取。发生 `401` 时检查 Token；`403` 表示 Consumer 未获得目标 App/环境/Namespace 的权限；`404` 通常表示目标或发布不存在。不要通过扩大 Token 到 AppRole 来绕过定位错误，优先补充精确 NamespaceRole。
