# 快速开始 (5分钟部署)

> ⚡ 最小模式部署指南 — 只需要 PHP + Docker

## 前置条件

- ✅ PHP {{PHP_VERSION}}+（含 FPM）
- ✅ Docker + Docker Compose
- ✅ Nginx 或 Apache
- ✅ 一个域名（或本地测试用 `localhost`）

## 步骤

### 1. 下载代码

```bash
git clone {{REPO_URL}}
cd {{PROJECT_NAME}}
```

### 2. 运行安装脚本

```bash
chmod +x scripts/install.sh
./scripts/install.sh --mode minimal --auto \
  --domain {{DOMAIN}} \
  --title "{{SITE_TITLE}}" \
  --path {{PROJECT_DIR}}
```

脚本会自动完成：
- ⚙️ 生成 `.env` 和 `config.json`
- 🐳 启动 Meilisearch（Docker）
- 🔑 创建搜索 API Key
- 📋 输出下一步提示

### 3. 配置 Nginx

```bash
sudo cp config/examples/nginx.minimal.conf /etc/nginx/sites-available/{{DOMAIN}}
# 编辑文件，替换 {{PLACEHOLDER}}
sudo ln -s /etc/nginx/sites-available/{{DOMAIN}} /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 4. 运行爬虫

```bash
cd transspider
pip install scrapy trafilatura meilisearch
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000
cd .. && python add_direct_links.py
```

### 5. 验证

访问 `https://{{DOMAIN}}/?q=HRT`

✅ 看到搜索结果 → 部署成功！

---

## 故障排除

| 问题 | 解决 |
|------|------|
| 页面空白 | 检查 PHP-FPM 是否运行 |
| 搜索无结果 | Meilisearch 未启动或爬虫未运行 |
| 502 Bad Gateway | PHP-FPM 监听地址不匹配 |

更多问题查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 下一步

- 🚀 [完整模式部署](FULL.md) — 添加 API + OAuth
- 🎨 [品牌替换](REBRAND.md) — 自定义站点信息
- 🔧 [详细配置](MINIMAL.md) — 了解最小模式全貌
