# Docker Compose 部署

> 🐳 所有服务容器化的一键部署方案

## 前置条件

- Docker 20.10+
- Docker Compose 2.0+
- 域名（或本地测试）

## 架构

```
┌─────────────────────────────────────────┐
│          Docker Compose                 │
│  ┌──────┐ ┌──────┐ ┌──────────┐        │
│  │Nginx │ │ PHP  │ │Meilisearch│        │
│  └──────┘ └──────┘ └──────────┘        │
│       │                                 │
│  ┌──────────┐                          │
│  │Flask API │ (可选)                    │
│  └──────────┘                          │
└─────────────────────────────────────────┘
```

## 文件

Docker 模式使用专用配置：

- `docker-compose.yml` — Meilisearch（所有模式共用）
- `docker-compose.full.yml` — 完整模式（+Nginx + PHP + API）

## 最小模式（Docker）

### 步骤1：配置环境

```bash
cp .env.minimal.example .env
# 编辑 .env，设置 MEILI_MASTER_KEY 和域名
```

### 步骤2：启动服务

```bash
docker-compose up -d
```

Meilisearch 将在 `http://localhost:7700` 运行。

### 步骤3：配置 Web 服务器

由于 PHP 不在容器中，你需要：

1. 在宿主机安装 PHP-FPM
2. 使用 `config/examples/nginx.minimal.conf` 配置 Nginx
3. 确保 Nginx 可以访问 Docker 网络中的 Meilisearch

或者使用 `docker-compose.full.yml`：

```bash
docker-compose -f docker-compose.full.yml up -d
```

## 完整模式（Docker）

### 步骤1：配置环境

```bash
cp .env.full.example .env
```

编辑 `.env`，设置所有必需变量：

```bash
DEPLOY_MODE=docker
ENABLE_API=true
ENABLE_OAUTH=true

MEILI_MASTER_KEY=$(openssl rand -hex 32)
MEILISEARCH_API_KEY=  # 启动后自动生成

GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
FLASK_SECRET=$(openssl rand -hex 32)
ADMIN_USERS=your_github_username

SITE_URL=https://{{DOMAIN}}
SITE_NAME={{SITE_NAME}}
```

### 步骤2：启动服务

```bash
docker-compose -f docker-compose.full.yml up -d
```

### 步骤3：生成 API Key

```bash
# 进入 Meilisearch 容器
docker exec -it trans_meilisearch sh

# 创建 Search Key
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "Search-only key", "actions": ["search"], "indexes": ["trans_resources"], "expiresAt": null}'
```

将 key 更新到 `.env` 并重启：

```bash
docker-compose -f docker-compose.full.yml restart api
```

### 步骤4：配置 GitHub OAuth

回调 URL 设置为：

```
https://{{DOMAIN}}/api/auth/callback
```

注意：如果 Docker 使用内部网络，确保域名解析正确。

## 数据持久化

| 数据 | 位置 | 说明 |
|------|------|------|
| Meilisearch | Docker Volume `meilisearch_data` | 索引数据 |
| SQLite | 挂载到 `./data/db.sqlite` | API 数据库 |
| 日志 | 挂载到 `./logs/` | 服务日志 |

备份：

```bash
# Meilisearch
docker run --rm -v trans_meilisearch_data:/data -v $(pwd):/backup alpine tar czf /backup/meili.tar.gz -C /data .

# SQLite
cp data/db.sqlite backup/db.sqlite.$(date +%Y%m%d)
```

## 环境变量传递

Docker 模式下，环境变量通过 `docker-compose.full.yml` 传递：

```yaml
services:
  php:
    environment:
      - MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}
      - MEILISEARCH_HOST=meilisearch
      - MEILISEARCH_PORT=7700

  api:
    environment:
      - FLASK_SECRET=${FLASK_SECRET}
      - GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
      - MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}
```

## 日志查看

```bash
# 所有服务
docker-compose -f docker-compose.full.yml logs -f

# 单个服务
docker-compose -f docker-compose.full.yml logs -f api
docker-compose -f docker-compose.full.yml logs -f nginx
docker-compose -f docker-compose.full.yml logs -f meilisearch
```

## 更新部署

```bash
# 拉取最新镜像
docker-compose -f docker-compose.full.yml pull

# 重启服务
docker-compose -f docker-compose.full.yml up -d

# 清理旧镜像
docker image prune -f
```

---

## 相关文档

- [快速开始](QUICKSTART.md)
- [最小模式](MINIMAL.md)
- [完整模式](FULL.md)
- [故障排除](TROUBLESHOOTING.md)
