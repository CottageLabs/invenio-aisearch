# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""API views for AI-powered search."""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from .search_service import get_search_service

# Create the API blueprint
api_blueprint = Blueprint(
    "invenio_aisearch_api",
    __name__,
    url_prefix="/api/aisearch",
)

@api_blueprint.route("/search", methods=["GET", "POST"])
def search():
    """AI-powered search endpoint.

    Query parameters (GET) or JSON body (POST):
        q (str): Natural language query
        limit (int, optional): Maximum results
        summaries (bool, optional): Include AI summaries

    Returns:
        JSON response with search results
    """
    try:
        # Get parameters from either GET or POST
        if request.method == "POST":
            data = request.get_json() or {}
            query = data.get("q") or data.get("query")
            limit = data.get("limit")
            include_summaries = data.get("summaries", False)
        else:  # GET
            query = request.args.get("q") or request.args.get("query")
            limit = request.args.get("limit", type=int)
            include_summaries = request.args.get("summaries", "false").lower() == "true"

        if not query:
            raise BadRequest("Missing required parameter: 'q' or 'query'")

        # Get embeddings file path from config
        embeddings_file = current_app.config.get("INVENIO_AISEARCH_EMBEDDINGS_FILE")
        if not embeddings_file:
            return jsonify({
                "error": "AI search not configured",
                "message": "INVENIO_AISEARCH_EMBEDDINGS_FILE not set"
            }), 503

        # Perform search
        service = get_search_service(embeddings_file)
        results = service.search(
            query=query,
            limit=limit,
            include_summaries=include_summaries
        )

        return jsonify(results)

    except BadRequest as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"AI search error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_blueprint.route("/similar/<record_id>", methods=["GET"])
def similar(record_id):
    """Find similar records endpoint.

    Args:
        record_id: InvenioRDM record ID

    Query parameters:
        limit (int, optional): Maximum results (default: 10)

    Returns:
        JSON response with similar records
    """
    try:
        limit = request.args.get("limit", 10, type=int)

        # Get embeddings file path from config
        embeddings_file = current_app.config.get("INVENIO_AISEARCH_EMBEDDINGS_FILE")
        if not embeddings_file:
            return jsonify({
                "error": "AI search not configured",
                "message": "INVENIO_AISEARCH_EMBEDDINGS_FILE not set"
            }), 503

        # Find similar records
        service = get_search_service(embeddings_file)
        results = service.search_by_record_id(record_id, limit=limit)

        return jsonify({
            "record_id": record_id,
            "similar": results,
            "total": len(results),
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Similar records error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_blueprint.route("/status", methods=["GET"])
def status():
    """Check AI search service status.

    Returns:
        JSON response with service status
    """
    try:
        embeddings_file = current_app.config.get("INVENIO_AISEARCH_EMBEDDINGS_FILE")

        if not embeddings_file:
            return jsonify({
                "status": "not_configured",
                "message": "INVENIO_AISEARCH_EMBEDDINGS_FILE not set",
                "embeddings_loaded": False,
                "embeddings_count": 0,
            })

        service = get_search_service(embeddings_file)

        return jsonify({
            "status": "ready" if service.embeddings else "no_embeddings",
            "embeddings_loaded": bool(service.embeddings),
            "embeddings_count": len(service.embeddings),
            "embeddings_file": embeddings_file,
        })

    except Exception as e:
        current_app.logger.error(f"Status check error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e),
        }), 500



# Entry point factory function for InvenioRDM
def create_api_blueprint(app):
    """Factory function to return the API blueprint.

    Args:
        app: Flask application instance (unused for plain blueprints)

    Returns:
        Blueprint for AI search API
    """
    return api_blueprint
