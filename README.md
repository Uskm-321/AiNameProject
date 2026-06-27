# AiNameProject

AI naming app with a uni-app frontend and a FastAPI backend.

## Project Structure

```text
AiNameProject/
  ainame/     Frontend uni-app project
  backend/    FastAPI backend
```

## Backend

Run backend commands from the `backend/` directory so the current import paths work correctly.

```powershell
cd backend
python main.py
```

After startup, open:

```text
http://127.0.0.1:9000/
```

The root page now opens the browser preview login page.

API root test behavior was replaced by the preview page. The old backend test response was:

```json
{"message":"Hello World"}
```

## Frontend

Open `ainame/` with HBuilderX or another uni-app compatible tool and run the app from there.

The frontend request helper is in `ainame/http/http.js`. It calls the backend on port `9000` using the current host name in browser builds.

## 改动

本次改动围绕本地预览、三类用户角色、管理员账号和用户管理能力展开。

### 启动与预览

- 后端 `backend/main.py` 增加了直接运行入口，可以用 `python main.py` 启动。
- 后端本地端口从 `8000` 调整为 `9000`。
- 浏览器打开 `http://127.0.0.1:9000/` 时，显示登录预览页。
- 新增浏览器预览页：
  - `ainame/login-preview.html`
  - `ainame/admin-preview.html`
  - `ainame/index-preview.html`
- 登录预览页登录成功后：
  - `admin` / `super_admin` 跳转到 `/page/admin`
  - `user` 跳转到 `/page/index`
- 注意：这些预览页用于浏览器快速联调；完整 uni-app 页面仍建议用 HBuilderX 打开 `ainame/` 运行。

### 角色体系

原来角色只有：

```text
USER
ADMIN
```

现在调整为：

```text
user
admin
super_admin
```

权限约定：

- `super_admin`：系统最高权限，可以管理用户、修改角色、冻结/解冻用户、删除用户、管理社区内容。
- `admin`：社区运营管理员，可以进入管理后台和管理社区内容，但不能修改用户角色。
- `user`：普通产品用户，可以使用起名、社区投票、API Key、邀请 credits 等普通功能。

兼容处理：

- 后端仍兼容旧值 `USER`、`ADMIN`、`SUPER_ADMIN`。
- 前端登录、首页入口、后台权限判断也兼容旧值。

### 管理后台能力

管理员预览页 `ainame/admin-preview.html` 已补充：

- 用户列表展示。
- 按用户名或邮箱查询。
- 输入查询内容后按回车查询。
- 点击“查询”按钮查询。
- 用户分页。
- 输入页码后按回车跳转。
- 点击“跳转”按钮跳转。
- 上一页 / 下一页。
- 角色排序：
  - `super_admin`
  - `admin`
  - `user`
- 同权限用户按创建时间排序。
- 用户角色修改。
- 冻结用户，冻结时必须填写理由，并可选择 `1天`、`7天`、`30天`、`永久`。
- 冻结后状态列展示冻结理由和截止时间；永久冻结显示“永久”。
- 解冻用户，冻结后同一操作位置显示“取消冻结”。
- 删除用户。
- 退出登录按钮保留。

后端补充：

- `DELETE /admin/users/{user_id}` 删除用户接口。
- `PATCH /admin/users/{user_id}/role` 只允许 `super_admin` 修改角色。
- `super_admin` 不能修改自己的角色。
- 删除用户时 `super_admin` 不能删除自己。
- 至少保留 1 个 `super_admin`。

### 数据库测试账号

已插入/更新以下 3 个本地测试账号，密码统一为：

```text
111111
```

| 邮箱 | 用户名 | 角色 |
| --- | --- | --- |
| `1046399289@qq.com` | `superadmin` | `super_admin` |
| `admin@qq.com` | `admin` | `admin` |
| `user@qq.com` | `user` | `user` |

数据库：

```text
MySQL database: ainame
```

如果本地没有 `ainame` 数据库，需要先创建数据库和表结构，再插入账号。

### 模块四：社区投票

已新增社区投票基础闭环：

- 起名结果页可将当前 `names[]` 发布到社区。
- 社区页展示投票列表、候选名字、AI 分析、票数和投票按钮。
- 用户每个投票帖只能投一票，再投其它选项会自动切换。
- 管理员后台新增“社区投票”页签，可隐藏/取消隐藏投票。
- 隐藏投票时必须填写理由。
- 被隐藏投票不会出现在公共社区列表；发布者本人仍可看到隐藏状态和理由。

接口：

```text
POST /community/polls
GET  /community/polls
POST /community/polls/{poll_id}/vote
GET  /community/admin/polls
POST /community/admin/polls/{poll_id}/hide
POST /community/admin/polls/{poll_id}/unhide
```

发布接口入参：

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

### 接口文档

完整接口说明已整理到 [backend/README.md](backend/README.md)，便于多人协作时查阅。以下为当前项目实际用到的接口摘要。

