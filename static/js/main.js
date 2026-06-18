let socket = null;

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
    document.querySelectorAll('form:not(#search-form)').forEach(form => {
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

function wsSearch(e) {
    e.preventDefault();
    const query = document.getElementById('search-query').value.trim();
    if (!query) return false;

    const progressLog = document.getElementById('progress-log');
    const progressMessages = document.getElementById('progress-messages');
    const resultArea = document.getElementById('result-area');

    progressLog.style.display = 'block';
    progressMessages.innerHTML = '';
    resultArea.innerHTML = '';
    document.getElementById('search-btn').disabled = true;

    if (socket) socket.disconnect();

    socket = io();
    socket.on('connect', function() {
        socket.emit('search_request', { query: query });
    });
    socket.on('search_progress', function(data) {
        const div = document.createElement('div');
        div.textContent = '> ' + data.message;
        progressMessages.appendChild(div);
        progressMessages.scrollTop = progressMessages.scrollHeight;
    });
    socket.on('search_result', function(data) {
        resultArea.innerHTML = data.html;
        document.getElementById('search-btn').disabled = false;
        progressLog.style.display = 'none';
        socket.disconnect();
    });
    socket.on('search_error', function(data) {
        resultArea.innerHTML = '<div class="alert alert-danger">' + data.error + '</div>';
        document.getElementById('search-btn').disabled = false;
        progressLog.style.display = 'none';
        socket.disconnect();
    });

    return false;
}
