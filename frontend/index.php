<?php
/**
 * 跨性别资源搜索引擎 - 搜索页面
 * 
 * 前端：类似谷歌的简洁搜索界面
 * 后端：调用 Meilisearch API 进行搜索
 * 
 * 配置：
 * - MEILISEARCH_HOST: Meilisearch 服务器地址
 * - MEILISEARCH_PORT: Meilisearch 端口
 * - MEILISEARCH_INDEX: 索引名称
 */

// Meilisearch 配置（本地开发用）
$MEILISEARCH_HOST = getenv('MEILISEARCH_HOST') ?: 'localhost';
$MEILISEARCH_PORT = getenv('MEILISEARCH_PORT') ?: '7700';
$MEILISEARCH_INDEX = 'trans_resources';

// 可用标签列表（从 domains.json 加载）
$availableTags = ['MtF', 'FtM', '社区', '性', '知识库', 'HRT', '指南', '报告', '学术', '影视', '音乐', '游戏', '小说', '法律', '医疗'];

// 获取搜索关键词（改用 GET 方法）
$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;
$selectedTags = isset($_GET['tags']) ? $_GET['tags'] : [];
if (!is_array($selectedTags)) {
    $selectedTags = $selectedTags ? [$selectedTags] : [];
}
$limit = 10; // 每页显示 10 条
$offset = ($page - 1) * $limit;
$results = [];
$totalHits = 0;
$searchTime = 0;
$error = '';

