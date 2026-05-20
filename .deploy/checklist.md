# 子代理实施清单

## 批次1: 配置系统 + License提取（并行3个子代理）

### 子代理A: 配置系统改造
**任务**: 
1. 读取 `.deploy/design.md` Section 2
2. 修改 `config.json` 添加 `deploy` 字段
3. 创建 `.env.minimal.example` 和 `.env.full.example`
4. 修改 `frontend/config.php` 支持读取 `deploy` 配置
5. 修改 `frontend/index.php` 和 `frontend/template.php` 根据 `ENABLE_API`/`ENABLE_OAUTH` 条件显示/隐藏元素
6. 创建 `frontend/manifest.php`（动态生成manifest）

**参考文件**:
- `.deploy/design.md`
- `frontend/config.php`（现有）
- `frontend/index.php`（现有）
- `frontend/template.php`（现有）

**输出**: 修改后的文件列表

### 子代理B: install.sh 部署向导
**任务**:
1. 读取 `.deploy/design.md` Section 3, 4.1
2. 创建 `scripts/install.sh`
3. 支持交互式和非交互式（--auto）
4. 支持三种模式: minimal, full, docker
5. 环境检测（PHP, Docker, Python, Nginx）
6. 生成配置文件（.env, config.json）
7. 启动 Meilisearch（Docker）
8. 输出下一步提示

**参考文件**:
- `.deploy/design.md`
- `.env.example`（现有）
- `config.json`（现有）
- `docker-compose.yml`（现有）

**输出**: scripts/install.sh

### 子代理C: License提取与显示
**任务**:
1. 读取 `.deploy/design.md` Section 5
2. 修改 `transspider/pipelines.py` 添加 license 提取逻辑
3. 修改 `transspider/items.py`（或创建）定义 license 字段
4. 修改 Meilisearch schema（在 pipelines.py 中）添加 license 字段
5. 修改 `frontend/search.php` 在搜索结果中显示 license 标识
6. 修改 `frontend/template.php` 添加 license 显示HTML

**参考文件**:
- `.deploy/design.md`
- `transspider/pipelines.py`（现有）
- `frontend/search.php`（现有）
- `frontend/template.php`（现有）

**输出**: 修改后的爬虫和前端文件

---

## 批次2: 品牌替换 + 文档（并行3个子代理）

### 子代理D: rebrand.sh + verify.sh
**任务**:
1. 读取 `.deploy/design.md` Section 4.2, 4.3
2. 创建 `scripts/rebrand.sh`（交互式和非交互式）
3. 创建 `scripts/verify.sh`（部署验证）
4. rebrand.sh 替换清单：
   - config.json 中的站点信息
   - .env 中的域名
   - frontend/ 中的默认回退值
   - docs/ 中的品牌引用
   - scripts/ 中的路径

**参考文件**:
- `.deploy/design.md`
- `config.json`（现有）
- `.env.example`（现有）

**输出**: scripts/rebrand.sh, scripts/verify.sh

### 子代理E: Nginx配置模板
**任务**:
1. 读取 `.deploy/design.md` Section 3
2. 创建 `config/examples/nginx.minimal.conf`
3. 创建 `config/examples/nginx.full.conf`
4. 创建 `config/examples/systemd.api.service`（完整模式Flask服务）
5. 创建 `config/examples/crontab.crawler`（爬虫定时任务）
6. 所有模板使用 `{{PLACEHOLDER}}` 格式

**参考文件**:
- `.deploy/design.md`
- `AGENTS.md` 中的 Nginx 配置示例

**输出**: config/examples/*

### 子代理F: 部署文档
**任务**:
1. 读取 `.deploy/design.md` Section 6
2. 创建 `docs/deploy/QUICKSTART.md`（5分钟上手）
3. 创建 `docs/deploy/MINIMAL.md`（最小模式详解）
4. 创建 `docs/deploy/FULL.md`（完整模式+OAuth配置）
5. 创建 `docs/deploy/DOCKER.md`（Docker模式）
6. 创建 `docs/deploy/REBRAND.md`（品牌替换）
7. 创建 `docs/deploy/TROUBLESHOOTING.md`（常见问题）

**参考文件**:
- `.deploy/design.md`
- `README.md`（现有）
- `AGENTS.md`（现有部署说明）

**输出**: docs/deploy/*.md

---

## 批次3: 整合与提交（主代理执行）

### 主代理任务:
1. 检查所有子代理输出
2. 验证文件完整性
3. 执行6个原子化提交
4. 验证提交历史

---

## 执行顺序

```
批次1（并行A+B+C）
    │
    ▼
批次2（并行D+E+F）
    │
    ▼
批次3（主代理整合提交）
```

---

## 关键约束

1. **不要修改已有提交**: 新功能只在 feat/easy-deploy 分支
2. **保持向后兼容**: 现有功能不受影响
3. **最小侵入**: 尽量新增文件，少改现有文件
4. **通用占位符**: 所有脚本使用 `{{DOMAIN}}` 而非真实域名
5. **文档先行**: 每个功能必须有文档说明
