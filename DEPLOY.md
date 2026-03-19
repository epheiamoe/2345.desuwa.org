# 部署文档

本项目可以轻松自托管。

## 环境要求

- PHP 7.4+
- Docker + Docker Compose
- Nginx（或使用宝塔面板）

## 快速部署

### 1. 克隆代码

```bash
git clone https://github.com/epheiamoe/2345.desuwa.org.git
cd 2345.desuwa.org
```

### 2. 启动 Meilisearch

```bash
docker-compose up -d
```

验证 Meilisearch 启动：
```bash
curl http://localhost:7700/health
```

### 3. 配置网站

#### 使用宝塔面板（推荐）

1. 登录宝塔面板
2. 添加站点：
   - 域名：`your-domain.com`
   - 根目录：`/www/wwwroot/your-domain.com/frontend`
   - PHP 版本：7.4+

#### 或使用 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/2345.desuwa.org/frontend;
    index index.php;
    
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

### 4. 运行爬虫

```bash
cd transspider
pip install scrapy trafilatura meilisearch
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=200
```

### 5. 设置定时任务

```bash
# 每周日凌晨3点更新索引
0 3 * * 0 cd /www/wwwroot/your-domain/transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=200 >> /var/log/trans-spider.log 2>&1
```

## 配置说明

### 环境变量配置

推荐使用环境变量配置所有敏感信息，避免硬编码：

```bash
# Meilisearch Master Key（必填，用于生成 API Key）
export MEILI_MASTER_KEY=$(openssl rand -hex 32)

# Flask Secret Key（必填，用于 session 签名）
export FLASK_SECRET=$(openssl rand -hex 32)

# GitHub OAuth（可选，用于 API 控制台登录）
export GITHUB_CLIENT_ID=your_github_oauth_client_id
export GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
```

### 域名列表

- `domains.json` - 完整的域名和标签列表
- `domains_test.txt` - 测试用域名（少量）

### Meilisearch 配置

在 `transspider/config.py` 中：

```python
MEILISEARCH_HOST = os.environ.get("MEILISEARCH_HOST", "localhost")
MEILISEARCH_PORT = int(os.environ.get("MEILISEARCH_PORT", "7700"))
MEILISEARCH_INDEX = "trans_resources"
MEILISEARCH_API_KEY = os.environ.get("MEILISEARCH_API_KEY", "")
```

### PHP 前端配置

在 `frontend/index.php` 中：

```php
$MEILISEARCH_HOST = getenv('MEILISEARCH_HOST') ?: 'localhost';
$MEILISEARCH_PORT = getenv('MEILISEARCH_PORT') ?: '7700';
$MEILISEARCH_INDEX = 'trans_resources';
$MEILISEARCH_API_KEY = getenv('MEILISEARCH_API_KEY') ?: '';
```

## 安全加固（生产环境必读）

### 1. Meilisearch 安全配置

**docker-compose.yml 已配置为生产模式：**
- `MEILI_ENV=production` - 启用生产模式
- `MEILI_MASTER_KEY` - 从环境变量读取 Master Key
- 端口绑定到 `127.0.0.1:7700` - 仅允许本地访问

**创建分层 API Key：**

```bash
# 使用 Master Key 登录 Meilisearch
MEILI_MASTER_KEY=your_master_key

# 创建搜索密钥（供前端和 API 使用）
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Search-only key for frontend and API",
    "actions": ["search"],
    "indexes": ["trans_resources"],
    "expiresAt": null
  }'

# 创建管理密钥（供爬虫使用）
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Admin key for crawler pipeline",
    "actions": ["documents.add", "documents.delete", "indexes.*"],
    "indexes": ["trans_resources"],
    "expiresAt": null
  }'
```

将返回的密钥设置为环境变量：
```bash
export MEILISEARCH_SEARCH_KEY="returned_search_key"
export MEILISEARCH_ADMIN_KEY="returned_admin_key"
```

### 2. Flask API 安全配置

**必须设置 FLASK_SECRET 环境变量：**
```bash
export FLASK_SECRET=$(openssl rand -hex 32)
```

**CORS 已配置为仅允许本站点访问：**
```python
CORS(app, resources={
    r"/api/*": {
        "origins": [SITE_URL],
        "methods": ["GET", "POST"],
        "allow_headers": ["Authorization", "Content-Type"]
    }
})
```

### 3. 文件权限

确保 `api/db.json` 文件权限为 600（仅所有者可读写）：
```bash
chmod 600 api/db.json
```

### 4. HTTPS 部署

生产环境必须使用 HTTPS。推荐使用 Let's Encrypt：

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 5. Nginx 安全头配置

在 Nginx 配置中添加安全响应头：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 安全头
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://your-domain.com;" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;

    # 代理配置（修复 X-Forwarded-For 伪造问题）
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. 验证安全配置

```bash
# 验证 Master Key 是否生效（应返回 401）
curl -s -o /dev/null -w "%{http_code}" http://localhost:7700/indexes

# 验证 Search Key 是否生效（应返回 200）
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer YOUR_SEARCH_KEY" \
  "http://localhost:7700/indexes/trans_resources/search" \
  -d '{"q": "test"}'
```

## 使用 Docker 部署（推荐）

### docker-compose.yml

```yaml
services:
  meilisearch:
    image: getmeili/meilisearch:latest
    ports:
      - "127.0.0.1:7700:7700"
    volumes:
      - meilisearch_data:/meili_data
    environment:
      - MEILI_ENV=production
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
    restart: unless-stopped

volumes:
  meilisearch_data:
```
  meilisearch_data:
```

启动：
```bash
docker-compose up -d
```

## 搜索功能测试

```bash
# 测试搜索
curl "http://localhost:7700/indexes/trans_resources/search?q=HRT"

# 测试筛选
curl "http://localhost:7700/indexes/trans_resources/search?q=HRT&filter=tags%20=%20%22MtF%22"
```

## 目录结构

```
2345.desuwa.org/
├── frontend/          # PHP 前端
│   └── index.php      # 搜索页面
├── transspider/       # Scrapy 爬虫
│   ├── spiders/       # 爬虫代码
│   ├── pipelines.py   # Meilisearch 推送
│   └── config.py      # 配置
├── domains.json       # 域名和标签列表
├── docker-compose.yml # Meilisearch
└── README.md
```

## 许可证

LGPLv3
