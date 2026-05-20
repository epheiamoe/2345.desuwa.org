# 故障排除指南

> 🔧 部署和运行中的常见问题及解决方案

## 目录

- [Meilisearch](#meilisearch)
- [PHP](#php)
- [Nginx](#nginx)
- [Flask API](#flask-api)
- [GitHub OAuth](#github-oauth)
- [爬虫](#爬虫)
- [搜索](#搜索)
- [Docker](#docker)
- [性能](#性能)
- [其他](#其他)

---

## Meilisearch

### 1. Meilisearch 启动失败

**现象**：`docker-compose up -d` 后容器退出

**排查**：
```bash
# 查看日志
docker logs trans_meilisearch

# 检查端口占用
sudo lsof -i :7700
```

**解决**：
- 端口被占用：修改 `docker-compose.yml` 端口映射
- 内存不足：增加 Docker 内存限制或服务器内存
- 权限问题：检查数据卷权限 `sudo chown -R 1000:1000 /path/to/data`

### 2. Meilisearch 返回 401 Unauthorized

**现象**：搜索时返回认证错误

**解决**：
```bash
# 检查 API Key 是否正确
curl "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY"

# 重新生成 Search Key
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "Search-only key", "actions": ["search"], "indexes": ["trans_resources"], "expiresAt": null}'
```

### 3. Meilisearch 数据丢失

**现象**：重启后索引为空

**解决**：
- 检查 Docker Volume 是否正确挂载
- 确认 `docker-compose.yml` 中 `volumes` 配置
- 从备份恢复（如果有）

### 4. Meilisearch 内存占用过高

**解决**：
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G  # 限制内存
```

---

## PHP

### 5. PHP 页面空白

**现象**：访问网站显示空白页面

**排查**：
```bash
# 检查 PHP-FPM 是否运行
sudo systemctl status php{{PHP_VERSION}}-fpm

# 检查 PHP 错误日志
sudo tail -f /var/log/php{{PHP_VERSION}}-fpm.log

# 检查 Nginx 错误日志
sudo tail -f /var/log/nginx/{{DOMAIN}}.error.log
```

**解决**：
- PHP-FPM 未运行：`sudo systemctl start php{{PHP_VERSION}}-fpm`
- 缺少扩展：`sudo apt install php{{PHP_VERSION}}-curl php{{PHP_VERSION}}-mbstring`
- 权限问题：`sudo chown -R www-data:www-data {{PROJECT_DIR}}/frontend`

### 6. PHP 找不到扩展

**现象**：`Fatal error: Call to undefined function curl_init()`

**解决**：
```bash
# Debian/Ubuntu
sudo apt install php{{PHP_VERSION}}-curl php{{PHP_VERSION}}-mbstring php{{PHP_VERSION}}-json
sudo systemctl restart php{{PHP_VERSION}}-fpm

# CentOS/RHEL
sudo yum install php-curl php-mbstring php-json
sudo systemctl restart php-fpm
```

### 7. PHP 环境变量读取不到

**现象**：`getenv('MEILISEARCH_API_KEY')` 返回 false

**解决**：
- 确认 Nginx 配置中 `fastcgi_param` 已设置
- 确认 `.env` 文件存在且可读
- 检查 PHP-FPM 进程是否有权限读取 `.env`

---

## Nginx

### 8. 502 Bad Gateway

**现象**：Nginx 返回 502 错误

**排查**：
```bash
# 检查 PHP-FPM 监听地址
sudo grep "listen" /etc/php/{{PHP_VERSION}}/fpm/pool.d/www.conf

# 检查 Nginx 配置中的 fastcgi_pass
sudo grep "fastcgi_pass" /etc/nginx/sites-available/{{DOMAIN}}
```

**解决**：
- 地址不匹配：统一为 socket 或 TCP
- PHP-FPM 未运行：`sudo systemctl restart php{{PHP_VERSION}}-fpm`
- 权限问题：`sudo chmod 666 /var/run/php/php{{PHP_VERSION}}-fpm.sock`

### 9. 404 Not Found

**现象**：静态文件或 PHP 文件找不到

**解决**：
- 检查 `root` 路径是否正确
- 检查文件是否存在：`ls -la {{PROJECT_DIR}}/frontend/`
- 检查 Nginx 用户是否有读取权限

### 10. Nginx 配置测试失败

**现象**：`nginx -t` 报错

**解决**：
```bash
# 查看详细错误
sudo nginx -t

# 常见错误：
# - 缺少分号
# - 大括号不匹配
# - 引号未闭合
```

### 11. HTTPS 配置问题

**现象**：证书错误或混合内容

**解决**：
```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d {{DOMAIN}}

# 检查证书续期
sudo certbot renew --dry-run
```

---

## Flask API

### 12. API 服务无法启动

**现象**：`python app.py` 报错

**排查**：
```bash
# 检查依赖
pip install -r requirements.txt

# 检查端口占用
sudo lsof -i :{{FLASK_PORT}}

# 查看详细错误
python app.py 2>&1 | head -50
```

**解决**：
- 缺少依赖：`pip install -r requirements.txt`
- 端口被占用：修改 `FLASK_PORT` 或停止占用进程
- `.env` 配置错误：检查必填字段

### 13. API 返回 500 Internal Server Error

**排查**：
```bash
# 查看日志
sudo journalctl -u {{SITE_NAME}} -f

# 或手动运行查看错误
source venv/bin/activate
python app.py
```

**常见原因**：
- `.env` 中缺少 `FLASK_SECRET`
- Meilisearch 连接失败
- 数据库权限问题

### 14. API 速率限制不生效

**解决**：
- 确认 `RATE_LIMIT_PER_MINUTE` 已设置
- 确认使用 SQLite 存储（v1.3+）
- 检查 `database.py` 是否正确初始化

---

## GitHub OAuth

### 15. OAuth 回调失败

**现象**：授权后跳转回错误页面

**排查**：
- 检查 GitHub OAuth App 的 Callback URL
- 检查 `.env` 中的 `SITE_URL`
- 检查 Nginx 代理配置

**解决**：
```bash
# Callback URL 必须完全一致
# 正确：https://{{DOMAIN}}/api/auth/callback
# 错误：https://{{DOMAIN}}/api/auth/callback/ （多了斜杠）
```

### 16. "Bad credentials" 错误

**现象**：GitHub 返回 bad credentials

**解决**：
- 检查 `GITHUB_CLIENT_ID` 和 `GITHUB_CLIENT_SECRET` 是否正确
- 确认没有多余的空格
- 重新生成 Client Secret

### 17. 登录后跳转回首页未登录

**现象**：授权成功但页面仍显示未登录

**解决**：
- 检查 `FLASK_SECRET` 是否设置
- 检查浏览器是否阻止 Cookie
- 检查 `SESSION_COOKIE_SECURE`（HTTPS 时需 true）

### 18. 管理员权限不生效

**现象**：已配置 `ADMIN_USERS` 但无管理权限

**解决**：
- 确认用户名大小写正确（GitHub 用户名区分大小写）
- 重启 API 服务
- 检查用户是否已完成 OAuth 流程

---

## 爬虫

### 19. 爬虫无法连接 Meilisearch

**现象**：爬虫运行但索引为空

**排查**：
```bash
# 检查 Meilisearch 是否可访问
curl http://{{MEILI_HOST}}:{{MEILI_PORT}}/health

# 检查 Admin Key 权限
curl "http://{{MEILI_HOST}}:{{MEILI_PORT}}/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY"
```

**解决**：
- 网络不通：检查防火墙
- Key 权限不足：使用 Admin Key（非 Search Key）
- 索引不存在：首次运行会自动创建

### 20. 爬虫被目标网站封禁

**现象**：返回 403 或连接超时

**解决**：
- 降低爬取速度：`scrapy crawl trans -s DOWNLOAD_DELAY=2`
- 修改 User-Agent（在 `transspider/settings.py`）
- 使用代理（配置 `HTTP_PROXY`）

### 21. 爬虫内存不足

**现象**：爬虫进程被 OOM Killer 终止

**解决**：
```bash
# 限制爬取数量
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=1000

# 增加交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 22. add_direct_links.py 失败

**现象**：直接链接添加失败

**解决**：
- 检查 `domains.json` 格式是否正确
- 检查 Meilisearch 连接
- 检查 API Key 权限

---

## 搜索

### 23. 搜索无结果

**现象**：任何关键词都返回空结果

**排查**：
```bash
# 检查索引是否存在
curl "http://localhost:7700/indexes" \
  -H "Authorization: Bearer $MEILISEARCH_API_KEY"

# 检查文档数量
curl "http://localhost:7700/indexes/trans_resources/stats" \
  -H "Authorization: Bearer $MEILISEARCH_API_KEY"
```

**解决**：
- 索引不存在：运行爬虫
- 文档数为 0：检查爬虫是否成功完成
- API Key 错误：重新生成

### 24. 搜索结果不准确

**解决**：
- 检查 `domains.json` 中的网站是否可访问
- 检查爬虫日志是否有错误
- 考虑调整 Meilisearch 搜索设置

### 25. 搜索慢

**解决**：
- 检查服务器资源（CPU、内存）
- 检查 Meilisearch 日志
- 增加 Meilisearch 内存限制

---

## Docker

### 26. Docker 容器无法启动

**排查**：
```bash
# 查看日志
docker-compose logs

# 检查端口冲突
sudo lsof -i :7700
sudo lsof -i :80
```

### 27. Docker 网络问题

**现象**：容器间无法通信

**解决**：
```bash
# 重建网络
docker-compose down
docker network prune
docker-compose up -d
```

### 28. Docker 数据卷丢失

**现象**：重启后数据消失

**解决**：
- 确保使用命名卷（非匿名卷）
- 检查 `docker-compose.yml` 中的 `volumes` 配置
- 定期备份数据卷

---

## 性能

### 29. 网站加载慢

**解决**：
- 启用 Nginx 静态文件缓存
- 启用 Gzip 压缩
- 使用 CDN（可选）

### 30. Meilisearch 响应慢

**解决**：
- 增加内存分配
- 检查磁盘 I/O
- 考虑使用 SSD

---

## 其他

### 31. 时区问题

**现象**：日志时间不正确

**解决**：
```bash
# 设置时区
sudo timedatectl set-timezone Asia/Shanghai

# Docker 中
docker-compose -f docker-compose.full.yml exec api ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

### 32. 日志文件过大

**解决**：
```bash
# 配置 logrotate
sudo tee /etc/logrotate.d/{{SITE_NAME}} << 'EOF'
{{PROJECT_DIR}}/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### 33. 磁盘空间不足

**排查**：
```bash
# 查看空间使用
df -h
du -sh {{PROJECT_DIR}}/*
docker system df
```

**解决**：
```bash
# 清理 Docker
docker system prune -a

# 清理日志
sudo find /var/log -name "*.log" -size +100M -exec truncate -s 0 {} \;
```

### 34. 权限问题

**现象**：文件无法写入或读取

**解决**：
```bash
# 设置正确权限
sudo chown -R www-data:www-data {{PROJECT_DIR}}
sudo chmod -R 755 {{PROJECT_DIR}}
sudo chmod -R 775 {{PROJECT_DIR}}/logs
```

### 35. SELinux 阻止访问

**现象**：CentOS/RHEL 上文件无法访问

**解决**：
```bash
# 临时禁用
sudo setenforce 0

# 或配置规则
sudo chcon -R -t httpd_sys_content_t {{PROJECT_DIR}}
```

---

## 快速诊断命令

```bash
# 一键检查所有服务状态
./scripts/verify.sh

# 检查 Meilisearch
curl -s http://localhost:7700/health | jq .

# 检查 PHP
php -v
php -m | grep -E "curl|mbstring"

# 检查 Nginx
sudo nginx -t
sudo systemctl status nginx

# 检查 API
curl -s http://127.0.0.1:{{FLASK_PORT}}/api/health

# 检查爬虫（最近一次运行）
tail -50 /var/log/trans_spider.log
```

---

## 获取帮助

如果以上方案无法解决你的问题：

1. 查看详细日志：`tail -f /var/log/nginx/error.log`
2. 运行验证脚本：`./scripts/verify.sh`
3. 检查 [GitHub Issues]({{REPO_URL}}/issues)

---

## 相关文档

- [快速开始](QUICKSTART.md)
- [最小模式](MINIMAL.md)
- [完整模式](FULL.md)
- [Docker 模式](DOCKER.md)
