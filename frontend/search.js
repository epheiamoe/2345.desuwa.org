function updateTagsInput() {
    var checkboxes = document.querySelectorAll('.tag-checkbox:checked');
    var tags = Array.from(checkboxes).map(cb => cb.value);
    document.getElementById('tags-input').value = tags.join(',');
}

function submitSearchForm() {
    var form = document.querySelector('.search-form');
    if (form) form.submit();
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.domain-link').forEach(function(link) {
        if (link.style.display === 'none') {
            link.classList.add('domain-link-hidden');
        }
    });

    document.querySelectorAll('.tag-checkbox').forEach(function(checkbox) {
        checkbox.addEventListener('change', updateTagsInput);
    });

    // 语言筛选 radio 点击时提交表单
    document.querySelectorAll('input[name="lang"]').forEach(function(radio) {
        radio.addEventListener('change', submitSearchForm);
    });
});
