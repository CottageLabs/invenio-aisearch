# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""AI search service implementation."""

import json
import numpy as np
from pathlib import Path
from typing import Optional

from flask import current_app
from invenio_rdm_records.proxies import current_rdm_records_service

from ...models import get_model_manager
from ...query_parser import QueryParser
from ..results import SearchResult, SimilarResult, StatusResult


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector (list or numpy array)
        vec2: Second vector (list or numpy array)

    Returns:
        Similarity score between -1 and 1
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


class AISearchService:
    """AI-powered search service for InvenioRDM records."""

    def __init__(self, config=None):
        """Initialize AI search service.

        Args:
            config: Service configuration object
        """
        self.config = config or {}
        self.query_parser = QueryParser()
        self.model_manager = get_model_manager()
        self.embeddings = {}
        self.embeddings_file = None

    def load_embeddings(self, embeddings_file: str):
        """Load embeddings from file.

        Args:
            embeddings_file: Path to embeddings JSON file
        """
        with open(embeddings_file, 'r') as f:
            self.embeddings = json.load(f)
        self.embeddings_file = embeddings_file
        current_app.logger.info(
            f"Loaded {len(self.embeddings)} embeddings from {embeddings_file}"
        )

    def _fetch_record_metadata(self, identity, record_id: str) -> Optional[dict]:
        """Fetch full record metadata from InvenioRDM.

        Args:
            identity: User identity for permission checking
            record_id: InvenioRDM record ID

        Returns:
            Record metadata dict or None if fetch fails
        """
        try:
            # Use InvenioRDM's records service to read the record
            record = current_rdm_records_service.read(identity, record_id)
            return record.data.get('metadata', {})

        except Exception as e:
            current_app.logger.warning(
                f"Error fetching metadata for {record_id}: {e}"
            )
            return None

    def search(
        self,
        identity,
        query: str,
        limit: Optional[int] = None,
        include_summaries: bool = False,
        semantic_weight: Optional[float] = None,
        metadata_weight: Optional[float] = None,
    ) -> SearchResult:
        """Perform AI-powered search.

        Args:
            identity: User identity (for permissions, not used yet)
            query: Natural language query
            limit: Maximum number of results
            include_summaries: Whether to generate AI summaries
            semantic_weight: Weight for semantic similarity (0-1)
            metadata_weight: Weight for metadata matching (0-1)

        Returns:
            SearchResult object with results and metadata

        Raises:
            ValueError: If no embeddings are loaded
        """
        if not self.embeddings:
            raise ValueError("No embeddings loaded. Call load_embeddings() first.")

        # Use config defaults if not specified
        semantic_weight = semantic_weight or getattr(
            self.config, 'default_semantic_weight', 0.7
        )
        metadata_weight = metadata_weight or getattr(
            self.config, 'default_metadata_weight', 0.3
        )

        # Step 1: Parse query
        parsed = self.query_parser.parse(query)

        # Step 2: Generate query embedding
        query_embedding = self.model_manager.generate_embedding(
            parsed['semantic_query']
        )

        # Step 3: Calculate similarity scores
        results = []

        for record_id, data in self.embeddings.items():
            # Semantic similarity
            semantic_score = cosine_similarity(query_embedding, data['embedding'])

            # Metadata matching
            metadata_score = 0.0
            if parsed['search_terms']:
                title_lower = data['title'].lower()
                matches = sum(1 for term in parsed['search_terms']
                            if term.lower() in title_lower)
                metadata_score = matches / len(parsed['search_terms'])

            # Hybrid score
            hybrid_score = (semantic_weight * semantic_score +
                          metadata_weight * metadata_score)

            results.append({
                'record_id': record_id,
                'title': data['title'],
                'semantic_score': semantic_score,
                'metadata_score': metadata_score,
                'hybrid_score': hybrid_score,
            })

        # Sort by hybrid score
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)

        # Apply limit
        result_limit = limit or parsed['limit'] or getattr(
            self.config, 'default_limit', 10
        )
        results = results[:result_limit]

        # Generate summaries if requested
        if include_summaries and getattr(self.config, 'enable_summaries', True):
            for result in results:
                try:
                    # Fetch full record metadata
                    metadata = self._fetch_record_metadata(identity, result['record_id'])

                    if metadata and metadata.get('description'):
                        # Use existing description if available
                        description = metadata['description']

                        # Optionally summarize long descriptions
                        if len(description) > 500:
                            summary = self.model_manager.generate_summary(
                                description,
                                max_length=getattr(self.config, 'summary_max_length', 150),
                                min_length=getattr(self.config, 'summary_min_length', 50)
                            )
                            result['summary'] = summary
                        else:
                            # Use description as-is if it's already concise
                            result['summary'] = description
                    else:
                        # Fallback: use title and subjects if no description
                        subjects = metadata.get('subjects', []) if metadata else []
                        subject_terms = ', '.join([s.get('subject', '') for s in subjects[:3]])
                        if subject_terms:
                            result['summary'] = f"{result['title']}. Subjects: {subject_terms}"
                        else:
                            result['summary'] = result['title']

                except Exception as e:
                    current_app.logger.warning(
                        f"Failed to generate summary for {result['record_id']}: {e}"
                    )
                    result['summary'] = result['title']

        return SearchResult(
            query=query,
            parsed=parsed,
            results=results,
            total=len(results),
        )

    def similar(
        self,
        identity,
        record_id: str,
        limit: int = 10
    ) -> SimilarResult:
        """Find similar records to a given record.

        Args:
            identity: User identity (for permissions, not used yet)
            record_id: ID of the record to find similar items for
            limit: Maximum number of results

        Returns:
            SimilarResult object with similar records

        Raises:
            ValueError: If embeddings not loaded or record not found
        """
        if not self.embeddings:
            raise ValueError("No embeddings loaded. Call load_embeddings() first.")

        if record_id not in self.embeddings:
            raise ValueError(f"Record {record_id} not found in embeddings")

        source_embedding = self.embeddings[record_id]['embedding']
        results = []

        for rid, data in self.embeddings.items():
            if rid == record_id:
                continue  # Skip itself

            similarity = cosine_similarity(source_embedding, data['embedding'])
            results.append({
                'record_id': rid,
                'title': data['title'],
                'similarity': similarity,
            })

        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return SimilarResult(
            record_id=record_id,
            similar=results[:limit],
            total=len(results),
        )

    def status(self, identity) -> StatusResult:
        """Get service status.

        Args:
            identity: User identity (for permissions, not used yet)

        Returns:
            StatusResult object with service status
        """
        if not self.embeddings_file:
            return StatusResult(
                status="not_configured",
                embeddings_loaded=False,
                embeddings_count=0,
                message="Embeddings file not configured"
            )

        if not self.embeddings:
            return StatusResult(
                status="no_embeddings",
                embeddings_loaded=False,
                embeddings_count=0,
                embeddings_file=self.embeddings_file,
                message="No embeddings loaded"
            )

        return StatusResult(
            status="ready",
            embeddings_loaded=True,
            embeddings_count=len(self.embeddings),
            embeddings_file=self.embeddings_file,
        )
