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
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('button[type="submit"]');
            if (btn) {
                const query = this.querySelector('[name="query"]');
                if (query && query.value.trim()) {
                    document.getElementById('loading-overlay').classList.add('active');
                }
            }
        });
    });
});
