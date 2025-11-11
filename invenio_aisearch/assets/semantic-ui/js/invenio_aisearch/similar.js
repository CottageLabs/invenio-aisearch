/*
 * Copyright (C) 2025 Cottage Labs.
 *
 * invenio-aisearch is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

(function() {
  'use strict';

  console.log('AI Similar: JavaScript loading...');

  document.addEventListener('DOMContentLoaded', function() {
    console.log('AI Similar: DOM loaded, fetching similar records...');

    const resultsContainer = document.getElementById('similar-results-container');
    const resultsDiv = document.getElementById('similar-results');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const noResults = document.getElementById('no-results');
    const resultsCount = document.getElementById('results-count');
    const sourceRecordInfo = document.getElementById('source-record-info');
    const sourceTitle = document.getElementById('source-title');
    const sourceCreators = document.getElementById('source-creators');
    const sourceRecordId = document.getElementById('source-record-id');

    // Get record ID from the page
    const recordId = sourceRecordId.textContent.trim();

    if (!recordId) {
      console.error('AI Similar: No record ID found');
      loadingIndicator.style.display = 'none';
      document.getElementById('error-text').textContent = 'No record ID specified';
      errorMessage.style.display = 'block';
      return;
    }

    console.log('AI Similar: Fetching similar records for:', recordId);

    // Close error message on click
    const closeButton = document.querySelector('#error-message .close');
    if (closeButton) {
      closeButton.addEventListener('click', function() {
        errorMessage.style.display = 'none';
      });
    }

    // Fetch similar records
    fetchSimilarRecords(recordId);

    async function fetchSimilarRecords(recordId) {
      try {
        const apiUrl = `/api/aisearch/similar/${recordId}?limit=10`;
        console.log('AI Similar: Fetching:', apiUrl);

        const response = await fetch(apiUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });

        loadingIndicator.style.display = 'none';

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Failed to fetch similar records');
        }

        const data = await response.json();
        console.log('AI Similar: Results:', data);

        // Show source record info if available
        if (data.source_title) {
          sourceTitle.textContent = data.source_title;
          if (data.source_creators && data.source_creators.length > 0) {
            sourceCreators.textContent = data.source_creators.join('; ');
          }
          sourceRecordInfo.style.display = 'block';
        }

        if (data.similar && data.similar.length > 0) {
          displayResults(data);
          resultsContainer.style.display = 'block';
        } else {
          noResults.style.display = 'block';
        }

      } catch (error) {
        console.error('AI Similar: Error:', error);
        loadingIndicator.style.display = 'none';
        document.getElementById('error-text').textContent = error.message;
        errorMessage.style.display = 'block';
      }
    }

    function displayResults(data) {
      // Update meta info
      resultsCount.textContent = `${data.total} similar record${data.total !== 1 ? 's' : ''}`;

      // Clear previous results
      resultsDiv.innerHTML = '';

      // Render each result
      data.similar.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = 'item';

        let html = '<div class="content">';

        // Labels at top (publication date, resource type, license/access)
        html += '<div class="extra" style="margin-bottom: 0.5em;">';

        // Publication date
        if (result.publication_date) {
          html += `<span class="ui tiny label">${escapeHtml(result.publication_date)}</span> `;
        }

        // Resource type
        if (result.resource_type) {
          html += `<span class="ui tiny label">${escapeHtml(result.resource_type)}</span> `;
        }

        // License / Access
        if (result.license) {
          html += `<span class="ui tiny green label">${escapeHtml(result.license)}</span> `;
        } else if (result.access_status === 'public') {
          html += '<span class="ui tiny green label">Open</span> ';
        } else if (result.access_status === 'restricted') {
          html += '<span class="ui tiny orange label">Restricted</span> ';
        }

        html += '</div>';

        // Title
        html += `
          <div class="header">
            <a href="/records/${result.record_id}">${escapeHtml(result.title)}</a>
          </div>
        `;

        // Authors
        if (result.creators && result.creators.length > 0) {
          const authors = result.creators.slice(0, 3).map(escapeHtml).join('; ');
          const moreAuthors = result.creators.length > 3 ? ` (+${result.creators.length - 3} more)` : '';
          html += `<div class="meta">${authors}${moreAuthors}</div>`;
        }

        // Summary/Description
        if (result.summary) {
          html += `
            <div class="description" style="margin-top: 0.5em;">
              ${escapeHtml(result.summary)}
            </div>
          `;
        }

        // Similarity score at bottom
        html += `
          <div class="extra" style="margin-top: 0.5em;">
            <span class="ui small primary label">
              <i class="chart line icon"></i>
              Similarity: ${result.similarity_score.toFixed(3)}
            </span>
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
  });
})();
