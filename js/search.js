// QatarPaws Search Functionality
(function() {
  let fuse = null;
  let searchData = [];

  // Initialize search when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
  } else {
    initSearch();
  }

  async function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    if (!searchInput || !searchResults) {
      return; // Search not on this page
    }

    try {
      // Load search data
      const response = await fetch('/js/search-data.json');
      searchData = await response.json();

      // Determine current language
      const isArabic = document.documentElement.lang === 'ar' || document.documentElement.dir === 'rtl';

      // Filter data by language
      const filteredData = searchData.filter(b => b.lang === (isArabic ? 'ar' : 'en'));

      // Initialize Fuse.js
      fuse = new Fuse(filteredData, {
        keys: [
          { name: 'name', weight: 2 },
          { name: 'category', weight: 1 }
        ],
        threshold: 0.3,
        minMatchCharLength: 2,
        ignoreLocation: true
      });

      // Add event listeners
      searchInput.addEventListener('input', handleSearch);
      searchInput.addEventListener('focus', handleSearch);

      // Close dropdown when clicking outside
      document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
          searchResults.classList.remove('show');
        }
      });

    } catch (error) {
      console.error('Error loading search data:', error);
    }
  }

  function handleSearch(e) {
    const query = e.target.value.trim();
    const searchResults = document.getElementById('searchResults');

    if (query.length < 2) {
      searchResults.classList.remove('show');
      return;
    }

    // Perform search
    const results = fuse.search(query).slice(0, 10); // Limit to 10 results

    // Display results
    displayResults(results);
  }

  function displayResults(results) {
    const searchResults = document.getElementById('searchResults');

    if (results.length === 0) {
      searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
      searchResults.classList.add('show');
      return;
    }

    let html = '';
    results.forEach(result => {
      const business = result.item;
      const stars = '★'.repeat(Math.floor(business.rating || 0));
      const rating = business.rating ? business.rating.toFixed(1) : 'N/A';

      html += `
        <a href="${business.url}" class="search-result-item">
          <div class="search-result-name">${escapeHtml(business.name)}</div>
          <div class="search-result-meta">
            <span class="search-result-category">${escapeHtml(business.category)}</span>
            ${business.rating ? `<span class="search-result-rating">${stars} ${rating}</span>` : ''}
          </div>
        </a>
      `;
    });

    searchResults.innerHTML = html;
    searchResults.classList.add('show');
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
})();
