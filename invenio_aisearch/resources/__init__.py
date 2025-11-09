# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""AI Search resources."""

from .config import AISearchResourceConfig
from .resource.ai_search_resource import AISearchResource

__all__ = (
    "AISearchResource",
    "AISearchResourceConfig",
)
