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
from ..results import SearchResult, SimilarResult, StatusResult


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
                'record_id': source.get('id'),  # Use PID, not internal UUID
                'title': metadata.get('title', 'Untitled'),
                'creators': creator_names,
                'publication_date': metadata.get('publication_date', ''),
                'resource_type': resource_type_title,
                'license': license_title,
                'access_status': access_status,
                'similarity_score': hit['_score'],  # k-NN cosine similarity score
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
        """Find similar records to a given record using k-NN.

        Args:
            identity: User identity for access control
            record_id: ID of the record to find similar items for
            limit: Maximum number of similar records to return

        Returns:
            SimilarResult object with similar records
        """
        # Get index name from RDM records with prefix
        prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
        base_index_name = RDMRecord.index._name
        index_name = f"{prefix}{base_index_name}"

        # Fetch the source record to get its embedding
        try:
            # Search for the record by its PID
            search_response = current_search_client.search(
                index=index_name,
                body={
                    "query": {"term": {"id": record_id}},
                    "size": 1,
                    "_source": ["aisearch.embedding", "metadata.title", "metadata.creators"]
                }
            )

            if not search_response['hits']['hits']:
                current_app.logger.error(f"Record {record_id} not found in index")
                return SimilarResult(
                    record_id=record_id,
                    similar=[],
                    total=0,
                )

            source_hit = search_response['hits']['hits'][0]
            source_data = source_hit['_source']
            source_embedding = source_data.get('aisearch', {}).get('embedding')

            if not source_embedding:
                current_app.logger.error(f"Record {record_id} has no embedding")
                return SimilarResult(
                    record_id=record_id,
                    similar=[],
                    total=0,
                )

            # Extract source record metadata
            source_metadata = source_data.get('metadata', {})
            source_title = source_metadata.get('title', 'Untitled')
            source_creators_data = source_metadata.get('creators', [])
            source_creators = [
                creator.get('person_or_org', {}).get('name', 'Unknown')
                for creator in source_creators_data
            ]

        except Exception as e:
            current_app.logger.error(f"Failed to fetch source record {record_id}: {e}")
            return SimilarResult(
                record_id=record_id,
                similar=[],
                total=0,
            )

        # Build k-NN query to find similar records
        # Request limit+1 to account for the source record in results
        search_body = {
            "size": limit + 1,
            "query": {
                "knn": {
                    "aisearch.embedding": {
                        "vector": source_embedding,
                        "k": limit + 1
                    }
                }
            },
            "_source": {
                "excludes": ["aisearch.embedding"]
            }
        }

        # Execute search
        try:
            response = current_search_client.search(
                index=index_name,
                body=search_body
            )
        except Exception as e:
            current_app.logger.error(f"k-NN similar query failed: {e}")
            return SimilarResult(
                record_id=record_id,
                similar=[],
                total=0,
            )

        # Parse results, excluding the source record
        similar_records = []
        for hit in response['hits']['hits']:
            source = hit['_source']

            # Skip the source record itself
            if source.get('id') == record_id:
                continue

            metadata = source.get('metadata', {})

            # Extract creators
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
                'record_id': source.get('id'),
                'title': metadata.get('title', 'Untitled'),
                'creators': creator_names,
                'publication_date': metadata.get('publication_date', ''),
                'resource_type': resource_type_title,
                'license': license_title,
                'access_status': access_status,
                'similarity_score': hit['_score'],
            }

            similar_records.append(result)

            # Stop once we have enough results
            if len(similar_records) >= limit:
                break

        return SimilarResult(
            record_id=record_id,
            similar=similar_records,
            total=len(similar_records),
            source_title=source_title,
            source_creators=source_creators,
        )

    def search_passages(self, identity, query: str, limit: int = 10):
        """Search document passages using AI-powered semantic search.

        This searches through document chunks (passages) to find semantically
        relevant text snippets that match the query. Perfect for questions like:
        - "find passages where the protagonist makes an important decision"
        - "show me where the main character embarks on their quest"

        Args:
            identity: User identity for access control
            query: Natural language search query
            limit: Maximum number of passages to return (default: 10)

        Returns:
            dict with passages and metadata
        """
        # Check if chunks feature is enabled
        if not current_app.config.get('INVENIO_AISEARCH_CHUNKS_ENABLED', False):
            current_app.logger.warning("Chunk search requested but CHUNKS_ENABLED is False")

        # Generate query embedding
        query_embedding = self.model_manager.generate_embedding(query)

        # Get chunks index name
        index_name = current_app.config.get('INVENIO_AISEARCH_CHUNKS_INDEX', 'document-chunks-v1')

        # Apply limit constraints
        max_limit = getattr(self.config, 'max_limit', 100)
        result_limit = min(limit, max_limit)

        # Build OpenSearch k-NN query for chunks
        search_body = {
            "size": result_limit,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding.tolist(),
                        "k": result_limit
                    }
                }
            },
            "_source": {
                "excludes": ["embedding"]  # Don't return the embedding vector
            }
        }

        # Execute search
        try:
            response = current_search_client.search(
                index=index_name,
                body=search_body
            )
        except Exception as e:
            current_app.logger.error(f"OpenSearch chunk k-NN query failed: {e}")
            return {
                'query': query,
                'passages': [],
                'total': 0,
                'error': str(e)
            }

        # Parse results
        passages = []
        for hit in response['hits']['hits']:
            source = hit['_source']

            passage = {
                'chunk_id': source.get('chunk_id'),
                'record_id': source.get('record_id'),
                'title': source.get('title', 'Untitled'),
                'creators': source.get('creators', 'Unknown'),
                'text': source.get('text', ''),
                'chunk_index': source.get('chunk_index', 0),
                'chunk_count': source.get('chunk_count', 0),
                'word_count': source.get('word_count', 0),
                'char_start': source.get('char_start', 0),
                'char_end': source.get('char_end', 0),
                'similarity_score': hit['_score'],  # k-NN similarity score
            }

            passages.append(passage)

        return {
            'query': query,
            'passages': passages,
            'total': len(passages),
        }

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
