# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Blueprint factory functions for AI search."""


def create_ai_search_api_bp(app):
    """Create AI search API blueprint.

    Args:
        app: Flask application instance

    Returns:
        Blueprint for AI search API endpoints
    """
    return app.extensions["invenio-aisearch"].search_resource.as_blueprint()
