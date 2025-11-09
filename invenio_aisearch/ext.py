# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Adds an AI-powered search interface to InvenioRDM."""

from flask import current_app

from . import config
from .resources import AISearchResource, AISearchResourceConfig
from .services import AISearchService, AISearchServiceConfig


class InvenioAISearch(object):
    """invenio-aisearch extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.init_services(app)
        self.init_resources(app)
        app.extensions["invenio-aisearch"] = self

    def init_config(self, app):
        """Initialize configuration."""
        # Use theme's base template if theme is installed
        if "BASE_TEMPLATE" in app.config:
            app.config.setdefault(
                "INVENIO_AISEARCH_BASE_TEMPLATE",
                app.config["BASE_TEMPLATE"],
            )
        # Load all INVENIO_AISEARCH_* config variables
        for k in dir(config):
            if k.startswith("INVENIO_AISEARCH_"):
                app.config.setdefault(k, getattr(config, k))

    def init_services(self, app):
        """Initialize the AI search service."""
        # Create service with configuration
        self.search_service = AISearchService(config=AISearchServiceConfig)

        # Load embeddings if configured
        embeddings_file = app.config.get("INVENIO_AISEARCH_EMBEDDINGS_FILE")
        if embeddings_file:
            try:
                self.search_service.load_embeddings(embeddings_file)
                app.logger.info(f"AI Search: Loaded embeddings from {embeddings_file}")
            except Exception as e:
                app.logger.warning(f"AI Search: Failed to load embeddings: {e}")

    def init_resources(self, app):
        """Initialize the AI search resource."""
        self.search_resource = AISearchResource(
            config=AISearchResourceConfig,
            service=self.search_service,
        )


# Keep backward compatibility
invenioaisearch = InvenioAISearch
