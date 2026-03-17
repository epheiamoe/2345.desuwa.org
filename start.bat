@echo off
chcp 65001 >nul
echo ========================================
echo  跨性别资源搜索引擎 - 本地启动
echo ========================================
echo.

REM 检查 Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 启动 Meilisearch
echo [INFO] 启动 Meilisearch...
docker-compose up -d

if %errorlevel% neq 0 (
    echo [错误] Meilisearch 启动失败
    pause
    exit /b 1
)

echo [INFO] Meilisearch 启动完成，等待服务就绪...
timeout /t 3 /nobreak >nul

REM 启动 PHP 服务器
echo.
echo ========================================
echo  搜索页面: http://localhost:8080
echo  Meilisearch: http://localhost:7700
echo ========================================
echo.
echo 按 Ctrl+C 停止服务器

cd frontend
php -S localhost:8080
