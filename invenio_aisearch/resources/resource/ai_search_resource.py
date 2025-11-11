# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Resource for handling AI search API endpoints."""

from flask import g
from flask_resources import Resource, resource_requestctx, response_handler, route
from flask_resources.parsers import request_parser
from flask_resources.resources import from_conf
from invenio_records_resources.resources.records.resource import request_data, request_search_args, request_view_args
from werkzeug.exceptions import BadRequest

# Create decorator for similar endpoint search args
request_similar_args = request_parser(from_conf("request_similar_args"), location="args")


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
            route("GET", self.config.routes["passages"], self.passages),
            route("GET", self.config.routes["status"], self.status),
        ]

    @request_search_args
    @response_handler()
    def search_get(self):
        """Handle GET request for AI search.

        Query parameters:
            q or query: Natural language query string
            limit: Maximum number of results
            summaries: Whether to include AI summaries (true/false)
            passages: Whether to include passage results (true/false)

        Returns:
            Search results as JSON
        """
        try:
            # Get query parameters from args (populated and validated by @request_search_args)
            args = resource_requestctx.args or {}

            query = args.get('q') or args.get('query')
            if not query:
                raise BadRequest("Missing required parameter: 'q' or 'query'")

            # Schema already converted types, just extract values
            limit = args.get('limit')
            summaries = args.get('summaries', False)
            passages = args.get('passages')  # None = use config default, True/False = override

            # Perform search using OpenSearch k-NN
            result = self.service.search(
                identity=g.identity,
                query=query,
                limit=limit,
                include_summaries=summaries,
                include_passages=passages,
            )

            return result.to_dict(), 200

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
            passages: Whether to include passage results

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

            # Perform search using OpenSearch k-NN
            result = self.service.search(
                identity=g.identity,
                query=query,
                limit=data.get('limit'),
                include_summaries=data.get('summaries', False),
                include_passages=data.get('passages'),  # None = use config default
            )

            return result.to_dict(), 200

        except ValueError as e:
            return {"error": str(e)}, 503
        except Exception as e:
            return {"error": "Internal server error", "message": str(e)}, 500

    @request_similar_args
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

            # Get query parameters from args (populated and validated by @request_search_args)
            args = resource_requestctx.args or {}
            limit = args.get('limit', 10)  # Schema sets default to 10

            # Find similar records
            result = self.service.similar(
                identity=g.identity,
                record_id=record_id,
                limit=limit,
            )

            return result.to_dict(), 200

        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception as e:
            return {"error": "Internal server error", "message": str(e)}, 500

    @request_search_args
    @response_handler()
    def passages(self):
        """Handle GET request for passage/chunk search.

        Query parameters:
            q or query: Natural language query string
            limit: Maximum number of passages to return

        Returns:
            Matching passages as JSON
        """
        try:
            # Get query parameters from args
            args = resource_requestctx.args or {}

            query = args.get('q') or args.get('query')
            if not query:
                raise BadRequest("Missing required parameter: 'q' or 'query'")

            # Schema already converted types
            limit = args.get('limit', 10)

            # Perform passage search
            result = self.service.search_passages(
                identity=g.identity,
                query=query,
                limit=limit,
            )

            return result, 200

        except ValueError as e:
            return {"error": str(e)}, 503
        except Exception as e:
            return {"error": "Internal server error", "message": str(e)}, 500

    @response_handler()
    def status(self):
        """Handle GET request for service status check.

        Returns:
            Service status as JSON
        """
        try:
            result = self.service.status()
            return result.to_dict(), 200

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }, 500
