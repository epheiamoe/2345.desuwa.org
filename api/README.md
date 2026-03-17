# 2345.desuwa.org API 服务

## 环境变量

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=Ov23lihGlJrOecfqaJYd
GITHUB_CLIENT_SECRET=your_client_secret

# Meilisearch
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_INDEX=trans_resources

# Flask Secret (for sessions)
FLASK_SECRET=change_this_to_random_string

# Server
API_HOST=0.0.0.0
API_PORT=5000
```

## 运行

```bash
cd api
pip install flask flask-cors meilisearch requests pygithub
python app.py
```

## API 端点

### OAuth
- `GET /api/auth/login` - 跳转 GitHub 登录
- `GET /api/auth/callback` - OAuth 回调处理
- `GET /api/auth/logout` - 退出登录

### API Key
- `GET /api/keys` - 获取用户的 API Key
- `POST /api/keys/regenerate` - 重新生成 API Key

### 搜索
- `GET /api/search?q=关键词&lang=zh` - 搜索

### 用户信息
- `GET /api/me` - 获取当前用户信息
