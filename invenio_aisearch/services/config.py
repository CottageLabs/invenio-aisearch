# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Service configuration for AI search."""


class AISearchServiceConfig:
    """Configuration for AI search service."""

    # Default search parameters
    default_limit = 10
    max_limit = 100

    # Summary generation
    enable_summaries = True
    summary_max_length = 150
    summary_min_length = 50
