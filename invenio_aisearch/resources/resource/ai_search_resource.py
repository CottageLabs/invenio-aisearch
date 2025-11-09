# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Resource for handling AI search API endpoints."""

from flask import g
from flask_resources import Resource, resource_requestctx, response_handler, route
from invenio_records_resources.resources.records.resource import request_data, request_view_args
from marshmallow import ValidationError
from werkzeug.exceptions import BadRequest


class AISearchResource(Resource):
    """Resource for handling AI search endpoints."""

    def __init__(self, config, service):
        """Constructor.

        Args:
            config: Resource configuration
            service: AI search service instance
        """
        super().__init__(config)
        self.service = service

    def create_url_rules(self):
        """Create the URL rules for the AI search resource."""
        return [
            route("GET", self.config.routes["search"], self.search_get),
            route("POST", self.config.routes["search"], self.search_post),
            route("GET", self.config.routes["similar"], self.similar),
            route("GET", self.config.routes["status"], self.status),
        ]

    @response_handler()
    def search_get(self):
        """Handle GET request for AI search.

        Query parameters:
            q or query: Natural language query string
            limit: Maximum number of results
            summaries: Whether to include AI summaries (true/false)
            semantic_weight: Weight for semantic similarity (0-1)
            metadata_weight: Weight for metadata matching (0-1)

        Returns:
            Search results as JSON
        """
        try:
            # Parse query parameters using schema
            from ..config import AISearchResourceConfig
            schema = AISearchResourceConfig.request_search_args()
            params = schema.load(resource_requestctx.args)

            # Get query (prefer 'q', fall back to 'query')
            query = params.get('q') or params.get('query')
            if not query:
                raise BadRequest("Missing required parameter: 'q' or 'query'")

            # Perform search
            result = self.service.search(
                identity=g.identity,
                query=query,
                limit=params.get('limit'),
                include_summaries=params.get('summaries', False),
                semantic_weight=params.get('semantic_weight'),
                metadata_weight=params.get('metadata_weight'),
            )

            return result.to_dict(), 200

        except ValidationError as e:
            raise BadRequest(str(e.messages))
        except ValueError as e:
            return {"error": str(e)}, 503
        except Exception as e:
            return {"error": "Internal server error", "message": str(e)}, 500

    @request_data
    @response_handler()
    def search_post(self):
        """Handle POST request for AI search.

        Request body (JSON):
            q or query: Natural language query string
            limit: Maximum number of results
            summaries: Whether to include AI summaries
            semantic_weight: Weight for semantic similarity (0-1)
            metadata_weight: Weight for metadata matching (0-1)

        Returns:
            Search results as JSON
        """
        try:
            # Parse request body using schema
            from ..config import AISearchResourceConfig
            schema = AISearchResourceConfig.request_search_args()
            data = schema.load(resource_requestctx.data or {})

            # Get query (prefer 'q', fall back to 'query')
            query = data.get('q') or data.get('query')
            if not query:
                raise BadRequest("Missing required parameter: 'q' or 'query'")

            # Perform search
            result = self.service.search(
                identity=g.identity,
                query=query,
                limit=data.get('limit'),
                include_summaries=data.get('summaries', False),
                semantic_weight=data.get('semantic_weight'),
                metadata_weight=data.get('metadata_weight'),
            )

            return result.to_dict(), 200

        except ValidationError as e:
            raise BadRequest(str(e.messages))
        except ValueError as e:
            return {"error": str(e)}, 503
        except Exception as e:
            return {"error": "Internal server error", "message": str(e)}, 500

    @request_view_args
    @response_handler()
    def similar(self):
        """Handle GET request for finding similar records.

        URL parameters:
            record_id: InvenioRDM record ID (from URL path)

        Query parameters:
            limit: Maximum number of results

        Returns:
            Similar records as JSON
        """
        try:
            # Get record_id from URL path
            record_id = resource_requestctx.view_args.get("record_id")
            if not record_id:
                raise BadRequest("Missing required parameter: 'record_id'")

            # Parse query parameters
            from ..config import AISearchResourceConfig
            schema = AISearchResourceConfig.request_similar_args()
            params = schema.load(resource_requestctx.args)

            # Find similar records
            result = self.service.similar(
                identity=g.identity,
                record_id=record_id,
                limit=params.get('limit', 10),
            )

            return result.to_dict(), 200

        except ValidationError as e:
            raise BadRequest(str(e.messages))
        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception as e:
            return {"error": "Internal server error", "message": str(e)}, 500

    @response_handler()
    def status(self):
        """Handle GET request for service status check.

        Returns:
            Service status as JSON
        """
        try:
            result = self.service.status(identity=g.identity)
            return result.to_dict(), 200

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }, 500
