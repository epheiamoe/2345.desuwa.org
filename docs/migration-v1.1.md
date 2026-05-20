# 迁移指南：v1.1 → v1.3

> 本文档指导您从旧版本迁移到 v1.3，包含新组件启用、数据库迁移和回滚步骤。

## 概述

v1.3 是一次安全加固和架构重构版本，主要变更：

- **数据库**：JSON 文件 → SQLite（解决竞争条件）
- **速率限制**：内存存储 → SQLite 滑动窗口
- **配置管理**：分散硬编码 → 统一 .env + config.json
- **前端**：单体文件 → 视图/逻辑分离
- **文档 ID**：MD5 → SHA-256（防冲突）

## 迁移前准备

### 1. 备份现有数据

```bash
# 备份 API 数据库
cp api/db.json api/db.json.backup.$(date +%Y%m%d)

# 备份配置文件
cp api/.env api/.env.backup.$(date +%Y%m%d) 2>/dev/null || true

# 备份 Meilisearch 数据（如使用 Docker）
docker cp trans_meilisearch:/meili_data ./meili_data_backup
```

### 2. 确认当前版本

```bash
cd /www/wwwroot/2345.desuwa.org
git log --oneline -1
# 或检查 CHANGELOG.md 中的版本号
```

## 迁移步骤

### 步骤 1：更新代码

```bash
cd /www/wwwroot/2345.desuwa.org
git pull origin main
# 或使用 scp 上传新文件
```

### 步骤 2：安装新依赖

```bash
cd api
pip install -r requirements.txt
# 确保包含：flask, flask-cors, meilisearch, requests, python-dotenv
```

### 步骤 3：创建/更新配置文件

#### 3.1 创建 .env 文件（如不存在）

```bash
cp env.example .env
```

编辑 `.env`，确保包含以下变量：

```bash
# 必填
FLASK_SECRET=your_random_secret_key_at_least_32_chars

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Meilisearch
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_API_KEY=your_search_key
MEILI_MASTER_KEY=your_master_key

# 站点
SITE_URL=https://your-domain.com

# 管理员（逗号分隔）
ADMIN_USERS=your_github_username

# API 端口
API_PORT=5000
```

#### 3.2 确认 config.json

检查项目根目录的 `config.json` 是否存在且格式正确：

```bash
cat ../config.json | python -m json.tool > /dev/null && echo "JSON valid" || echo "JSON invalid"
```

### 步骤 4：数据库迁移（JSON → SQLite）

```bash
cd /www/wwwroot/2345.desuwa.org

# 运行迁移脚本
python scripts/migrate_db.py \
  --source api/db.json \
  --target api/db.sqlite

# 预期输出：
# 开始迁移: api/db.json -> api/db.sqlite
# 已加载 JSON 数据
# 已迁移 X 个用户
# 已迁移 Y 个 API Key
# 迁移完成!
```

迁移完成后，验证数据库：

```bash
sqlite3 api/db.sqlite ".tables"
# 应输出：api_keys  rate_limits  users
```

### 步骤 5：更新 Nginx 配置

在 Nginx 配置中添加环境变量传递（PHP-FPM 需要）：

```nginx
location ~ \.php$ {
    include fastcgi_params;
    fastcgi_pass unix:/tmp/php-cgi-84.sock;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    
    # 新增：传递 Meilisearch API Key 给 PHP
    fastcgi_param MEILISEARCH_API_KEY your_search_key;
    fastcgi_param MEILISEARCH_HOST localhost;
    fastcgi_param MEILISEARCH_PORT 7700;
}
```

测试并重载 Nginx：

```bash
nginx -t
systemctl reload nginx
```

### 步骤 6：重启服务

```bash
# 重启 Flask API
pkill -f 'python.*api/app.py'
cd api
MEILISEARCH_API_KEY=your_key nohup python app.py > /var/log/api.log 2>&1 &

# 检查 API 健康状态
curl http://127.0.0.1:5000/api/health
# 应返回：{"status": "ok"}
```

### 步骤 7：运行健康检查

```bash
cd /www/wwwroot/2345.desuwa.org
bash scripts/health_check.sh
```

### 步骤 8：验证搜索功能

```bash
# 测试前端搜索
curl -s "https://your-domain.com/?q=HRT" | grep "找到约"

# 测试 API 搜索（需要有效 API Key）
curl "https://your-domain.com/api/search?q=HRT" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 环境变量配置参考

### 必需变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `FLASK_SECRET` | Flask Session 密钥（≥32字符） | `openssl rand -hex 32` |
| `GITHUB_CLIENT_ID` | GitHub OAuth App ID | `Iv23lixxx...` |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth Secret | `a1b2c3...` |
| `MEILISEARCH_API_KEY` | Meilisearch Search Key | 从 Meilisearch 生成 |

### 可选变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MEILISEARCH_HOST` | `localhost` | Meilisearch 主机 |
| `MEILISEARCH_PORT` | `7700` | Meilisearch 端口 |
| `SITE_URL` | `https://2345.desuwa.org` | 站点 URL |
| `ADMIN_USERS` | `''` | 管理员用户名（逗号分隔） |
| `API_PORT` | `5000` | API 服务端口 |

