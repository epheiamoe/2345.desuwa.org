# 完整模式部署详解

> 🚀 PHP + Flask API + GitHub OAuth 的全功能部署

## 前置条件

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| PHP | {{PHP_VERSION}} | 需 FPM 模块 |
| Python | 3.8+ | 运行 Flask API |
| Docker | 20.10+ | 运行 Meilisearch |
| Nginx | 1.18+ | 反向代理 |
| GitHub 账号 | - | 创建 OAuth App |

## 架构

```
┌──────────┐      ┌──────────────┐      ┌──────────┐
│   PHP    │──────│ Meilisearch  │◄─────│  Flask   │
│ Frontend │      │   (Docker)   │      │   API    │
└──────────┘      └──────────────┘      └──────────┘
       │                                   │
       └────────── GitHub OAuth ───────────┘
```

**特点**：
- ✅ API 控制台（开发者使用）
- ✅ GitHub 登录 + 配额管理
- ✅ 速率限制
- ✅ 管理员面板

## 一步步部署

### 步骤1-4：同最小模式

先完成 [最小模式](MINIMAL.md) 的步骤1-4。

### 步骤5：配置 Python 环境

```bash
# 创建虚拟环境
cd {{PROJECT_DIR}}/api
python3 -m venv ../venv
source ../venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤6：配置 GitHub OAuth

这是完整模式的关键步骤。

#### 6.1 创建 GitHub OAuth App

1. 访问 [GitHub Developer Settings](https://github.com/settings/developers)
2. 点击 **"New OAuth App"**
3. 填写信息：

| 字段 | 值 |
|------|-----|
| Application name | `{{SITE_NAME}} Search` |
| Homepage URL | `https://{{DOMAIN}}` |
| Application description | ` transgender resource search API` |
| Authorization callback URL | `https://{{DOMAIN}}/api/auth/callback` |

4. 点击 **"Register application"**

#### 6.2 获取 Client ID 和 Secret

注册成功后：
- **Client ID**：页面直接显示（如 `Iv1.abc123...`）
- **Client Secret**：点击 **"Generate a new client secret"** 生成

⚠️ **重要**：Client Secret 只显示一次，请立即保存！

#### 6.3 配置环境变量

编辑 `.env` 文件：

```bash
DEPLOY_MODE=full
ENABLE_API=true
ENABLE_OAUTH=true

# GitHub OAuth
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
ADMIN_USERS=your_github_username

# Flask
FLASK_SECRET=$(openssl rand -hex 32)
FLASK_PORT=5000

# Meilisearch
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_API_KEY=your_search_key
MEILI_MASTER_KEY=your_master_key

# 站点
SITE_URL=https://{{DOMAIN}}
SITE_NAME={{SITE_NAME}}
SITE_TITLE={{SITE_TITLE}}

# 速率限制（可选）
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_DAY=1000
RATE_LIMIT_PER_MONTH=2000
```

### 步骤7：配置 Nginx（完整版）

```bash
sudo cp config/examples/nginx.full.conf /etc/nginx/sites-available/{{DOMAIN}}
```

编辑文件，替换占位符：

| 占位符 | 示例值 |
|--------|--------|
| `{{DOMAIN}}` | `search.example.com` |
| `{{PROJECT_DIR}}` | `/var/www/search` |
| `{{PHP_VERSION}}` | `8.1` |
| `{{MEILI_API_KEY}}` | `abc123...` |
| `{{FLASK_PORT}}` | `5000` |
| `{{RATE_LIMIT_PER_MINUTE}}` | `10` |
| `{{SEARCH_RATE_LIMIT}}` | `30` |

```bash
sudo ln -s /etc/nginx/sites-available/{{DOMAIN}} /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 步骤8：启动 API 服务

#### 使用 systemd（推荐生产环境）

```bash
# 复制服务文件
sudo cp config/examples/systemd.api.service /etc/systemd/system/{{SITE_NAME}}.service

# 编辑文件，替换占位符
sudo systemctl daemon-reload
sudo systemctl enable {{SITE_NAME}}
sudo systemctl start {{SITE_NAME}}

# 查看状态
sudo systemctl status {{SITE_NAME}}
```

#### 或使用手动启动

```bash
cd {{PROJECT_DIR}}/api
source ../venv/bin/activate
python app.py
```

### 步骤9：验证

#### 验证 API 服务

```bash
# API 健康检查
curl http://127.0.0.1:{{FLASK_PORT}}/api/health

# 验证 OAuth 配置（会跳转到 GitHub）
curl -I "https://{{DOMAIN}}/api/auth/login"
```

#### 验证前端集成

1. 访问 `https://{{DOMAIN}}`
2. 确认看到 **"API 控制台"** 按钮
3. 点击 **"登录"**，应跳转到 GitHub 授权页面
4. 授权后返回，确认登录成功

#### 验证 API 调用

```bash
# 获取 API Key（登录后在控制台查看）
curl "https://{{DOMAIN}}/api/search?q=HRT" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 设置管理员

在 `.env` 的 `ADMIN_USERS` 中添加 GitHub 用户名（逗号分隔）：

```bash
ADMIN_USERS=alice,bob,charlie
```

重启 API 服务生效：

```bash
sudo systemctl restart {{SITE_NAME}}
```

管理员可以：
- 查看所有用户配额使用情况
- 重置用户配额
- 查看系统统计信息

## 速率限制配置

### Nginx 层

在 `nginx.full.conf` 中已配置：
- API 调用：`{{RATE_LIMIT_PER_MINUTE}}` 请求/分钟
- 搜索请求：`{{SEARCH_RATE_LIMIT}}` 请求/分钟

### Flask 层

在 `.env` 中配置：
- `RATE_LIMIT_PER_MINUTE=10`
- `RATE_LIMIT_PER_DAY=1000`
- `RATE_LIMIT_PER_MONTH=2000`

## 安全加固

### 1. HTTPS

```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d {{DOMAIN}}
```

### 2. 防火墙

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### 3. Meilisearch 认证

确保 `MEILI_MASTER_KEY` 已设置且复杂：

```bash
# 生成强密钥
openssl rand -hex 32
```

---

## 相关文档

- [快速开始](QUICKSTART.md)
- [最小模式](MINIMAL.md)
- [Docker 模式](DOCKER.md)
- [故障排除](TROUBLESHOOTING.md)
