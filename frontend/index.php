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

// 可用语言列表
$availableLanguages = [
    'zh-cn' => '简体中文',
    'zh-hant' => '繁體中文',
    'zh' => '中文',
    'en' => 'English',
    'ja' => '日本語',
    'es' => 'Español',
    'nl' => 'Nederlands',
];

// 获取索引总数
$statsUrl = "http://{$MEILISEARCH_HOST}:{$MEILISEARCH_PORT}/indexes/{$MEILISEARCH_INDEX}/stats";
$statsJson = @file_get_contents($statsUrl);
$totalDocs = 0;
if ($statsJson) {
    $stats = json_decode($statsJson, true);
    $totalDocs = $stats['numberOfDocuments'] ?? 0;
}

// 获取搜索关键词（改用 GET 方法）
$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;

// 处理标签筛选 - PHP 对多个同名 GET 参数处理有问题
$selectedTags = [];
if (isset($_GET['tags'])) {
    $tagsParam = $_GET['tags'];
    if (is_array($tagsParam)) {
        $selectedTags = $tagsParam;
    } elseif (is_string($tagsParam) && $tagsParam) {
        // 尝试解析逗号分隔的标签
        $selectedTags = array_filter(array_map('trim', explode(',', $tagsParam)));
    }
}

// 处理站点筛选
$selectedSite = isset($_GET['site']) ? trim($_GET['site']) : '';

