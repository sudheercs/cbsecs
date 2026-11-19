let activeTypeFilter = 'all';
let activeYearFilter = 'all';

function filterCards() {
  const cards = Array.from(document.querySelectorAll('.q-card'));
  const search = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
  let visibleCount = 0;

  cards.forEach((card) => {
    const matchesType = activeTypeFilter === 'all' || card.dataset.type === activeTypeFilter;
    const matchesYear = activeYearFilter === 'all' || card.dataset.year === activeYearFilter;
    const matchesSearch = !search || card.textContent.toLowerCase().includes(search);
    card.hidden = !(matchesType && matchesYear && matchesSearch);
    if (!card.hidden) visibleCount += 1;
  });

  document.querySelectorAll('.group-section').forEach((section) => {
    section.hidden = !Array.from(section.querySelectorAll('.q-card')).some((card) => !card.hidden);
  });

  const resultsCount = document.getElementById('resultsCount');
  if (resultsCount) {
    resultsCount.textContent = visibleCount === cards.length
      ? 'Showing all questions'
      : `Showing ${visibleCount} of ${cards.length} questions`;
  }
}

function setTypeFilter(type, button) {
  activeTypeFilter = type;
  setActiveFilterButton(button);
  filterCards();
}

function setYearFilter(year, button) {
  activeYearFilter = year;
  setActiveFilterButton(button);
  filterCards();
}

function setActiveFilterButton(button) {
  const group = button.closest('.filter-group');
  if (!group) return;

  group.querySelectorAll('.pill').forEach((pill) => {
    pill.classList.toggle('active', pill === button);
  });
}

function toggleAns(button) {
  const answer = button.closest('.q-card')?.querySelector('.ans-container');
  if (answer) answer.classList.toggle('hidden');
}

function toggleAllAnswers(show) {
  document.querySelectorAll('.q-card .ans-container').forEach((answer) => {
    answer.classList.toggle('hidden', !show);
  });
}

function applyTheme(theme) {
  document.body.setAttribute('data-theme', theme);
  const text = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
  document.querySelectorAll('#globalThemeBtn, #themeBtn').forEach((button) => {
    button.textContent = text;
  });
  localStorage.setItem('cbse_theme', theme);
}

function toggleTheme() {
  const current = document.body.getAttribute('data-theme') || 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

const savedTheme = localStorage.getItem('cbse_theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
applyTheme(savedTheme || (prefersDark ? 'dark' : 'light'));
