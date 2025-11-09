# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""AI Search services."""

from .config import AISearchServiceConfig
from .results import SearchResult, SimilarResult, StatusResult
from .schemas import (
    SearchRequestSchema,
    SearchResponseSchema,
    SimilarRequestSchema,
    SimilarResponseSchema,
    StatusResponseSchema,
)
from .service.ai_search_service import AISearchService

__all__ = (
    "AISearchService",
    "AISearchServiceConfig",
    "SearchResult",
    "SimilarResult",
    "StatusResult",
    "SearchRequestSchema",
    "SearchResponseSchema",
    "SimilarRequestSchema",
    "SimilarResponseSchema",
    "StatusResponseSchema",
)