// 搜索请求
if ($query) {
    // 简单的速率限制（基于 IP）
    $rateLimitFile = sys_get_temp_dir() . '/search_rate_' . md5($_SERVER['REMOTE_ADDR']);
    $now = time();
    
    // 检查是否超过限制（每分钟 20 次）
    if (file_exists($rateLimitFile)) {
        $rateData = json_decode(file_get_contents($rateLimitFile), true);
        if ($rateData && ($now - $rateData['time']) < 60) {
            if ($rateData['count'] >= 20) {
                $error = '搜索次数超限，请稍后再试';
            } else {
                $rateData['count']++;
                file_put_contents($rateLimitFile, json_encode($rateData));
            }
        } else {
            $rateData = ['time' => $now, 'count' => 1];
            file_put_contents($rateLimitFile, json_encode($rateData));
        }
    } else {
        $rateData = ['time' => $now, 'count' => 1];
        file_put_contents($rateLimitFile, json_encode($rateData));
    }
    
    // 调用 Meilisearch API
    if (!$error) {
        $url = "http://{$MEILISEARCH_HOST}:{$MEILISEARCH_PORT}/indexes/{$MEILISEARCH_INDEX}/search";
        
        // 构建搜索参数
        $searchParams = [
            'q' => $query,
            'limit' => $limit,
            'offset' => $offset,
            'attributesToHighlight' => ['title', 'content'],
            'highlightPreTag' => '<em>',
            'highlightPostTag' => '</em>',
            'attributesToCrop' => ['content'],
            'cropLength' => 200,
        ];
        
        // 添加标签筛选
        if (!empty($selectedTags)) {
            $filters = [];
            foreach ($selectedTags as $tag) {
                $filters[] = "tags = '{$tag}'";
            }
            $searchParams['filter'] = implode(' OR ', $filters);
        }
        
        $postData = json_encode($searchParams);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
        ]);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode === 200) {
            $data = json_decode($response, true);
            $results = $data['hits'] ?? [];
            $totalHits = $data['estimatedTotalHits'] ?? 0;
            $searchTime = $data['processingTimeMs'] ?? 0;
        } else {
            $error = "搜索服务暂时不可用 (HTTP {$httpCode})";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2345.desuwa.org - 跨性别资源搜索</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #fff;
            color: #333;
            line-height: 1.6;
        }
        
        /* 头部 */
        .header {
            padding: 20px 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .logo {
            font-size: 24px;
            font-weight: bold;
            color: #1a73e8;
            text-decoration: none;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
        }
        
        .nav-links a {
            color: #666;
            text-decoration: none;
            font-size: 14px;
        }
        
        .nav-links a:hover {
            color: #1a73e8;
        }
        
        /* 主内容区 */
        .main {
            max-width: 800px;
            margin: 0 auto;
            padding: 60px 20px;
            text-align: center;
        }
        
        /* 搜索框 */
        .search-box {
            margin-bottom: 40px;
        }
        
        .search-form {
            display: flex;
            max-width: 600px;
            margin: 0 auto;
            border: 1px solid #dfe1e5;
            border-radius: 24px;
            padding: 8px 16px;
            box-shadow: 0 1px 6px rgba(32,33,36,0.28);
        }
        
        .search-form:hover {
            box-shadow: 0 1px 6px rgba(32,33,36,0.4);
        }
        
        .search-input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 16px;
            padding: 8px 0;
        }
        
        .search-btn {
            background: #1a73e8;
            color: #fff;
            border: none;
            padding: 8px 20px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }
        
        .search-btn:hover {
            background: #1557b0;
        }
        
        /* 标签筛选 */
        .tag-filter {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            margin-bottom: 20px;
        }
        
        .tag-filter label {
            display: inline-block;
            padding: 4px 12px;
            border: 1px solid #dfe1e5;
            border-radius: 16px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .tag-filter label:hover {
            background: #f1f3f4;
        }
        
        .tag-filter input[type="checkbox"] {
            display: none;
        }
        
        .tag-filter input[type="checkbox"]:checked + span {
            background: #1a73e8;
            color: white;
            border-color: #1a73e8;
        }
        
        .tag-filter label:has(input:checked) {
            background: #e8f0fe;
            border-color: #1a73e8;
            color: #1a73e8;
        }
        
        /* 搜索结果 */
        .results-info {
            text-align: left;
            margin-bottom: 20px;
            color: #666;
            font-size: 14px;
        }
        
        .results-list {
            text-align: left;
        }
        
        .result-item {
            margin-bottom: 30px;
        }
        
        /* 分页 */
        .pagination {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 30px 0;
        }
        
        .pagination a, .pagination span {
            padding: 8px 16px;
            border: 1px solid #dfe1e5;
            border-radius: 4px;
            text-decoration: none;
            color: #1a73e8;
        }
        
        .pagination a:hover {
            background: #f1f3f4;
        }
        
        .pagination .current {
            background: #1a73e8;
            color: white;
            border-color: #1a73e8;
        }
        
        .result-title {
            font-size: 20px;
            margin-bottom: 5px;
        }
        
        .result-title a {
            color: #1a0dab;
            text-decoration: none;
        }
        
        .result-title a:hover {
            text-decoration: underline;
        }
        
        .result-url {
            color: #006621;
            font-size: 14px;
            margin-bottom: 5px;
        }
        
        .result-snippet {
            color: #545454;
            font-size: 14px;
            line-height: 1.58;
        }
        
        .result-snippet em {
            font-style: normal;
            color: #5f6368;
            background: #f1f3f4;
            padding: 0 2px;
        }
        
        .no-results {
            color: #666;
            margin: 40px 0;
        }
        
        .error-msg {
            color: #d93025;
            background: #fce8e6;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        
        /* 底部 */
        .footer {
            background: #f2f2f2;
            padding: 20px 40px;
            margin-top: 40px;
        }
        
        .footer-content {
            max-width: 800px;
            margin: 0 auto;
            font-size: 14px;
            color: #666;
        }
        
        .disclaimer {
            background: #fff3cd;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #856404;
        }
        
        /* TODO: LLM 概览区域 */
        .ai-overview {
            background: #e8f0fe;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            text-align: left;
        }
        
        .ai-overview h3 {
            color: #1a73e8;
            font-size: 16px;
            margin-bottom: 10px;
        }
        
        .ai-overview p {
            color: #5f6368;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="logo">2345.desuwa.org</a>
        <div class="nav-links">
            <a href="https://2345.lgbt" target="_blank">2345.lgbt 导航站</a>
        </div>
    </div>
    
    <div class="main">
        <div class="search-box">
            <form method="GET" action="" class="search-form">
                <input 
                    type="text" 
                    name="q" 
                    class="search-input" 
                    placeholder="搜索跨性别资源..." 
                    value="<?php echo htmlspecialchars($query); ?>"
                    autofocus
                >
                <button type="submit" class="search-btn">搜索</button>
            </form>
            
            <!-- 标签筛选 -->
            <div class="tag-filter">
                <?php foreach ($availableTags as $tag): ?>
                    <label>
                        <input type="checkbox" name="tags[]" value="<?php echo htmlspecialchars($tag); ?>"
                            <?php echo in_array($tag, $selectedTags) ? 'checked' : ''; ?>>
                        <span><?php echo htmlspecialchars($tag); ?></span>
                    </label>
                <?php endforeach; ?>
            </div>
        </div>
        
        <?php if ($error): ?>
            <div class="error-msg"><?php echo htmlspecialchars($error); ?></div>
        <?php endif; ?>
        
        <?php if ($query && !$error): ?>
            <div class="results-info">
                找到约 <?php echo number_format($totalHits); ?> 个结果 
                (<?php echo $searchTime; ?> 毫秒)
            </div>
            
            <?php if (empty($results)): ?>
                <div class="no-results">
                    <p>没有找到相关结果，请尝试其他关键词</p>
                </div>
            <?php else: ?>
                <div class="results-list">
                    <?php foreach ($results as $result): ?>
                        <div class="result-item">
                            <div class="result-title">
                                <a href="<?php echo htmlspecialchars($result['url']); ?>" target="_blank">
                                    <?php echo !empty($result['_formatted']['title']) ? $result['_formatted']['title'] : htmlspecialchars($result['title']); ?>
                                </a>
                            </div>
                            <div class="result-url"><?php echo htmlspecialchars($result['domain']); ?></div>
                            <div class="result-snippet">
                                <?php if (!empty($result['_formatted']['content'])): ?>
                                    <?php echo $result['_formatted']['content']; ?>
                                <?php else: ?>
                                    <?php echo htmlspecialchars(mb_substr($result['content'], 0, 200)); ?>...
                                <?php endif; ?>
                            </div>
                        </div>
                    <?php endforeach; ?>
                </div>
                
                <?php
                // 生成分页（使用 GET 方法）
                $totalPages = ceil($totalHits / $limit);
                if ($totalPages > 1):
                    // 构建基础 URL 参数
                    $baseParams = 'q=' . urlencode($query);
                    foreach ($selectedTags as $tag) {
                        $baseParams .= '&tags[]=' . urlencode($tag);
                    }
                ?>
                <div class="pagination">
                    <?php if ($page > 1): ?>
                        <a href="?<?php echo $baseParams; ?>&page=<?php echo $page-1; ?>">上一页</a>
                    <?php endif; ?>
                    
                    <?php
                    $startPage = max(1, $page - 2);
                    $endPage = min($totalPages, $page + 2);
                    for ($i = $startPage; $i <= $endPage; $i++):
                    ?>
                        <?php if ($i == $page): ?>
                            <span class="current"><?php echo $i; ?></span>
                        <?php else: ?>
                            <a href="?<?php echo $baseParams; ?>&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                        <?php endif; ?>
                    <?php endfor; ?>
                    
                    <?php if ($page < $totalPages): ?>
                        <a href="?<?php echo $baseParams; ?>&page=<?php echo $page+1; ?>">下一页</a>
                    <?php endif; ?>
                </div>
                <?php endif; ?>
            <?php endif; ?>
            
            <!-- TODO: LLM 概览区域 -->
            <div class="ai-overview">
                <h3>AI 智能摘要（开发中）</h3>
                <p>此功能正在开发中，预计后续版本将提供LLM智能摘要功能。</p>
            </div>
        <?php endif; ?>
    </div>
    
    <div class="footer">
        <div class="footer-content">
            <div class="disclaimer">
                <strong>免责声明：</strong>本搜索引擎仅收录 2345.lgbt 公开资源，仅供参考。医疗问题请咨询专业医生，本网站不承担任何责任。
            </div>
            <p>© 2026 2345.desuwa.org | 数据来源：<a href="https://2345.lgbt" target="_blank">2345.lgbt</a></p>
        </div>
    </div>
</body>
</html>
