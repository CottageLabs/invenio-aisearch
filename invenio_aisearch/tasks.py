# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for AI search operations.

Note: With the k-NN approach, embeddings are generated automatically
during record indexing via EmbeddingDumperExt. No separate task needed.

To regenerate embeddings for all records, use:
    invenio index reindex --yes-i-know -t recid
    invenio index run
"""

from celery import shared_task
from flask import current_app


@shared_task(ignore_result=True)
def example_task():
    """Placeholder for future AI search tasks.

    With k-NN, embeddings are generated automatically during indexing,
    so no manual embedding generation tasks are needed.
    """
    current_app.logger.info("AI search task placeholder - no tasks needed with k-NN")
    pass