**Base URL：** `http://127.0.0.1:9000`

**鉴权：**

- 登录接口返回 `token`，后续请求带 `Authorization: Bearer {token}`
- 外部 API 调用可带 `X-API-Key: {key}` 访问 `/name/npc`、`/name/novel-character`、`/name/place`、`/name/generate`

| 模块 | 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- | --- |
| 认证 | GET | `/auth/code?email=` | 否 | 发送邮箱验证码 |
| 认证 | POST | `/auth/register` | 否 | 注册 |
| 认证 | POST | `/auth/login` | 否 | 登录 |
| 起名 | POST | `/name/generate` | Token / API Key | 首次生成 |
| 起名 | POST | `/name/feedback` | Token | 意见微调 |
| 起名 | POST | `/name/npc` | Token / API Key | NPC 生成 |
| 起名 | POST | `/name/novel-character` | Token / API Key | 小说角色生成 |
| 起名 | POST | `/name/place` | Token / API Key | 地名生成 |
| 起名 | POST | `/name/get_names` | Token | 旧版生成接口 |
| 知识库 | POST | `/knowledge/upload` | Token | 上传 TXT/PDF |
| 视觉 | POST | `/visual/generate` | Token | 企业 slogan / logo |
| 邀请 | GET | `/invitation/me` | Token | 邀请码、credits、奖励记录 |
| API Key | POST | `/api-key/create` | Token | 创建 Key |
| API Key | GET | `/api-key/list` | Token | Key 列表 |
| API Key | POST | `/api-key/disable` | Token | 禁用 Key |
| API Key | POST | `/api-key/enable` | Token | 启用 Key |
| API Key | POST | `/api-key/delete` | Token | 删除 Key |
| API Key | GET | `/api-key/stats` | Token | 调用统计 |
| API Key | GET | `/api-key/usage` | Token | 调用记录 |
| 社区 | POST | `/community/polls` | Token | 发布投票 |
| 社区 | GET | `/community/polls` | Token | 投票列表 |
| 社区 | POST | `/community/polls/{poll_id}/vote` | Token | 投票 / 切换 |
| 社区 | GET | `/community/admin/polls` | 管理员 | 管理端列表 |
| 社区 | POST | `/community/admin/polls/{poll_id}/hide` | 管理员 | 隐藏 |
| 社区 | POST | `/community/admin/polls/{poll_id}/unhide` | 管理员 | 取消隐藏 |
| 管理 | GET | `/admin/users` | 管理员 | 用户列表 |
| 管理 | GET | `/admin/users/overview` | 管理员 | 用户总览 |
| 管理 | GET | `/admin/users/{user_id}/detail` | 管理员 | 用户详情 |
| 管理 | POST | `/admin/users` | super_admin | 创建用户 |
| 管理 | PATCH | `/admin/users/{user_id}/role` | super_admin | 改角色 |
| 管理 | PATCH | `/admin/users/{user_id}/segment` | super_admin | 改画像 |
| 管理 | POST | `/admin/users/{user_id}/ban` | 管理员 | 封禁 |
| 管理 | POST | `/admin/users/{user_id}/unban` | 管理员 | 解封 |
| 管理 | POST | `/admin/users/{user_id}/blacklist` | super_admin | 拉黑 |
| 管理 | DELETE | `/admin/users/{user_id}/blacklist` | super_admin | 移出黑名单 |
| 管理 | DELETE | `/admin/users/{user_id}` | super_admin | 删除用户 |
| 管理 | GET | `/admin/sensitive-words` | 管理员 | 敏感词列表 |
| 管理 | POST | `/admin/sensitive-words` | 管理员 | 新增 / 更新敏感词 |
| 管理 | DELETE | `/admin/sensitive-words/{word}` | 管理员 | 删除敏感词 |
| 管理 | GET | `/admin/moderation-records` | 管理员 | 巡查记录 |
| 管理 | POST | `/admin/moderation-records/{record_id}/review` | 管理员 | 标记已审 |
| 管理 | GET | `/admin/action-logs` | 管理员 | 操作日志 |

前端封装位置：`ainame/http/http.js`

详细请求体、响应示例、权限说明见 [backend/README.md](backend/README.md)。

## Git Workflow

Use `main` as the stable branch. Build each module on a feature branch and merge it back with a pull request after review.

Recommended branch examples:

```text
feature/module-1-naming
feature/community-vote
feature/api-key
feature/invite-credits
```

Before starting new work, sync from `main`:

```powershell
git checkout main
git pull origin main
git checkout -b feature/your-module
```

## Current Module Split

This branch starts with structure cleanup, then module 1 work.

Our side:

- Module 1: naming core form/schema/prompt/result updates.
- Module 2: `.com` domain checks for generated names.
- Module 3: enterprise-only slogan and logo placeholder flow.
- Admin cleanup for user bans, roles, sensitive words, and logs.

Teammate side:

- Community voting.
- API Key page and generation API.
- Invitation credits.
