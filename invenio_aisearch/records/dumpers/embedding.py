# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Search dumper for AI embeddings."""

from flask import current_app
from invenio_records.dumpers import SearchDumperExt


class EmbeddingDumperExt(SearchDumperExt):
    """Search dumper extension for AI embeddings.

    On dump, it generates an embedding for the record's title and description
    and adds it to the search index for k-NN vector search.
    """

    def dump(self, record, data):
        """Generate and dump the embedding to the data dictionary."""
        # Skip drafts
        if record.is_draft:
            return

        try:
            # Get model manager from extension
            ext = current_app.extensions.get("invenio-aisearch")
            if not ext or not ext.model_manager:
                current_app.logger.warning("AI Search extension not initialized")
                return

            # Get title and description for embedding
            metadata = data.get("metadata", {})
            title = metadata.get("title", "")
            description = metadata.get("description", "")

            # Combine title and description for embedding
            text = title
            if description:
                text = f"{title}. {description}"

            if not text:
                current_app.logger.warning(
                    f"No text to embed for record {record.pid.pid_value}"
                )
                return

            # Generate embedding
            embedding = ext.model_manager.generate_embedding(text)

            # Add to search document
            data["aisearch"] = {"embedding": embedding.tolist()}

        except Exception as e:
            current_app.logger.error(
                f"Failed to generate embedding for record {record.pid.pid_value}: {e}"
            )

    def load(self, data, record_cls):
        """Remove embedding from data when loading from search index."""
        # We don't need embeddings in the record data
        data.pop("aisearch", None)
