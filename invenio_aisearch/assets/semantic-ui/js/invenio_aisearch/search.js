/*
 * Copyright (C) 2025 Cottage Labs.
 *
 * invenio-aisearch is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

(function() {
  'use strict';

  console.log('AI Search: JavaScript loading...');

  document.addEventListener('DOMContentLoaded', function() {
    console.log('AI Search: DOM loaded, attaching event listeners...');

    const form = document.getElementById('ai-search-form');
    const resultsContainer = document.getElementById('search-results-container');
    const resultsDiv = document.getElementById('search-results');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const noResults = document.getElementById('no-results');
    const resultsCount = document.getElementById('results-count');
    const queryInfo = document.getElementById('query-info');

    if (!form) {
      console.error('AI Search: Form not found!');
      return;
    }

    console.log('AI Search: Form found, attaching submit listener...');

    // Close error message on click
    const closeButton = document.querySelector('#error-message .close');
    if (closeButton) {
      closeButton.addEventListener('click', function() {
        errorMessage.style.display = 'none';
      });
    }

    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      console.log('AI Search: Form submitted');

      const query = document.getElementById('search-query').value.trim();
      const includeSummaries = document.getElementById('include-summaries').checked;
      const limit = document.getElementById('results-limit').value;

      console.log('AI Search: Query:', query, 'Summaries:', includeSummaries, 'Limit:', limit);

      if (!query) {
        return;
      }

      // Hide previous results and errors
      resultsContainer.style.display = 'none';
      errorMessage.style.display = 'none';
      noResults.style.display = 'none';

      // Show loading
      loadingIndicator.style.display = 'block';

      try {
        // Build API URL
        const params = new URLSearchParams({
          q: query,
          limit: limit,
          summaries: includeSummaries
        });

        const apiUrl = `/api/aisearch/search?${params}`;
        console.log('AI Search: Fetching:', apiUrl);

        const response = await fetch(apiUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });

        loadingIndicator.style.display = 'none';

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Search failed');
        }

        const data = await response.json();
        console.log('AI Search: Results:', data);

        if (data.results && data.results.length > 0) {
          displayResults(data);
          resultsContainer.style.display = 'block';
        } else {
          noResults.style.display = 'block';
        }

      } catch (error) {
        console.error('AI Search: Error:', error);
        loadingIndicator.style.display = 'none';
        document.getElementById('error-text').textContent = error.message;
        errorMessage.style.display = 'block';
      }
    });

    function displayResults(data) {
      // Update meta info
      resultsCount.textContent = `${data.total} result${data.total !== 1 ? 's' : ''}`;

      let queryInfoText = `Query: "${data.query}"`;
      if (data.parsed && data.parsed.intent) {
        queryInfoText += ` (Intent: ${data.parsed.intent})`;
      }
      queryInfo.textContent = queryInfoText;

      // Clear previous results
      resultsDiv.innerHTML = '';

      // Render each result
      data.results.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = 'item';

        let html = `
          <div class="content">
            <div class="header">
              <a href="/records/${result.record_id}">${escapeHtml(result.title)}</a>
            </div>
            <div class="meta">
              <span>Record ID: ${result.record_id}</span>
            </div>
        `;

        if (result.summary) {
          html += `
            <div class="description" style="margin-top: 0.5em;">
              ${escapeHtml(result.summary)}
            </div>
          `;
        }

        html += `
            <div class="extra" style="margin-top: 0.5em;">
              <span class="ui small label">
                <i class="chart line icon"></i>
                Semantic: ${result.semantic_score.toFixed(3)}
              </span>
              <span class="ui small label">
                <i class="tags icon"></i>
                Metadata: ${result.metadata_score.toFixed(3)}
              </span>
              <span class="ui small primary label">
                <i class="star icon"></i>
                Hybrid: ${result.hybrid_score.toFixed(3)}
              </span>
            </div>
          </div>
        `;

        item.innerHTML = html;
        resultsDiv.appendChild(item);
      });
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  });
})();
