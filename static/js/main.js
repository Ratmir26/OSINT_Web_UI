document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-copy]').forEach(el => {
        el.addEventListener('click', function() {
            const text = this.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(() => {
                const orig = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check"></i> Скопировано';
                setTimeout(() => this.innerHTML = orig, 1500);
            });
        });
    });
});
