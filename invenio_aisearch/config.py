# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Configuration for AI-powered search."""

INVENIO_AISEARCH_BASE_TEMPLATE = "invenio_theme/page.html"
"""Default base template for the AI search page."""

INVENIO_AISEARCH_DEFAULT_LIMIT = 10
"""Default number of search results to return."""

INVENIO_AISEARCH_MAX_LIMIT = 100
"""Maximum number of search results allowed."""

# Full-text search configuration
INVENIO_AISEARCH_CHUNKS_INDEX = "document-chunks-v1"
"""OpenSearch index name for document chunks."""

INVENIO_AISEARCH_CHUNK_SIZE = 600
"""Target chunk size in words for full-text search."""

INVENIO_AISEARCH_CHUNK_OVERLAP = 150
"""Overlap size in words between chunks."""

INVENIO_AISEARCH_CHUNKS_ENABLED = False
"""Enable full-text search on document chunks (requires separate indexing)."""

INVENIO_AISEARCH_DATA_DIR = "aisearch_data"
"""Directory containing the document chunks JSONL file.
Relative to instance path or absolute path."""

INVENIO_AISEARCH_CHUNKS_FILE = "document_chunks.jsonl"
"""Filename for the document chunks JSONL file (stored in DATA_DIR)."""
