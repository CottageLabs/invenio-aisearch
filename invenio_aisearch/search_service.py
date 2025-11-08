# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Search service combining NL parsing, semantic search, and AI summaries."""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

from .models import get_model_manager
from .query_parser import QueryParser


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


class SearchService:
    """AI-powered search service for InvenioRDM records."""

    def __init__(self, embeddings_file: Optional[str] = None):
        """Initialize search service.

        Args:
            embeddings_file: Path to embeddings JSON file
        """
        self.query_parser = QueryParser()
        self.model_manager = get_model_manager()
        self.embeddings = {}
        self.embeddings_file = embeddings_file

        if embeddings_file:
            self.load_embeddings(embeddings_file)

    def load_embeddings(self, embeddings_file: str):
        """Load embeddings from file.

        Args:
            embeddings_file: Path to embeddings JSON file
        """
        with open(embeddings_file, 'r') as f:
            self.embeddings = json.load(f)

    def search(
        self,
        query: str,
        limit: Optional[int] = None,
        include_summaries: bool = False,
        semantic_weight: float = 0.7,
        metadata_weight: float = 0.3,
    ) -> Dict:
        """Perform AI-powered search.

        Args:
            query: Natural language query
            limit: Maximum number of results (overrides query parsing)
            include_summaries: Whether to generate AI summaries
            semantic_weight: Weight for semantic similarity (0-1)
            metadata_weight: Weight for metadata matching (0-1)

        Returns:
            Dictionary with search results and metadata:
            {
                "query": str,
                "parsed": {...},  # Parsed query components
                "results": [...],  # Search results
                "total": int,  # Total matches
            }
        """
        if not self.embeddings:
            raise ValueError("No embeddings loaded. Call load_embeddings() first.")

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
        result_limit = limit or parsed['limit'] or 10
        results = results[:result_limit]

        # Generate summaries if requested
        if include_summaries:
            for result in results:
                try:
                    # In production, use full record text
                    summary_text = f"A classic work titled '{result['title']}'"
                    summary = self.model_manager.generate_summary(
                        summary_text,
                        max_length=50,
                        min_length=10
                    )
                    result['summary'] = summary
                except Exception as e:
                    result['summary'] = None

        return {
            'query': query,
            'parsed': parsed,
            'results': results,
            'total': len(results),
        }

    def search_by_record_id(self, record_id: str, limit: int = 10) -> List[Dict]:
        """Find similar records to a given record.

        Args:
            record_id: ID of the record to find similar items for
            limit: Maximum number of results

        Returns:
            List of similar records with similarity scores
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

        return results[:limit]


# Global service instance
_search_service = None


def get_search_service(embeddings_file: Optional[str] = None) -> SearchService:
    """Get the global search service instance.

    Args:
        embeddings_file: Optional path to embeddings file

    Returns:
        SearchService instance
    """
    global _search_service
    if _search_service is None:
        _search_service = SearchService(embeddings_file=embeddings_file)
    elif embeddings_file and not _search_service.embeddings:
        _search_service.load_embeddings(embeddings_file)
    return _search_service
