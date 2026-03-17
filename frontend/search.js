// 检测用户浏览器语言并自动选择
function detectUserLanguage() {
    // 已经有搜索词或已有语言参数时不处理
    var urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('q') || urlParams.get('lang')) return;
    
    var userLang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    var lang = 'zh';
    
    if (userLang.startsWith('en')) lang = 'en';
    else if (userLang.startsWith('ja')) lang = 'ja';
    else if (userLang.startsWith('es')) lang = 'es';
    else if (userLang.startsWith('nl')) lang = 'nl';
    else lang = 'zh';
    
    window.location.href = '?lang=' + lang;
}

document.addEventListener('DOMContentLoaded', function() {
    // 首页没有搜索词时检测设备语言
    detectUserLanguage();
});
