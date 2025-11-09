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
    ):
        """Initialize search result.

        Args:
            query: Original query string
            parsed: Parsed query components
            results: List of search results
            total: Total number of results
        """
        self._query = query
        self._parsed = parsed
        self._results = results
        self._total = total

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

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with search results and metadata
        """
        return {
            "query": self._query,
            "parsed": self._parsed,
            "results": self._results,
            "total": self._total,
        }


class SimilarResult:
    """Result object for similar records query."""

    def __init__(
        self,
        record_id: str,
        similar: List[Dict],
        total: int,
    ):
        """Initialize similar result.

        Args:
            record_id: Source record ID
            similar: List of similar records
            total: Total number of similar records
        """
        self._record_id = record_id
        self._similar = similar
        self._total = total

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

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with similar records and metadata
        """
        return {
            "record_id": self._record_id,
            "similar": self._similar,
            "total": self._total,
        }


class StatusResult:
    """Result object for service status check."""

    def __init__(
        self,
        status: str,
        embeddings_loaded: bool,
        embeddings_count: int,
        embeddings_file: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Initialize status result.

        Args:
            status: Status string (ready, not_configured, no_embeddings, error)
            embeddings_loaded: Whether embeddings are loaded
            embeddings_count: Number of embeddings loaded
            embeddings_file: Path to embeddings file
            message: Optional status message
        """
        self._status = status
        self._embeddings_loaded = embeddings_loaded
        self._embeddings_count = embeddings_count
        self._embeddings_file = embeddings_file
        self._message = message

    @property
    def status(self) -> str:
        """Get status."""
        return self._status

    @property
    def embeddings_loaded(self) -> bool:
        """Check if embeddings are loaded."""
        return self._embeddings_loaded

    @property
    def embeddings_count(self) -> int:
        """Get embeddings count."""
        return self._embeddings_count

    @property
    def embeddings_file(self) -> Optional[str]:
        """Get embeddings file path."""
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
            "embeddings_loaded": self._embeddings_loaded,
            "embeddings_count": self._embeddings_count,
        }
        if self._embeddings_file:
            result["embeddings_file"] = self._embeddings_file
        if self._message:
            result["message"] = self._message
        return result
