# Apollo 2.2 Open API 参考

## Token 创建与授权

Apollo 2.2.0 没有面向个人的 `apollo_pat_` 用户 Token，使用开放平台 Consumer Token。

管理员在 Portal 中操作：

1. 打开 `/open/manage.html`。
2. 点击“创建第三方应用”，进入 `/open/add-consumer.html`。
3. 填写第三方 AppId、名称、部门和负责人。“允许创建应用”保持关闭，除非集成确实需要创建 Apollo App。
4. 创建后页面显示 Consumer Token。Token 是持久敏感凭据，不要发送到对话或提交到代码仓库。
5. 在“查看 Token 并赋权”中选择 `NamespaceRole`，填写被管理的 AppId、Namespace 和环境。
6. 只有需要管理整个应用时才授予 `AppRole`；普通配置查询、修改和发布使用最小范围的 `NamespaceRole`。

前端对应的 Portal 接口是 `/consumers`、`/consumer-tokens/by-appId` 和 `/consumers/{token}/assign-role`。这些是管理员登录态 WebAPI，仅用于 Portal 页面本身；技能运行时使用下方 `/openapi/v1/*`，不能拿登录 Cookie 模拟管理操作。

Consumer Token 请求头：

```text
Authorization: <consumer-token>
Content-Type: application/json;charset=UTF-8
```

## 管理接口

公共前缀：`{portalUrl}/openapi/v1`。

| 功能 | 方法与路径 |
|---|---|
| App 环境/集群 | `GET /apps/{appId}/envclusters` |
| 集群 Namespace 列表 | `GET /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces` |
| Namespace 编辑态 | `GET /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}` |
| Namespace 锁 | `GET /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}/lock` |
| 单个编辑态配置 | `GET /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}/items/{key}` |
| 分页配置列表 | `GET /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}/items?page={page}&size={size}` |
| 新增/修改配置 | `PUT /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}/items/{key}?createIfNotExists=true` |
| 发布 | `POST /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}/releases` |
| 最新已发布快照 | `GET /envs/{env}/apps/{appId}/clusters/{cluster}/namespaces/{namespace}/releases/latest` |

分页配置列表从 Apollo 2.1.0 起可用，2.2.0 可以直接使用。

更新配置请求体：

```json
{
  "key": "timeout",
  "value": "3000",
  "comment": "调整超时时间",
  "dataChangeLastModifiedBy": "operator",
  "dataChangeCreatedBy": "operator"
}
```

发布请求体：

```json
{
  "releaseTitle": "change-timeout",
  "releaseComment": "调整超时时间",
  "releasedBy": "operator"
}
```

## 状态语义

- `items` 和 Namespace 查询得到的是当前编辑态，可能含未发布修改。
- `releases/latest` 是当前已发布快照。
- 编辑态与已发布快照的差异就是待发布内容。
- Open API 发布成功只证明 Portal 创建了 Release。要证明具体应用实例已获取配置，还需从能访问 ConfigService 的网络位置调用客户端接口，并带上实际 `appId`、cluster、Namespace、IP/label 及可能的 AccessKey 签名。

## K8s 推荐访问方式

公网 HTTP Portal 不适合携带 Token。优先在本机建立端口转发：

```bash
kubectl -n <namespace> get svc
kubectl -n <namespace> port-forward svc/<apollo-portal-service> 18070:<portal-service-port>
```

另一个终端使用：

```bash
export APOLLO_PORTAL_URL=http://127.0.0.1:18070
read -s "APOLLO_OPENAPI_TOKEN?Apollo OpenAPI token: "
export APOLLO_OPENAPI_TOKEN
```

也可以在集群内的受控运维容器执行脚本。不要把 ConfigService 或 AdminService 直接暴露到公网。
