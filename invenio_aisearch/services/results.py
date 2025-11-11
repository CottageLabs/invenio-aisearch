# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Result classes for AI search service."""

from typing import Dict, List, Optional


class SearchResult:
    """Result object for AI search queries."""

    def __init__(
        self,
        query: str,
        parsed: Dict,
        results: List[Dict],
        total: int,
        passages: Optional[List[Dict]] = None,
        passage_total: int = 0,
    ):
        """Initialize search result.

        Args:
            query: Original query string
            parsed: Parsed query components
            results: List of search results
            total: Total number of results
            passages: Optional list of passage-level results
            passage_total: Total number of passages
        """
        self._query = query
        self._parsed = parsed
        self._results = results
        self._total = total
        self._passages = passages or []
        self._passage_total = passage_total

    @property
    def query(self) -> str:
        """Get the original query."""
        return self._query

    @property
    def parsed(self) -> Dict:
        """Get parsed query components."""
        return self._parsed

    @property
    def results(self) -> List[Dict]:
        """Get search results."""
        return self._results

    @property
    def total(self) -> int:
        """Get total number of results."""
        return self._total

    @property
    def passages(self) -> List[Dict]:
        """Get passage results."""
        return self._passages

    @property
    def passage_total(self) -> int:
        """Get total number of passages."""
        return self._passage_total

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with search results and metadata
        """
        result = {
            "query": self._query,
            "parsed": self._parsed,
            "results": self._results,
            "total": self._total,
        }

        # Include passages if available
        if self._passages:
            result["passages"] = self._passages
            result["passage_total"] = self._passage_total

        return result


class SimilarResult:
    """Result object for similar records query."""

    def __init__(
        self,
        record_id: str,
        similar: List[Dict],
        total: int,
        source_title: Optional[str] = None,
        source_creators: Optional[List[str]] = None,
    ):
        """Initialize similar result.

        Args:
            record_id: Source record ID
            similar: List of similar records
            total: Total number of similar records
            source_title: Title of the source record
            source_creators: List of creator names for the source record
        """
        self._record_id = record_id
        self._similar = similar
        self._total = total
        self._source_title = source_title
        self._source_creators = source_creators or []

    @property
    def record_id(self) -> str:
        """Get the source record ID."""
        return self._record_id

    @property
    def similar(self) -> List[Dict]:
        """Get similar records."""
        return self._similar

    @property
    def total(self) -> int:
        """Get total number of similar records."""
        return self._total

    @property
    def source_title(self) -> Optional[str]:
        """Get the source record title."""
        return self._source_title

    @property
    def source_creators(self) -> List[str]:
        """Get the source record creators."""
        return self._source_creators

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with similar records and metadata
        """
        result = {
            "record_id": self._record_id,
            "similar": self._similar,
            "total": self._total,
        }
        if self._source_title:
            result["source_title"] = self._source_title
        if self._source_creators:
            result["source_creators"] = self._source_creators
        return result


class StatusResult:
    """Result object for service status check."""

    def __init__(
        self,
        status: str,
        model_loaded: bool = False,
        opensearch_version: Optional[str] = None,
        knn_plugin_available: bool = False,
        error: Optional[str] = None,
        # Legacy parameters for backward compatibility
        embeddings_loaded: bool = None,
        embeddings_count: int = None,
        embeddings_file: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Initialize status result.

        Args:
            status: Status string (ready, error)
            model_loaded: Whether the embedding model is loaded
            opensearch_version: OpenSearch version string
            knn_plugin_available: Whether k-NN plugin is available
            error: Error message if status is error
            embeddings_loaded: (Legacy) Whether embeddings are loaded
            embeddings_count: (Legacy) Number of embeddings loaded
            embeddings_file: (Legacy) Path to embeddings file
            message: Optional status message
        """
        self._status = status
        self._model_loaded = model_loaded
        self._opensearch_version = opensearch_version
        self._knn_plugin_available = knn_plugin_available
        self._error = error
        # Legacy fields
        self._embeddings_loaded = embeddings_loaded if embeddings_loaded is not None else model_loaded
        self._embeddings_count = embeddings_count or 0
        self._embeddings_file = embeddings_file
        self._message = message or error

    @property
    def status(self) -> str:
        """Get status."""
        return self._status

    @property
    def model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model_loaded

    @property
    def opensearch_version(self) -> Optional[str]:
        """Get OpenSearch version."""
        return self._opensearch_version

    @property
    def knn_plugin_available(self) -> bool:
        """Check if k-NN plugin is available."""
        return self._knn_plugin_available

    @property
    def error(self) -> Optional[str]:
        """Get error message."""
        return self._error

    @property
    def embeddings_loaded(self) -> bool:
        """Check if embeddings are loaded (legacy)."""
        return self._embeddings_loaded

    @property
    def embeddings_count(self) -> int:
        """Get embeddings count (legacy)."""
        return self._embeddings_count

    @property
    def embeddings_file(self) -> Optional[str]:
        """Get embeddings file path (legacy)."""
        return self._embeddings_file

    @property
    def message(self) -> Optional[str]:
        """Get status message."""
        return self._message

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with status information
        """
        result = {
            "status": self._status,
            "model_loaded": self._model_loaded,
        }
        if self._opensearch_version:
            result["opensearch_version"] = self._opensearch_version
        if self._knn_plugin_available:
            result["knn_plugin_available"] = self._knn_plugin_available
        if self._error:
            result["error"] = self._error
        if self._message:
            result["message"] = self._message
        return result
