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

### 域名列表

- `domains.json` - 完整的域名和标签列表
- `domains_test.txt` - 测试用域名（少量）

### Meilisearch 配置

在 `transspider/config.py` 中：

```python
MEILISEARCH_HOST = "localhost"
MEILISEARCH_PORT = 7700
MEILISEARCH_INDEX = "trans_resources"
```

### PHP 前端配置

在 `frontend/index.php` 中：

```php
$MEILISEARCH_HOST = 'localhost';
$MEILISEARCH_PORT = '7700';
$MEILISEARCH_INDEX = 'trans_resources';
```

## 使用 Docker 部署（推荐）

### docker-compose.yml

```yaml
services:
  meilisearch:
    image: getmeili/meilisearch:latest
    ports:
      - "7700:7700"
    volumes:
      - meilisearch_data:/meili_data
    environment:
      - MEILI_ENV=development

volumes:
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
