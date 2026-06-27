# Backend 协作说明

FastAPI 后端，默认端口 `9000`。前端请求封装见 `ainame/http/http.js`。

## 改动

改动记录见项目根目录 [README.md 改动章节](../README.md#改动)。

---

## 接口文档

**Base URL**

```text
http://127.0.0.1:9000
```

**鉴权约定**

| 方式 | Header | 适用场景 |
| --- | --- | --- |
| 登录 Token | `Authorization: Bearer {token}` | 大部分用户 / 管理员接口 |
| API Key | `X-API-Key: {key}` | 外部调用 `/name/npc`、`/name/novel-character`、`/name/place`、`/name/generate` |
| 无需登录 | 无 | 注册、登录、获取邮箱验证码 |

**通用响应**

- 成功：HTTP `200`，返回 JSON
- 失败：HTTP `4xx/5xx`，`detail` 为字符串或校验错误数组

---

### 1. 认证 `/auth`

| 方法 | 路径 | 鉴权 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| GET | `/auth/code?email={email}` | 否 | 发送 4 位邮箱验证码 | `getEmailCode` |
| POST | `/auth/register` | 否 | 用户注册 | `register` |
| POST | `/auth/login` | 否 | 用户登录，返回 token 和 user | `login` |

**POST `/auth/register` 请求体**

```json
{
  "username": "testuser",
  "email": "user@qq.com",
  "code": "1234",
  "password": "111111",
  "confirm_password": "111111",
  "invite_code": "可选，邀请码"
}
```

**POST `/auth/login` 请求体**

```json
{
  "email": "user@qq.com",
  "password": "111111"
}
```

**POST `/auth/login` 响应示例**

```json
{
  "token": "jwt-token",
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@qq.com",
    "role": "user",
    "credits": 0
  }
}
```

---

### 2. 起名 `/name`

| 方法 | 路径 | 鉴权 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| POST | `/name/generate` | Token 或 API Key | 首次生成名字（uni-app 主流程） | `generateName` |
| POST | `/name/get_names` | Token | 生成名字（旧接口） | — |
| POST | `/name/feedback` | Token | 基于 thread_id 微调重生成 | `feedbackName` |
| POST | `/name/npc` | Token 或 API Key | NPC 起名，扣 API Key 额度 | dashboard 示例 |
| POST | `/name/novel-character` | Token 或 API Key | 小说角色起名 | dashboard 示例 |
| POST | `/name/place` | Token 或 API Key | 地名起名 | dashboard 示例 |

**POST `/name/generate` / `/name/npc` / `/name/novel-character` / `/name/place` 请求体**

```json
{
  "category": "人名",
  "surname": "张",
  "gender": "不限",
  "length": "两字",
  "style": "国风",
  "brand_tone": "",
  "other": "核心诉求",
  "exclude": []
}
```

说明：

- `category` 可选：`人名`、`企业名`、`宠物名`、`NPC`、`小说角色`、`地名`
- 访问 `/name/npc` 等专用路径时，后端会自动覆盖 `category`
- 使用 API Key 时，每次成功调用默认消耗 1 次额度

**POST `/name/feedback` 请求体**

```json
{
  "thread_id": "会话线程 ID",
  "category": "人名",
  "feedback": "保留第二个，其余换成带水字旁的"
}
```

---

### 3. 知识库 `/knowledge`

| 方法 | 路径 | 鉴权 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| POST | `/knowledge/upload` | Token | 上传 TXT/PDF，multipart 字段名 `file` | `uploadKnowledge` |

---

### 4. 企业视觉 `/visual`

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/visual/generate` | Token | 企业 slogan / logo 占位生成 |

**请求体**

```json
{
  "name": "企业名",
  "moral": "寓意",
  "brand_tone": "品牌调性",
  "other": "补充要求"
}
```

---

### 5. 邀请 credits `/invitation`

| 方法 | 路径 | 鉴权 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| GET | `/invitation/me` | Token | 邀请码、链接、人数、credits、奖励记录 | `getInvitationSummary` |

**响应字段**

- `invite_code`：我的邀请码
- `invite_link`：邀请注册链接（默认 uni-app 注册页 hash 路由）
- `invite_count`：已邀请人数
- `credits`：当前 credits
- `rewards`：奖励记录列表

邀请规则：邀请人 +10 credits，被邀请人 +5 credits。

---

### 6. API Key `/api-key`

| 方法 | 路径 | 鉴权 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| POST | `/api-key/create` | Token | 创建 Key，默认 10 次额度 | `createApiKey` |
| GET | `/api-key/list` | Token | 我的 Key 列表 | `getApiKeys` |
| POST | `/api-key/disable` | Token | 禁用 Key | `disableApiKey` |
| POST | `/api-key/enable` | Token | 启用 Key | `enableApiKey` |
| POST | `/api-key/delete` | Token | 删除 Key（软删） | `deleteApiKey` |
| GET | `/api-key/stats` | Token | 今日/剩余/总调用统计 | `getApiKeyStats` |
| GET | `/api-key/usage?page=1&page_size=20` | Token | 调用记录分页 | `getApiKeyUsage` |

**POST `/api-key/create` 请求体**

```json
{
  "name": "我的测试 Key"
}
```

**POST `/api-key/disable` / `/enable` / `/delete` 请求体**

```json
{
  "key_id": 1
}
```

---

### 7. 社区投票 `/community`

| 方法 | 路径 | 鉴权 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| POST | `/community/polls` | Token | 发布起名投票 | `createCommunityPoll` |
| GET | `/community/polls?page=1&page_size=20` | Token | 社区投票列表 | `getCommunityPolls` |
| POST | `/community/polls/{poll_id}/vote` | Token | 投票 / 切换选项 | `voteCommunityPoll` |
| GET | `/community/admin/polls?page=1&page_size=20` | 管理员 | 管理端查看全部投票 | `getAdminCommunityPolls` |
| POST | `/community/admin/polls/{poll_id}/hide` | 管理员 | 隐藏投票，必填理由 | `hideCommunityPoll` |
| POST | `/community/admin/polls/{poll_id}/unhide` | 管理员 | 取消隐藏 | `unhideCommunityPoll` |

**POST `/community/polls` 请求体**

```json
{
  "naming_type": "人名",
  "candidate_names": [
    {
      "name": "示例名",
      "reference": "出处",
      "moral": "寓意",
      "style_reason": "风格理由",
      "score": 90,
      "domains": []
    }
  ],
  "ai_analysis": "AI 分析"
}
```

**POST `/community/polls/{poll_id}/vote` 请求体**

```json
{
  "option_id": 1
}
```

**POST `/community/admin/polls/{poll_id}/hide` 请求体**

```json
{
  "reason": "隐藏理由"
}
```

---

### 8. 管理员 `/admin`

所有接口均需管理员 Token（`admin` / `super_admin`）。部分接口仅 `super_admin` 可用。

| 方法 | 路径 | 权限 | 说明 | 前端方法 |
| --- | --- | --- | --- | --- |
| GET | `/admin/users?page=1&page_size=20&keyword=&user_segment=&status=&blacklisted=` | 管理员 | 用户列表 | `getAdminUsers` |
| GET | `/admin/users/overview` | 管理员 | 用户总览统计 | `getAdminUsersOverview` |
| GET | `/admin/users/{user_id}` | 管理员 | 单个用户 | — |
| GET | `/admin/users/{user_id}/detail` | 管理员 | 用户详情 + API Key | `getAdminUserDetail` |
| POST | `/admin/users` | super_admin | 创建用户 | `createAdminUser` |
| PATCH | `/admin/users/{user_id}/role` | super_admin | 修改角色 USER/ADMIN | `updateAdminUserRole` |
| PATCH | `/admin/users/{user_id}/segment` | super_admin | 修改用户画像 B/C | `updateAdminUserSegment` |
| POST | `/admin/users/{user_id}/ban` | 管理员 | 封禁用户 | `banAdminUser` |
| POST | `/admin/users/{user_id}/unban` | 管理员 | 解封用户 | `unbanAdminUser` |
| POST | `/admin/users/{user_id}/blacklist` | super_admin | 拉黑 | `addAdminBlacklist` |
| DELETE | `/admin/users/{user_id}/blacklist` | super_admin | 移出黑名单 | `removeAdminBlacklist` |
| DELETE | `/admin/users/{user_id}` | super_admin | 删除用户 | — |
| GET | `/admin/sensitive-words` | 管理员 | 敏感词列表 | `getSensitiveWords` |
| POST | `/admin/sensitive-words` | 管理员 | 新增 / 更新敏感词 | `saveSensitiveWord` |
| DELETE | `/admin/sensitive-words/{word}` | 管理员 | 删除敏感词 | `disableSensitiveWord` |
| GET | `/admin/moderation-records?page=1&page_size=20` | 管理员 | 内容巡查记录 | `getModerationRecords` |
| POST | `/admin/moderation-records/{record_id}/review` | 管理员 | 标记已审 | `reviewModerationRecord` |
| GET | `/admin/action-logs?page=1&page_size=20` | 管理员 | 管理员操作日志 | `getAdminActionLogs` |

**POST `/admin/users/{user_id}/ban` 请求体**

```json
{
  "reason": "封禁理由",
  "banned_until": "2026-06-28T12:00:00"
}
```

说明：`banned_until` 为空表示永久封禁；到期后用户登录会自动解封。

**POST `/admin/sensitive-words` 请求体**

```json
{
  "word": "敏感词",
  "reason": "拦截原因"
}
```

**PATCH `/admin/users/{user_id}/role` 请求体**

```json
{
  "role": "USER"
}
```

---

### 9. 页面预览与测试（main.py）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 登录预览页 |
| GET | `/page/admin` | 管理员预览页 |
| GET | `/page/index` | 起名预览页 |
| GET | `/page/dashboard` | API Key 预览页 |
| GET | `/mail/test?email=` | 邮件发送测试 |
| GET | `/hello/{name}` | 健康检查 |

**静态预览页（`/static/`）**

- `register-preview.html`：注册预览
- `invitation-preview.html`：邀请预览
- `dashboard-preview.html`：API Key 预览
- `admin-users-preview.html`：用户管理预览

---

### 10. 前端已封装接口一览

以下路径均已在 `ainame/http/http.js` 中封装，多人协作时优先对照该文件：

```text
/auth/code
/auth/register
/auth/login
/invitation/me
/name/generate
/name/feedback
/knowledge/upload
/api-key/create
/api-key/list
/api-key/disable
/api-key/enable
/api-key/delete
/api-key/stats
/api-key/usage
/admin/users
/admin/users/overview
/admin/users/{id}/detail
/admin/users
/admin/users/{id}/role
/admin/users/{id}/segment
/admin/users/{id}/ban
/admin/users/{id}/unban
/admin/users/{id}/blacklist
/admin/sensitive-words
/admin/moderation-records
/admin/moderation-records/{id}/review
/admin/action-logs
/community/polls
/community/polls/{id}/vote
/community/admin/polls
/community/admin/polls/{id}/hide
/community/admin/polls/{id}/unhide
```

---

### 本地测试账号

密码统一为 `111111`：

| 邮箱 | 用户名 | 角色 |
| --- | --- | --- |
| `1046399289@qq.com` | `superadmin` | `super_admin` |
| `admin@qq.com` | `admin` | `admin` |
| `user@qq.com` | `user` | `user` |

更多改动说明见 [../README.md](../README.md)。
