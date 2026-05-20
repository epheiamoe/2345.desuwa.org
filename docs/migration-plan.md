# 生产环境迁移计划 v1.1

## 版本: 1.0
## 日期: 2026-05-20
## 状态: 待执行

---

## 1. 迁移前准备

### 1.1 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| db.json 迁移失败 | 低 | 高 | 迁移前完整备份，脚本支持回滚 |
| Meilisearch 版本不兼容 | 中 | 高 | 先在测试环境验证 v1.6 |
| API 配置加载失败 | 低 | 高 | 保留旧 .env 格式兼容性 |
| 前端 XSS 修复引入显示问题 | 低 | 中 | 测试搜索高亮显示 |
| 爬虫 ID 变更导致重复索引 | 中 | 中 | 重建索引或清理旧数据 |

### 1.2 备份清单

```bash
# 1. 备份代码（当前分支已包含所有修改）
git branch backup/pre-refactor-$(date +%Y%m%d)
git add -A
git stash  # 或提交到临时分支

# 2. 备份数据库
cp api/db.json api/db.json.backup.$(date +%Y%m%d)

# 3. 备份 Meilisearch 数据
curl -X POST "http://localhost:7700/indexes/trans_resources/documents" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -o meilisearch_backup_$(date +%Y%m%d).json

# 4. 备份 Nginx 配置
cp /etc/nginx/sites-available/2345.desuwa.org \
   nginx_backup_$(date +%Y%m%d).conf

# 5. 备份环境变量
cp .env .env.backup.$(date +%Y%m%d)
```

### 1.3 测试环境验证

在测试环境（或本地）执行：
1. 检出 refactor 分支
2. 运行数据库迁移脚本
3. 验证搜索功能
4. 验证 OAuth 登录
5. 验证管理员功能
6. 运行爬虫测试索引

---

## 2. 迁移步骤

### 阶段 1: 准备新配置（零停机）

```bash
# 1. 上传新配置文件（不影响当前服务）
scp config.json myvps:/www/wwwroot/2345.desuwa.org/
scp .env.example myvps:/www/wwwroot/2345.desuwa.org/

# 2. 在服务器上创建 .env
cd /www/wwwroot/2345.desuwa.org
cp .env.example .env
# 编辑 .env 填入实际值（保持与现有配置一致）
nano .env
```

### 阶段 2: 数据库迁移（计划停机 5 分钟）

```bash
# 1. 进入维护模式（可选：显示维护页面）
# nginx 配置中添加维护页面

# 2. 停止 Flask API
pkill -f 'python.*api/app.py'

# 3. 运行数据库迁移
python scripts/migrate_db.py

# 4. 验证迁移结果
python -c "from api.database import db; print(len(db.list_api_keys()))"
```

### 阶段 3: 更新 Meilisearch（计划停机 10 分钟）

```bash
# 1. 导出当前索引
curl -X POST "http://localhost:7700/indexes/trans_resources/documents" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -o /tmp/meilisearch_backup.json

# 2. 停止 Meilisearch
docker-compose down

# 3. 更新 docker-compose.yml（已包含版本固定）
cp docker-compose.yml /www/wwwroot/2345.desuwa.org/

# 4. 拉取新版本并启动
docker-compose pull
docker-compose up -d

# 5. 等待服务就绪（健康检查）
./scripts/health_check.sh

# 6. 重建索引（如果需要）
# python add_direct_links.py
```

### 阶段 4: 部署新代码（计划停机 5 分钟）

```bash
# 1. 上传新代码
# frontend/
# api/
# transspider/
# scripts/

# 2. 安装 Python 依赖
cd /www/wwwroot/2345.desuwa.org/api
pip install -r requirements.txt

# 3. 验证配置加载
python -c "from api.config import config; print(config.meilisearch_url)"

# 4. 启动 Flask API（使用 Gunicorn）
# 方法 A: 直接启动
gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app

# 方法 B: 使用 nohup（当前方式兼容）
nohup gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app > /var/log/api.log 2>&1 &

# 5. 验证 API
./scripts/health_check.sh
```

### 阶段 5: 前端部署（零停机）

