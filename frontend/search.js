// 检测用户设备语言并自动选择
function detectUserLanguage() {
    var langInput = document.getElementById('lang-input');
    if (!langInput || langInput.value !== '') return; // 已有选择则不覆盖
    
    var userLang = navigator.language || navigator.userLanguage || '';
    var langMap = {
        'zh': 'zh', 'zh-CN': 'zh', 'zh-TW': 'zh', 'zh-HK': 'zh',
        'en': 'en', 'ja': 'ja', 'es': 'es', 'nl': 'nl'
    };
    
    var shortLang = langMap[userLang] || '';
    if (shortLang && shortLang !== 'zh') {
        // 构建当前 URL 并添加语言参数
        var url = new URL(window.location.href);
        url.searchParams.set('lang', shortLang);
        window.location.href = url.toString();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // 首页没有搜索词时检测设备语言
    var queryInput = document.querySelector('input[name="q"]');
    if (queryInput && !queryInput.value) {
        detectUserLanguage();
    }
});
