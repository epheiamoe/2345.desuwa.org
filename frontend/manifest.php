<?php

declare(strict_types=1);

/**
 * 动态生成 PWA Manifest
 *
 * 读取 config.json 中的站点配置，输出符合 Web App Manifest 规范的 JSON。
 * 替代静态 manifest.json，支持自部署时通过配置一键替换品牌信息。
 *
 * @package TransSearch
 * @license MIT
 */

require_once __DIR__ . '/config.php';

AppConfig::init();

$siteName  = AppConfig::get('site.name', '2345.desuwa.org');
$siteTitle = AppConfig::get('site.title', '跨性别资源搜索');

$manifest = [
    'name'             => "$siteName - $siteTitle",
    'short_name'       => $siteName . '搜索',
    'description'      => $siteTitle . ' - 搜索跨性别相关的知识、社区、医疗资源等',
    'start_url'        => AppConfig::get('pwa.start_url', '/'),
    'display'          => AppConfig::get('pwa.display', 'standalone'),
    'background_color' => AppConfig::get('pwa.background_color', '#ffffff'),
    'theme_color'      => AppConfig::get('pwa.theme_color', '#1a73e8'),
    'orientation'      => 'portrait-primary',
    'icons'            => [
        [
            'src'     => '/icon-192.png',
            'sizes'   => '192x192',
            'type'    => 'image/png',
            'purpose' => 'any maskable',
        ],
        [
            'src'     => '/icon-512.png',
            'sizes'   => '512x512',
            'type'    => 'image/png',
            'purpose' => 'any maskable',
        ],
    ],
    'categories' => ['health', 'education', 'lifestyle'],
    'lang'       => 'zh-CN',
    'dir'        => 'ltr',
];

header('Content-Type: application/manifest+json; charset=utf-8');
echo json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
