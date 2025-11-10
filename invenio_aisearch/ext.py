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
        # TODO: Fix index patching - currently disabled
        # self.init_index_patch(app)
        self.init_dumper(app)
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

        # Make model manager available for dumpers
        self.model_manager = self.search_service.model_manager

    def init_resources(self, app):
        """Initialize the AI search resource."""
        self.search_resource = AISearchResource(
            config=AISearchResourceConfig,
            service=self.search_service,
        )

    def init_index_patch(self, app):
        """Patch InvenioSearch.create_index to enable k-NN support for RDM records."""
        # We'll patch when invenio-search extension is initialized
        # Store this extension for later access
        app.config.setdefault('AISEARCH_KNN_ENABLED', True)

        # Register an init_app callback that runs after invenio-search is initialized
        @app.before_first_request
        def _apply_knn_patch():
            from invenio_search.proxies import current_search
            import json

            # Get the search extension instance
            search_ext = current_search._get_current_object()

            # Store original create_index method
            original_create_index = search_ext.create_index

            def patched_create_index(
                index,
                mapping_path=None,
                prefix=None,
                suffix=None,
                create_write_alias=True,
                ignore=None,
                dry_run=False,
            ):
                """Patched create_index that adds k-NN settings for RDM records."""
                # Check if this is an RDM records index
                if 'rdmrecords-records-record' in index:
                    # Patch the client.indices.create method temporarily
                    original_client_create = search_ext.client.indices.create

                    def patched_client_create(index=None, body=None, **kwargs):
                        """Add k-NN settings to the body."""
                        # Ensure body has settings
                        if body is None:
                            body = {}
                        if 'settings' not in body:
                            body['settings'] = {}
                        if 'index' not in body['settings']:
                            body['settings']['index'] = {}

                        # Enable k-NN
                        body['settings']['index']['knn'] = True
                        app.logger.info(f"AI Search: Enabling k-NN for index {index}")

                        # Call original
                        return original_client_create(index=index, body=body, **kwargs)

                    # Apply temporary patch
                    search_ext.client.indices.create = patched_client_create

                    try:
                        # Call original method with patched client
                        result = original_create_index(
                            index, mapping_path, prefix, suffix,
                            create_write_alias, ignore, dry_run
                        )
                    finally:
                        # Restore original client method
                        search_ext.client.indices.create = original_client_create

                    return result
                else:
                    # Not an RDM records index, call original
                    return original_create_index(
                        index, mapping_path, prefix, suffix,
                        create_write_alias, ignore, dry_run
                    )

            # Monkey-patch the create_index method on the instance
            search_ext.create_index = patched_create_index
            app.logger.info("AI Search: Patched InvenioSearch.create_index to enable k-NN")

    def init_dumper(self, app):
        """Add our embedding dumper to RDM records."""
        # Import here to avoid circular imports
        from invenio_rdm_records.records.api import RDMRecord, RDMDraft
        from .records.dumpers import EmbeddingDumperExt

        # Add our dumper extension to RDM records and drafts
        RDMRecord.dumper._extensions.append(EmbeddingDumperExt())
        RDMDraft.dumper._extensions.append(EmbeddingDumperExt())
        app.logger.info("AI Search: Registered embedding dumper")


# Keep backward compatibility
invenioaisearch = InvenioAISearch
