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
      const includePassages = document.getElementById('include-passages').checked;
      const limit = document.getElementById('results-limit').value;

      console.log('AI Search: Query:', query, 'Summaries:', includeSummaries, 'Passages:', includePassages, 'Limit:', limit);

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
          summaries: includeSummaries,
          passages: includePassages
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
      let countText = `${data.total} book result${data.total !== 1 ? 's' : ''}`;
      if (data.passages && data.passage_total > 0) {
        countText += `, ${data.passage_total} passage${data.passage_total !== 1 ? 's' : ''}`;
      }
      resultsCount.textContent = countText;

      let queryInfoText = `Query: "${data.query}"`;
      if (data.parsed && data.parsed.intent) {
        queryInfoText += ` (Intent: ${data.parsed.intent})`;
      }
      queryInfo.textContent = queryInfoText;

      // Clear previous results
      resultsDiv.innerHTML = '';

      // Group passages by record_id
      const passagesByRecord = {};
      if (data.passages && data.passages.length > 0) {
        data.passages.forEach(passage => {
          if (!passagesByRecord[passage.record_id]) {
            passagesByRecord[passage.record_id] = [];
          }
          passagesByRecord[passage.record_id].push(passage);
        });
      }

      // Track which books we've displayed
      const displayedRecords = new Set();

      // Render book results with their passages
      if (data.results && data.results.length > 0) {
        const bookHeader = document.createElement('h3');
        bookHeader.className = 'ui dividing header';
        bookHeader.innerHTML = '<i class="book icon"></i> Results';
        resultsDiv.appendChild(bookHeader);

        data.results.forEach((result, index) => {
          displayedRecords.add(result.record_id);

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

          // Score label with boosting information
          html += `
            <div class="extra" style="margin-top: 0.5em;">`;

          // Show boost details if available
          if (result.passage_boost !== undefined && result.passage_boost !== null) {
            html += `
              <span class="ui small blue label" title="Original book-level similarity score">
                <i class="book icon"></i>
                Book score: ${result.original_book_score.toFixed(3)}
              </span>
              <span class="ui small teal label" title="Boost from matching passages">
                <i class="arrow up icon"></i>
                Passage boost: ${result.passage_boost.toFixed(3)}
              </span>
              <span class="ui small green label" title="Final combined score">
                <i class="chart line icon"></i>
                Final: ${result.similarity_score.toFixed(3)}
              </span>`;
          } else {
            // No boosting - just show single score
            html += `
              <span class="ui small primary label">
                <i class="chart line icon"></i>
                Similarity: ${result.similarity_score.toFixed(3)}
              </span>`;
          }

          html += `
            </div>
          `;

          // Add matching passages for this book (if any)
          if (passagesByRecord[result.record_id]) {
            const passages = passagesByRecord[result.record_id];

            html += `
              <div style="margin-top: 1em; padding-top: 1em; border-top: 1px solid #e0e0e0;">
                <div style="margin-bottom: 0.5em;">
                  <strong><i class="file alternate outline icon"></i> Matching passage${passages.length > 1 ? 's' : ''} from this book:</strong>
                </div>
            `;

            passages.forEach((passage, pIdx) => {
              const chunkPosition = `Chunk ${passage.chunk_index + 1} of ${passage.chunk_count}`;
              const wordCount = `${passage.word_count} words`;

              html += `
                <div style="margin-top: ${pIdx > 0 ? '1em' : '0.5em'};">
                  <div style="margin-bottom: 0.5em;">
                    <span class="ui tiny label">
                      <i class="file alternate outline icon"></i>
                      ${chunkPosition}
                    </span>
                    <span class="ui tiny label">
                      <i class="font icon"></i>
                      ${wordCount}
                    </span>
                    <span class="ui tiny teal label">
                      <i class="chart line icon"></i>
                      Passage similarity: ${passage.similarity_score.toFixed(3)}
                    </span>
                  </div>
                  <div style="padding: 1em; background-color: #f9fafb; border-left: 3px solid #00b5ad; font-family: Georgia, serif; line-height: 1.8; text-align: justify;">
                    ${escapeHtml(truncateText(passage.text, 600))}
                  </div>
                </div>
              `;
            });

            html += '</div>';
          }

          html += '</div>';

          item.innerHTML = html;
          resultsDiv.appendChild(item);
        });
      }

      // Render passages from books that didn't appear in top results
      const orphanPassages = [];
      for (const recordId in passagesByRecord) {
        if (!displayedRecords.has(recordId)) {
          orphanPassages.push(...passagesByRecord[recordId]);
        }
      }

      if (orphanPassages.length > 0) {
        const orphanHeader = document.createElement('h3');
        orphanHeader.className = 'ui dividing header';
        orphanHeader.style.marginTop = '2em';
        orphanHeader.innerHTML = '<i class="file alternate outline icon"></i> Other Relevant Passages';
        resultsDiv.appendChild(orphanHeader);

        orphanPassages.forEach((passage, index) => {
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
              <span class="ui tiny teal label">
                <i class="chart line icon"></i>
                Similarity: ${passage.similarity_score.toFixed(3)}
              </span>
            </div>
          `;

          // Passage text
          html += `
            <div class="description" style="display: block !important; margin-top: 1em; padding: 1em; background-color: #f9fafb; border-left: 3px solid #00b5ad; font-family: Georgia, serif; line-height: 1.8; text-align: justify;">
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
    }

    function truncateText(text, maxLength) {
      // Don't truncate if text is short (under 400 words ≈ 2000 chars)
      // This ensures small chunks are shown in full
      if (text.length <= 2000) {
        return text;
      }

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

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  });
})();
