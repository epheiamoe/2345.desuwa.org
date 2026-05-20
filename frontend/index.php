<?php

declare(strict_types=1);

/**
 * 跨性别资源搜索引擎 - 入口文件
 *
 * 职责：
 * 1. 加载所有依赖模块
 * 2. 解析并净化请求参数
 * 3. 调用搜索逻辑获取数据
 * 4. 调用模板渲染输出页面
 *
 * @package TransSearch
 * @license MIT
 */

// 引入依赖（顺序敏感：language_rules 需在 search 之前加载）
include_once __DIR__ . '/language_rules.php';
include_once __DIR__ . '/config.php';
include_once __DIR__ . '/functions.php';
include_once __DIR__ . '/search.php';
include_once __DIR__ . '/template.php';

// 初始化配置
AppConfig::init();

// Meilisearch 连接配置
$meilisearch_host = AppConfig::env('MEILISEARCH_HOST', 'localhost');
$meilisearch_port = AppConfig::env('MEILISEARCH_PORT', '7700');
$meilisearch_index = AppConfig::get('search.index_name', 'trans_resources');
$meilisearch_api_key = AppConfig::env('MEILISEARCH_API_KEY', '');

// ---- 请求参数处理 ----

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$page  = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;

// 标签筛选（兼容数组和逗号分隔字符串）
$selected_tags = [];
if (isset($_GET['tags'])) {
    $tags_param = $_GET['tags'];
    if (is_array($tags_param)) {
        $selected_tags = $tags_param;
    } elseif (is_string($tags_param) && $tags_param) {
        $selected_tags = array_filter(array_map('trim', explode(',', $tags_param)));
    }
}

// 站点筛选
$selected_site = isset($_GET['site']) ? trim($_GET['site']) : '';

// 解析 site:example.com 语法
if ($query && !$selected_site) {
    if (preg_match('/site:(\S+)/i', $query, $matches)) {
        $selected_site = trim($matches[1]);
        $query = trim(preg_replace('/site:\S+/i', '', $query));
        $query = preg_replace('/\s+/', ' ', $query);
    }
}

// 语言筛选
$selected_lang = isset($_GET['lang']) ? trim($_GET['lang']) : '';

// ---- 配置数据 ----

$available_tags = AppConfig::getTags();

$language_names = [
    'zh-cn'   => '简体中文',
    'zh-hant' => '繁體中文',
    'zh'      => '中文',
    'en'      => 'English',
    'ja'      => '日本語',
    'es'      => 'Español',
    'nl'      => 'Nederlands',
    'ko'      => '한국어',
    'fr'      => 'Français',
    'de'      => 'Deutsch',
    'pl'      => 'Polski',
    'el'      => 'Ελληνικά',
    'hu'      => 'Magyar',
    'ru'      => 'Русский',
];

$available_languages = [];
foreach (AppConfig::getLanguages() as $lang_code) {
    if (isset($language_names[$lang_code])) {
        $available_languages[$lang_code] = $language_names[$lang_code];
    }
}

$limit = 10;

// ---- 执行业务逻辑 ----

$stats = get_index_stats($meilisearch_host, $meilisearch_port, $meilisearch_index, $meilisearch_api_key);
$total_docs = $stats['numberOfDocuments'] ?? 0;

$results     = [];
$total_hits  = 0;
$search_time = 0;
$error       = '';

if ($query) {
    [$results, $total_hits, $search_time, $error] = search_meilisearch(
        $query,
        $page,
        $limit,
        $selected_tags,
        $selected_site,
        $selected_lang,
        $available_tags,
        $meilisearch_host,
        $meilisearch_port,
        $meilisearch_index,
        $meilisearch_api_key
    );
}

// ---- 构建页面数据并渲染 ----

$page_data = [
    'query'               => $query,
    'page'                => $page,
    'limit'               => $limit,
    'selected_tags'       => $selected_tags,
    'selected_site'       => $selected_site,
    'selected_lang'       => $selected_lang,
    'total_docs'          => $total_docs,
    'total_hits'          => $total_hits,
    'search_time'         => $search_time,
    'results'             => $results,
    'error'               => $error,
    'available_tags'      => $available_tags,
    'available_languages' => $available_languages,
];

render_header($page_data);
render_search_form($page_data);
render_results($page_data);
render_footer($page_data);
