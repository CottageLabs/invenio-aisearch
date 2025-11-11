# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Resource configuration for AI search."""

import marshmallow as ma
from flask_resources import (
    JSONDeserializer,
    JSONSerializer,
    RequestBodyParser,
    ResourceConfig,
    ResponseHandler,
)

from ..services.schemas import (
    SearchRequestSchema,
    SimilarRequestSchema,
)


class AISearchResourceConfig(ResourceConfig):
    """Configuration for the AI Search API resource."""

    blueprint_name = "ai_search_api"
    url_prefix = "/aisearch"

    # Routes
    routes = {
        "search": "/search",
        "similar": "/similar/<record_id>",
        "passages": "/passages",
        "status": "/status",
    }

    # Request view arguments
    request_view_args = {
        "record_id": ma.fields.String(),
    }

    # Request parsers for different content types
    request_body_parsers = {
        "application/json": RequestBodyParser(JSONDeserializer()),
    }

    # Default content type
    default_content_type = "application/json"

    # Response handlers for different content types
    response_handlers = {
        "application/json": ResponseHandler(JSONSerializer()),
        "application/vnd.inveniordm.v1+json": ResponseHandler(JSONSerializer()),
    }

    # Request search args schemas (for GET parameters)
    request_search_args = SearchRequestSchema
    request_similar_args = SimilarRequestSchema
