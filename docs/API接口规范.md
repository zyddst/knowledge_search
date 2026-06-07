# API 接口规范

## 通用约定

- 基础 URL: `https://api.company.com/v1`
- 认证方式: Header `Authorization: Bearer <token>`
- Content-Type: `application/json`
- 所有时间使用 ISO 8601 格式: `2026-06-06T10:30:00+08:00`

## 分页

列表接口统一使用游标分页：

```
GET /v1/users?limit=20&cursor=eyJpZCI6MTIzfQ==
```

响应:
```json
{
  "data": [...],
  "next_cursor": "eyJpZCI6MTQzfQ==",
  "has_more": true
}
```

## 错误码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |

错误响应体:
```json
{
  "error": {
    "code": "INVALID_PARAM",
    "message": "email 格式不正确",
    "detail": "email field must be a valid email address"
  }
}
```

## 用户模块

### 获取当前用户信息

```
GET /v1/users/me
```

### 更新用户信息

```
PATCH /v1/users/me
{
  "name": "新名字",
  "avatar_url": "https://example.com/avatar.jpg"
}
```
