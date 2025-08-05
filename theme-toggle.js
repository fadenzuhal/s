
document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('theme-toggle');
    const body = document.body;

    // Varsayılan tema kontrolü
    if (localStorage.getItem('theme') === 'dark') {
        body.classList.add('dark-theme');
        toggleButton.textContent = '☀️ Açık Tema';
    } else {
        toggleButton.textContent = '🌙 Karanlık Tema';
    }

    // Tema değiştirme işlemi
    toggleButton.addEventListener('click', () => {
        body.classList.toggle('dark-theme');
        if (body.classList.contains('dark-theme')) {
            localStorage.setItem('theme', 'dark');
            toggleButton.textContent = '☀️ Açık Tema';
        } else {
            localStorage.setItem('theme', 'light');
            toggleButton.textContent = '🌙 Karanlık Tema';
        }
    });
});
