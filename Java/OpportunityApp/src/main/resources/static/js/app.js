// The sidebar, opened from the header's menu button as in SolarERP.
const hamburgerBtn = document.getElementById('hamburgerBtn');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebar-overlay');

function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden'; // keep wheel/touch scroll inside the sidebar
}

function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
}

hamburgerBtn.addEventListener('click', openSidebar);
overlay.addEventListener('click', closeSidebar);
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeSidebar();
});
