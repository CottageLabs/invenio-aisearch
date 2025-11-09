# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio Jobs integration for AI search tasks."""

from invenio_jobs.jobs import JobType

from invenio_aisearch import tasks


class RegenerateEmbeddingsJob(JobType):
    """Job for regenerating embeddings for all records."""

    task = tasks.regenerate_all_embeddings
    id = 'regenerate_embeddings'
    title = 'Regenerate AI Search Embeddings'
    description = 'Generate embeddings for all InvenioRDM records for semantic search'