### 速率限制变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `RATE_LIMIT_PER_MINUTE` | `10` | 每分钟请求数 |
| `RATE_LIMIT_PER_DAY` | `1000` | 每天请求数 |
| `RATE_LIMIT_PER_MONTH` | `2000` | 每月请求数 |

## 数据库迁移详情

### 从 db.json 迁移到 SQLite

迁移脚本 `scripts/migrate_db.py` 会自动：

1. **读取** `api/db.json` 中的用户和 API Key 数据
2. **创建** `api/db.sqlite`（如不存在）
3. **导入** 数据到 SQLite 表结构
4. **保留** 原有 JSON 文件作为备份

### 新表结构

```sql
-- API Keys 表
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    github_id TEXT,
    github_login TEXT,
    email TEXT,
    avatar_url TEXT,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 速率限制表（滑动窗口）
CREATE TABLE rate_limits (
    key TEXT PRIMARY KEY,
    minute_count INTEGER DEFAULT 0,
    day_count INTEGER DEFAULT 0,
    month_count INTEGER DEFAULT 0,
    minute_reset INTEGER,
    day_reset INTEGER,
    month_reset INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 使用审计日志
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 手动验证迁移

```bash
sqlite3 api/db.sqlite "SELECT COUNT(*) FROM users;"
sqlite3 api/db.sqlite "SELECT COUNT(*) FROM api_keys;"
```

## 回滚步骤

如果迁移后出现问题，可按以下步骤回滚：

### 方案 A：使用迁移脚本回滚（推荐）

```bash
cd /www/wwwroot/2345.desuwa.org

# 自动回滚到最近的备份
python scripts/migrate_db.py \
  --source api/db.json \
  --target api/db.sqlite \
  --rollback

# 回滚会：
# 1. 备份当前 SQLite 数据库
# 2. 恢复最近的 .backup 文件
```

### 方案 B：手动回滚

```bash
cd /www/wwwroot/2345.desuwa.org

# 1. 停止 API 服务
pkill -f 'python.*api/app.py'

# 2. 恢复数据库（如有备份）
cp api/db.sqlite.backup.20260520_120000 api/db.sqlite

# 3. 或切换回 JSON 模式（修改 app.py 配置）
# 将 DB_PATH 改回 api/db.json

# 4. 重启 API
cd api
python app.py &
```

### 方案 C：完全回滚代码

```bash
cd /www/wwwroot/2345.desuwa.org

# 回滚到上一个版本
git log --oneline -5
git reset --hard HEAD~1

# 恢复配置文件
cp api/.env.backup.20260520 api/.env

# 重启服务
pkill -f 'python.*api/app.py'
cd api && python app.py &
```

## 常见问题

### Q: 迁移后 API Key 失效？

A: 检查 `api/db.sqlite` 中是否包含该 key：

```bash
sqlite3 api/db.sqlite "SELECT * FROM api_keys WHERE key = 'your-key';"
```

如不存在，检查迁移日志是否有报错，或手动重新生成。

### Q: 速率限制不生效？

A: 确认 `api/app.py` 已集成新组件。当前版本中，新组件（`rate_limiter.py`、`database.py`）已创建但未在 `app.py` 中使用。需要手动修改 `app.py` 以使用新组件。

### Q: PHP 前端无法连接 Meilisearch？

A: 检查 Nginx 配置中是否正确传递了环境变量：

```bash
grep -A5 "fastcgi_param MEILISEARCH" /etc/nginx/sites-enabled/your-site
```

### Q: SQLite 数据库权限错误？

A: 确保 web 服务器用户有写入权限：

```bash
chown www-data:www-data api/db.sqlite
chmod 644 api/db.sqlite
```

## 迁移检查清单

- [ ] 已备份 `api/db.json`
- [ ] 已备份 `api/.env`
- [ ] 已更新 `.env` 文件
- [ ] 已确认 `config.json` 格式正确
- [ ] 已运行数据库迁移脚本
- [ ] 已验证 SQLite 表结构
- [ ] 已更新 Nginx 配置
- [ ] 已重启 Flask API
- [ ] 已测试前端搜索
- [ ] 已测试 API 搜索
- [ ] 已运行健康检查脚本

---

**注意**：当前版本中新组件（`rate_limiter.py`、`database.py`、`validators.py`、`config.py`）已创建，但 `api/app.py` 尚未集成。如需启用新功能，请手动修改 `app.py` 导入并使用这些组件。