```bash
# 1. 上传 PHP 文件
# frontend/*.php
# frontend/*.css
# frontend/*.js

# 2. 验证 PHP 语法
php -l /www/wwwroot/2345.desuwa.org/frontend/index.php
php -l /www/wwwroot/2345.desuwa.org/frontend/config.php
php -l /www/wwwroot/2345.desuwa.org/frontend/functions.php

# 3. 配置 Nginx 传递环境变量
# 在 nginx.conf 中添加：
# fastcgi_param MEILISEARCH_API_KEY your_search_key;
# fastcgi_param SITE_URL https://2345.desuwa.org;

# 4. 重载 Nginx
nginx -s reload
```

### 阶段 6: 验证（零停机）

```bash
# 1. 运行健康检查
./scripts/health_check.sh

# 2. 手动验证功能
curl "https://2345.desuwa.org/?q=HRT"
curl -H "X-API-Key: YOUR_KEY" "https://2345.desuwa.org/api/search?q=test"

# 3. 检查日志
tail -f /var/log/api.log
tail -f /var/log/nginx/access.log
```

---

## 3. 回滚计划

### 3.1 触发回滚的条件

- API 无法启动或持续 500 错误
- 数据库迁移后数据丢失
- 搜索功能完全不可用
- OAuth 登录失败
- 超过 30 分钟无法恢复

### 3.2 回滚步骤（10 分钟内完成）

```bash
# 1. 停止新服务
pkill -f gunicorn
pkill -f 'python.*api/app.py'

# 2. 恢复旧代码
cd /www/wwwroot/2345.desuwa.org
git checkout backup/pre-refactor-$(date +%Y%m%d) -- .

# 3. 恢复旧数据库
cp api/db.json.backup.$(date +%Y%m%d) api/db.json
rm -f api/db.sqlite api/db.sqlite-journal

# 4. 恢复 Meilisearch（如果更新了版本）
docker-compose down
docker-compose pull getmeili/meilisearch:latest  # 回退到 latest
docker-compose up -d

# 5. 启动旧版 API
cd api
nohup python app.py > /var/log/api.log 2>&1 &

# 6. 验证回滚
curl "https://2345.desuwa.org/?q=test"
```

### 3.3 数据恢复

如果 db.json 迁移后有问题：
```bash
# 从备份恢复
python scripts/migrate_db.py --rollback
# 或
rm api/db.sqlite
cp api/db.json.backup.$(date +%Y%m%d) api/db.json
```

---

## 4. 迁移后验证清单

### 4.1 功能验证

- [ ] 首页搜索正常显示
- [ ] 搜索高亮显示正确（无 XSS）
- [ ] 标签筛选正常
- [ ] 语言筛选正常
- [ ] 分页正常
- [ ] 暗黑模式切换正常
- [ ] PWA 安装正常

### 4.2 API 验证

- [ ] `/api/search` 返回正确结果
- [ ] 速率限制生效（测试超过 10 次/分钟）
- [ ] OAuth 登录流程正常
- [ ] API Key 认证正常
- [ ] 管理员接口正常
- [ ] Cookie 安全属性正确（Secure, HttpOnly, SameSite）

### 4.3 爬虫验证

- [ ] 爬虫正常启动
- [ ] 索引文档 ID 使用 SHA-256
- [ ] 无重复索引
- [ ] 批量推送正常

### 4.4 性能验证

- [ ] 页面加载时间 < 2s
- [ ] API 响应时间 < 500ms
- [ ] Meilisearch 响应正常

### 4.5 安全验证

- [ ] XSS payload 不执行
- [ ] API 错误不泄露内部信息
- [ ] 未认证请求被拒绝
- [ ] 速率限制正常工作

---

## 5. 后续优化（迁移后 1 周内）

1. **监控**: 检查日志是否有异常
2. **性能**: 根据实际负载调整 Gunicorn worker 数
3. **Redis**: 如果负载高，启用 Redis 替代 SQLite 速率限制
4. **索引重建**: 考虑重建 Meilisearch 索引以使用新 ID 格式
5. **清理**: 删除临时备份文件（保留最近 3 个）

---

## 6. 联系方式

迁移期间如有问题：
- 检查 `scripts/health_check.sh` 输出
- 查看 `/var/log/api.log`
- 回滚到 `backup/pre-refactor-*` 分支

---

*本文档为生产环境迁移的标准操作程序（SOP），执行前请仔细阅读并确认所有备份已完成。*
