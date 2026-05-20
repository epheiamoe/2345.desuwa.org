# 最小模式部署详解

> 🏠 纯 PHP + Meilisearch 的最轻量部署方案

## 前置条件

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| PHP | {{PHP_VERSION}} | 需 FPM 模块 |
| Docker | 20.10+ | 运行 Meilisearch |
| Nginx | 1.18+ | 或 Apache |
| Python | 3.8+ | 仅爬虫需要 |

## 架构

```
┌──────────┐      ┌──────────────┐
│   PHP    │──────│ Meilisearch  │
│ Frontend │      │   (Docker)   │
└──────────┘      └──────────────┘
```

**特点**：
- ✅ 无需 Python 运行时（服务器上）
- ✅ 无需 API 服务
- ✅ 搜索功能完整
- ⚠️ 无 API 控制台，无用户登录

## 一步步部署

### 步骤1：准备服务器

```bash
# 安装 PHP 及扩展
sudo apt update
sudo apt install php{{PHP_VERSION}}-fpm php{{PHP_VERSION}}-curl php{{PHP_VERSION}}-mbstring

# 安装 Docker
sudo apt install docker.io docker-compose

# 启动服务
sudo systemctl enable php{{PHP_VERSION}}-fpm
sudo systemctl start php{{PHP_VERSION}}-fpm
```

### 步骤2：下载代码

```bash
cd /var/www
git clone {{REPO_URL}} {{PROJECT_DIR}}
cd {{PROJECT_DIR}}
```

### 步骤3：配置环境

创建 `.env` 文件：

```bash
DEPLOY_MODE=minimal
ENABLE_API=false
ENABLE_OAUTH=false
ENABLE_CRAWLER=true

MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_API_KEY=
MEILI_MASTER_KEY=your_random_master_key_here

SITE_URL=https://{{DOMAIN}}
SITE_NAME={{SITE_NAME}}
SITE_TITLE={{SITE_TITLE}}
```

生成 Meilisearch API Key：

```bash
# 启动 Meilisearch
docker-compose up -d

# 创建 Search Key
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "Search-only key", "actions": ["search"], "indexes": ["trans_resources"], "expiresAt": null}'
```

将返回的 key 填入 `.env` 的 `MEILISEARCH_API_KEY`。

### 步骤4：配置 Nginx

```bash
sudo cp config/examples/nginx.minimal.conf /etc/nginx/sites-available/{{DOMAIN}}
```

编辑文件，替换以下占位符：

| 占位符 | 示例值 |
|--------|--------|
| `{{DOMAIN}}` | `search.example.com` |
| `{{PROJECT_DIR}}` | `/var/www/search` |
| `{{PHP_VERSION}}` | `8.1` |
| `{{MEILI_API_KEY}}` | `abc123...` |
| `{{MEILI_HOST}}` | `localhost` |
| `{{MEILI_PORT}}` | `7700` |

```bash
sudo ln -s /etc/nginx/sites-available/{{DOMAIN}} /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 步骤5：运行爬虫（首次）

在**本地或另一台机器**上（服务器不需要 Python）：

```bash
cd transspider
pip install scrapy trafilatura meilisearch
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000

cd ..
python add_direct_links.py
```

⚠️ 如果服务器有 Python 环境，也可以直接在服务器上运行。

### 步骤6：验证

```bash
# 检查 Meilisearch
curl http://localhost:7700/health

# 检查搜索
curl "https://{{DOMAIN}}/?q=test"

# 检查文档数量
curl "http://localhost:7700/indexes/trans_resources/stats" \
  -H "Authorization: Bearer $MEILISEARCH_API_KEY"
```

## 如何运行爬虫

### 手动运行

```bash
cd {{PROJECT_DIR}}/transspider
{{PROJECT_DIR}}/venv/bin/scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000
cd {{PROJECT_DIR}} && {{PROJECT_DIR}}/venv/bin/python add_direct_links.py
```

### 定时任务

```bash
# 编辑 crontab
crontab -e

# 添加（复制 config/examples/crontab.crawler 内容）
0 3 * * 0 cd {{PROJECT_DIR}}/transspider && {{PROJECT_DIR}}/venv/bin/scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000 >> /var/log/trans_spider.log 2>&1
```

## 常见问题

### Q: 爬虫必须在服务器上运行吗？

**A**: 不需要。你可以在任何能访问 Meilisearch 的机器上运行爬虫，只要配置正确的 `MEILISEARCH_HOST` 和 `MEILISEARCH_API_KEY`。

### Q: 如何更新索引？

**A**: 重新运行爬虫即可。Meilisearch 会自动更新文档。

### Q: 可以添加自己的网站吗？

**A**: 编辑 `domains.json`，在 `domains` 数组中添加：

```json
{"domain": "example.com", "name": "示例", "url": "https://example.com/", "tags": ["知识库"]}
```

### Q: 最小模式可以升级到完整模式吗？

**A**: 可以！运行 `./scripts/install.sh --mode full`，然后配置 GitHub OAuth 即可。

### Q: 如何备份数据？

**A**: Meilisearch 数据在 Docker Volume 中：

```bash
# 备份
docker run --rm -v trans_meilisearch_data:/data -v $(pwd):/backup alpine tar czf /backup/meilisearch_backup.tar.gz -C /data .

# 恢复
docker run --rm -v trans_meilisearch_data:/data -v $(pwd):/backup alpine tar xzf /backup/meilisearch_backup.tar.gz -C /data
```

---

## 相关文档

- [快速开始](QUICKSTART.md) — 5分钟上手
- [完整模式](FULL.md) — 添加 API + OAuth
- [故障排除](TROUBLESHOOTING.md)