// 处理语言筛选
$selectedLang = isset($_GET['lang']) ? trim($_GET['lang']) : '';
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
        
        // 添加站点筛选
        if (!empty($selectedSite)) {
            $existingFilter = $searchParams['filter'] ?? '';
            $siteFilter = "domain = '{$selectedSite}'";
            $searchParams['filter'] = $existingFilter ? "({$existingFilter}) AND {$siteFilter}" : $siteFilter;
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
            
            // 添加语言筛选（前端过滤）
            if (!empty($selectedLang)) {
                $filteredResults = [];
                foreach ($results as $r) {
                    $url = $r['url'] ?? '';
                    $lang = 'zh-cn';  // 默认中文简体
                    if (preg_match('/\/zh-hant\//', $url) || preg_match('/\/zh-tw\//', $url) || preg_match('/\/zh-hk\//', $url)) {
                        $lang = 'zh-hant';
                    } elseif (preg_match('/\/zh-cn\//', $url) || preg_match('/\/zh-\w+\//', $url)) {
                        $lang = 'zh-cn';
                    } elseif (preg_match('/\/en\//', $url)) {
                        $lang = 'en';
                    } elseif (preg_match('/\/ja\//', $url)) {
                        $lang = 'ja';
                    } elseif (preg_match('/\/es\//', $url)) {
                        $lang = 'es';
                    } elseif (preg_match('/\/nl\//', $url)) {
                        $lang = 'nl';
                    }
                    
                    // 兼容处理：zh = 所有中文
                    $match = false;
                    if ($selectedLang === 'zh') {
                        $match = in_array($lang, ['zh-cn', 'zh-hant']);
                    } else {
                        $match = ($lang === $selectedLang);
                    }
                    
                    if ($match) {
                        $filteredResults[] = $r;
                    }
                }
                $results = $filteredResults;
                $totalHits = count($results);
            }
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
    <link rel="stylesheet" href="style.css?v=6">
</head>
<body>
    <div class="header">
        <a href="<?php echo $selectedLang ? '/?lang=' . htmlspecialchars($selectedLang) : '/'; ?>" class="logo">2345.desuwa.org</a>
        <div class="nav-links">
            <a href="https://2345.lgbt" target="_blank">2345.lgbt 导航站</a>
            <a href="https://github.com/epheiamoe/2345.desuwa.org" target="_blank" style="color:#1a73e8;">⭐ 开源</a>
            <a href="/api/console.html" target="_blank">API 控制台</a>
            <a href="/docs/api.html" target="_blank">API 文档</a>
            <a href="javascript:toggleTheme()" id="theme-toggle" title="切换主题">🌙</a>
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
                <input type="hidden" name="tags" id="tags-input" value="<?php echo htmlspecialchars(implode(',', $selectedTags)); ?>">
                <input type="hidden" name="lang" id="lang-input" value="<?php echo htmlspecialchars($selectedLang); ?>">
                <button type="submit" class="search-btn">搜索</button>
            </form>
            
            <!-- 语言筛选（搜索框下方） -->
            <div style="margin-top:12px;">
                <span style="color:#666;font-size:13px;margin-right:8px;">语言：</span>
                <?php foreach ($availableLanguages as $langCode => $langName): ?>
                    <a href="?q=<?php echo urlencode($query); ?><?php if($selectedTags): foreach($selectedTags as $t): ?>&tags=<?php echo urlencode($t); endforeach; endif; ?>&lang=<?php echo urlencode($langCode); ?>" 
                       class="lang-link <?php echo $selectedLang === $langCode ? 'active' : ''; ?>">
                        <?php echo htmlspecialchars($langName); ?>
                    </a>
                <?php endforeach; ?>
                <a href="?q=<?php echo urlencode($query); ?><?php if($selectedTags): foreach($selectedTags as $t): ?>&tags=<?php echo urlencode($t); endforeach; endif; ?>" 
                   class="lang-link <?php echo $selectedLang === '' ? 'active' : ''; ?>">
                    全部
                </a>
            </div>
            
            <?php if (!$query): ?>
            <p style="margin-top:15px;color:#666;font-size:14px;">共收录 <?php echo number_format($totalDocs); ?> 条跨性别资源</p>
            <?php endif; ?>
            
            <!-- 标签筛选 -->
            <div style="margin-top:10px;">
                <span style="color:#666;font-size:13px;margin-right:8px;">标签：</span>
                <?php foreach ($availableTags as $i => $tag): ?>
                    <?php if ($i >= 8): ?>
                    <span class="tag-more" style="display:none;">
                    <?php endif; ?>
                    <a href="?q=<?php echo urlencode($query); ?><?php echo $selectedLang ? '&lang=' . urlencode($selectedLang) : ''; ?>&tags=<?php echo urlencode($tag); ?>" 
                       class="tag-link <?php echo in_array($tag, $selectedTags) ? 'active' : ''; ?>">
                        <?php echo htmlspecialchars($tag); ?>
                    </a>
                    <?php if ($i >= 7): ?>
                    </span>
                    <?php endif; ?>
                <?php endforeach; ?>
                <?php if (count($availableTags) > 8): ?>
                <a href="javascript:void(0)" onclick="document.querySelectorAll('.tag-more').forEach(el=>el.style.display='inline');this.style.display='none'" style="font-size:12px;color:#1a73e8;">更多</a>
                <?php endif; ?>
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
            
            <?php 
            // 统计搜索结果中的域名
            $domainCounts = [];
            foreach ($results as $r) {
                $d = $r['domain'] ?? '';
                if ($d) {
                    $domainCounts[$d] = ($domainCounts[$d] ?? 0) + 1;
                }
            }
            if (count($domainCounts) > 1):
            ?>
            <div class="domain-filter">
                <span style="color:#666;">来源：</span>
                <?php 
                $i = 0;
                $totalDomains = count($domainCounts);
                foreach (array_keys($domainCounts) as $domain): 
                    $i++;
                    $show = $i <= 5;
                    $style = $show ? '' : 'display:none;';
                    $langParam = $selectedLang ? '&lang=' . urlencode($selectedLang) : '';
                ?>
                    <a href="?q=<?php echo urlencode($query); ?><?php if($selectedTags): foreach($selectedTags as $t): ?>&tags=<?php echo urlencode($t); endforeach; endif; ?><?php echo $langParam; ?>&site=<?php echo urlencode($domain); ?>" 
                       class="domain-link" style="<?php echo $style; ?>"
                       title="只看 <?php echo htmlspecialchars($domain); ?>">
                        <?php echo htmlspecialchars($domain); ?> (<?php echo $domainCounts[$domain]; ?>)
                    </a>
                <?php endforeach; ?>
                <?php if ($totalDomains > 5): ?>
                    <a href="javascript:void(0)" onclick="var links=document.querySelectorAll('.domain-link-hidden');links.forEach(l=>l.style.display='inline');this.style.display='none';" class="domain-link-more">更多 (<?php echo $totalDomains - 5; ?>)</a>
                <?php endif; ?>
            </div>
            <?php endif; ?>
            
            <?php if (empty($results)): ?>
                <div class="no-results">
                    <p>没有找到相关结果，请尝试其他关键词</p>
                </div>
            <?php else: ?>
                <div class="results-list">
                    <?php foreach ($results as $result): ?>
                        <div class="result-item">
                            <div class="result-title">
                                <?php 
                                $linkUrl = $result['url'];
                                if (!preg_match('/^https?:\/\/[^\/]+(\/.*)?$/i', $linkUrl)) {
                                    $linkUrl = 'https://' . ($result['domain'] ?? '');
                                }
                                ?>
                                <a href="<?php echo htmlspecialchars($linkUrl); ?>" target="_blank">
                                    <?php echo !empty($result['_formatted']['title']) ? $result['_formatted']['title'] : htmlspecialchars($result['title']); ?>
                                </a>
                            </div>
                            <div class="result-url">
                                <?php 
                                // 显示域名（加粗）+ 完整链接（截断）
                                $url = $result['url'];
                                $domain = $result['domain'];
                                
                                // 检查 URL 是否有效（必须有有效的 scheme://domain/）
                                $urlValid = !empty($url) && preg_match('/^https?:\/\/[^\/]+(\/.*)?$/i', $url);
                                
                                if (!$urlValid) {
                                    // URL 无效，使用 domain 作为后备
                                    $url = 'https://' . $domain . '/';
                                }
                                
                                $displayUrl = strlen($url) > 80 ? substr($url, 0, 80) . '...' : $url;
                                // 移除域名部分，只保留路径
                                $urlPath = preg_replace('/^https?:\/\/' . preg_quote($domain, '/') . '/i', '', $displayUrl);
                                if ($urlPath === $displayUrl || $urlPath === '') {
                                    $urlPath = '/';
                                }
                                ?>
                                <strong><?php echo htmlspecialchars($domain); ?></strong>
                                <span style="color:#545454;"> - <?php echo htmlspecialchars($urlPath); ?></span>
                            </div>
                            <?php if (!empty($result['tags'])): ?>
                            <div class="result-tags">
                                <?php foreach ($result['tags'] as $tag): ?>
                                    <span class="tag-badge"><?php echo htmlspecialchars($tag); ?></span>
                                <?php endforeach; ?>
                            </div>
                            <?php endif; ?>
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
                    if ($selectedLang) {
                        $baseParams .= '&lang=' . urlencode($selectedLang);
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
            <p>
                <a href="/docs/terms.html">服务条款</a> | 
                <a href="/docs/privacy.html">隐私政策</a> | 
                <a href="/docs/disclaimer.html">免责声明</a> | 
                <a href="https://github.com/epheiamoe/2345.desuwa.org" target="_blank">开源</a> | 
                © 2026 2345.desuwa.org | 
                数据来源：<a href="https://2345.lgbt" target="_blank">2345.lgbt</a>
            </p>
        </div>
    </div>
    <script src="search.js?v=4"></script>
</body>
</html>
