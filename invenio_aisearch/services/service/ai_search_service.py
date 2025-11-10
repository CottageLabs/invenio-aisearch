# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""AI search service implementation using OpenSearch k-NN."""

from flask import current_app
from invenio_search import current_search_client
from invenio_rdm_records.records.api import RDMRecord

from ...models import get_model_manager
from ...query_parser import QueryParser
from ..results import SearchResult, StatusResult


class AISearchService:
    """AI-powered search service using OpenSearch k-NN."""

    def __init__(self, config=None):
        """Initialize AI search service.

        Args:
            config: Service configuration object
        """
        self.config = config or {}
        self.query_parser = QueryParser()
        self.model_manager = get_model_manager()

    def search(self, identity, query: str, limit: int = None, include_summaries: bool = True):
        """Search records using AI-powered semantic search with OpenSearch k-NN.

        Args:
            identity: User identity for access control
            query: Natural language search query
            limit: Maximum number of results (default from config)
            include_summaries: Whether to include AI-generated summaries

        Returns:
            SearchResult object with matching records
        """
        # Parse query
        parsed = self.query_parser.parse(query)

        # Generate query embedding
        query_embedding = self.model_manager.generate_embedding(query)

        # Determine limit
        result_limit = limit or parsed.get('limit') or getattr(
            self.config, 'default_limit', 10
        )
        max_limit = getattr(self.config, 'max_limit', 100)
        result_limit = min(result_limit, max_limit)

        # Get index name from RDM records with prefix
        prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
        base_index_name = RDMRecord.index._name
        index_name = f"{prefix}{base_index_name}"

        # Build OpenSearch k-NN query
        search_body = {
            "size": result_limit,
            "query": {
                "knn": {
                    "aisearch.embedding": {
                        "vector": query_embedding.tolist(),
                        "k": result_limit
                    }
                }
            },
            "_source": {
                "excludes": ["aisearch.embedding"]  # Don't return the embedding
            }
        }

        # Execute search
        try:
            response = current_search_client.search(
                index=index_name,
                body=search_body
            )
        except Exception as e:
            current_app.logger.error(f"OpenSearch k-NN query failed: {e}")
            # Return empty results on error
            return SearchResult(
                query=query,
                parsed=parsed,
                results=[],
                total=0,
            )

        # Parse results
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            metadata = source.get('metadata', {})

            # Extract creators (authors)
            creators = metadata.get('creators', [])
            creator_names = [
                creator.get('person_or_org', {}).get('name', 'Unknown')
                for creator in creators
            ]

            # Extract resource type
            resource_type = metadata.get('resource_type', {})
            resource_type_title = resource_type.get('title', {}).get('en', 'Unknown')

            # Extract rights/license
            rights = metadata.get('rights', [])
            license_title = None
            if rights:
                license_title = rights[0].get('title', {}).get('en')

            # Extract access status
            access = source.get('access', {})
            access_status = access.get('record', 'restricted')

            # Build result item
            result = {
                'record_id': hit['_id'],
                'title': metadata.get('title', 'Untitled'),
                'creators': creator_names,
                'publication_date': metadata.get('publication_date', ''),
                'resource_type': resource_type_title,
                'license': license_title,
                'access_status': access_status,
                'semantic_score': hit['_score'],  # k-NN score
                'metadata_score': 0.0,  # Not used in k-NN mode
                'hybrid_score': hit['_score'],  # Same as semantic for now
            }

            # Add summary if requested
            if include_summaries and getattr(self.config, 'enable_summaries', True):
                description = metadata.get('description')
                if description:
                    if len(description) > 500:
                        # Generate summary for long descriptions
                        summary = self.model_manager.generate_summary(
                            description,
                            max_length=getattr(self.config, 'summary_max_length', 150),
                            min_length=getattr(self.config, 'summary_min_length', 50)
                        )
                        result['summary'] = summary
                    else:
                        result['summary'] = description
                else:
                    # Fallback: use title
                    result['summary'] = result['title']

            results.append(result)

        return SearchResult(
            query=query,
            parsed=parsed,
            results=results,
            total=len(results),
        )

    def similar(self, identity, record_id: str, limit: int = 10):
        """Find similar records to a given record.

        Args:
            identity: User identity for access control
            record_id: ID of the record to find similar items for
            limit: Maximum number of similar records to return

        Returns:
            SimilarResult object with similar records
        """
        # TODO: Implement using OpenSearch More Like This or k-NN
        raise NotImplementedError("Similar records search not yet implemented with k-NN")

    def status(self):
        """Get service status.

        Returns:
            StatusResult with service health information
        """
        try:
            # Check if OpenSearch is accessible
            info = current_search_client.info()
            opensearch_version = info.get('version', {}).get('number', 'unknown')

            # Check if k-NN plugin is available
            plugins_response = current_search_client.cat.plugins(format='json')
            knn_plugin = any(p.get('component') == 'opensearch-knn' for p in plugins_response)

            return StatusResult(
                status='ready',
                model_loaded=self.model_manager is not None,
                opensearch_version=opensearch_version,
                knn_plugin_available=knn_plugin,
            )
        except Exception as e:
            current_app.logger.error(f"Status check failed: {e}")
            return StatusResult(
                status='error',
                error=str(e),
            )
