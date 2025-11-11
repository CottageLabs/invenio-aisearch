/*
 * Copyright (C) 2025 Cottage Labs.
 *
 * invenio-aisearch is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

(function() {
  'use strict';

  console.log('Passage Search: JavaScript loading...');

  document.addEventListener('DOMContentLoaded', function() {
    console.log('Passage Search: DOM loaded, attaching event listeners...');

    const form = document.getElementById('passage-search-form');
    const resultsContainer = document.getElementById('passage-results-container');
    const resultsDiv = document.getElementById('passage-results');
    const loadingIndicator = document.getElementById('passage-loading');
    const errorMessage = document.getElementById('passage-error');
    const noResults = document.getElementById('passage-no-results');
    const resultsCount = document.getElementById('passage-results-count');
    const queryInfo = document.getElementById('passage-query-info');

    if (!form) {
      console.error('Passage Search: Form not found!');
      return;
    }

    console.log('Passage Search: Form found, attaching submit listener...');

    // Close error message on click
    const closeButton = document.querySelector('#passage-error .close');
    if (closeButton) {
      closeButton.addEventListener('click', function() {
        errorMessage.style.display = 'none';
      });
    }

    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      console.log('Passage Search: Form submitted');

      const query = document.getElementById('passage-query').value.trim();
      const limit = document.getElementById('passage-limit').value;

      console.log('Passage Search: Query:', query, 'Limit:', limit);

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
          limit: limit
        });

        const apiUrl = `/api/aisearch/passages?${params}`;
        console.log('Passage Search: Fetching:', apiUrl);

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
        console.log('Passage Search: Results:', data);

        if (data.passages && data.passages.length > 0) {
          displayResults(data);
          resultsContainer.style.display = 'block';
        } else {
          noResults.style.display = 'block';
        }

      } catch (error) {
        console.error('Passage Search: Error:', error);
        loadingIndicator.style.display = 'none';
        document.getElementById('passage-error-text').textContent = error.message;
        errorMessage.style.display = 'block';
      }
    });

    function displayResults(data) {
      // Update meta info
      resultsCount.textContent = `${data.total} passage${data.total !== 1 ? 's' : ''} found`;
      queryInfo.textContent = `Query: "${data.query}"`;

      // Clear previous results
      resultsDiv.innerHTML = '';

      // Render each passage
      data.passages.forEach((passage, index) => {
        const item = document.createElement('div');
        item.className = 'item';

        let html = '<div class="content">';

        // Header with book title and link
        html += `
          <div class="header">
            <a href="/records/${passage.record_id}">${escapeHtml(passage.title)}</a>
          </div>
        `;

        // Author
        if (passage.creators) {
          html += `<div class="meta">${escapeHtml(passage.creators)}</div>`;
        }

        // Chunk position info
        const chunkPosition = `Chunk ${passage.chunk_index + 1} of ${passage.chunk_count}`;
        const wordCount = `${passage.word_count} words`;
        html += `
          <div class="meta" style="margin-top: 0.5em;">
            <span class="ui tiny label">
              <i class="file alternate outline icon"></i>
              ${chunkPosition}
            </span>
            <span class="ui tiny label">
              <i class="font icon"></i>
              ${wordCount}
            </span>
            <span class="ui tiny primary label">
              <i class="chart line icon"></i>
              Similarity: ${passage.similarity_score.toFixed(3)}
            </span>
          </div>
        `;

        // Passage text
        html += `
          <div class="description" style="display: block !important; margin-top: 1em; padding: 1em; background-color: #f9fafb; border-left: 3px solid #2185d0; font-family: Georgia, serif; line-height: 1.8; text-align: justify;">
            ${escapeHtml(truncateText(passage.text, 600))}
          </div>
        `;

        // Action buttons at bottom
        html += `
          <div class="extra" style="margin-top: 0.5em;">
            <a href="/records/${passage.record_id}" class="ui small button">
              <i class="book icon"></i>
              View Full Record
            </a>
          </div>
        `;

        html += '</div>';

        item.innerHTML = html;
        resultsDiv.appendChild(item);
      });
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    function truncateText(text, maxLength) {
      if (text.length <= maxLength) {
        return text;
      }
      // Try to truncate at a sentence boundary
      const truncated = text.substring(0, maxLength);
      const lastPeriod = truncated.lastIndexOf('.');
      const lastQuestion = truncated.lastIndexOf('?');
      const lastExclamation = truncated.lastIndexOf('!');
      const lastSentence = Math.max(lastPeriod, lastQuestion, lastExclamation);

      if (lastSentence > maxLength * 0.7) {
        return truncated.substring(0, lastSentence + 1) + '...';
      }

      // Otherwise truncate at last space
      const lastSpace = truncated.lastIndexOf(' ');
      return truncated.substring(0, lastSpace) + '...';
    }
  });
})();
