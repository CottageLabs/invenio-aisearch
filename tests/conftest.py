# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

import pytest


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory fixture."""
    from invenio_app.factory import create_app as _create_app
    return _create_app


@pytest.fixture()
def minimal_record():
    """Minimal record data fixture."""
    return {
        "metadata": {
            "title": "Test Record",
            "resource_type": {"id": "publication-article"},
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "given_name": "John",
                        "family_name": "Doe",
                    }
                }
            ],
            "publication_date": "2025-01-01",
        }
    }


@pytest.fixture()
def indexed_records(app, db, minimal_record):
    """Create and index multiple test records."""
    from invenio_rdm_records.records.api import RDMRecord
    from invenio_search import current_search_client

    records = []

    # Create multiple records with different titles
    test_data = [
        {
            "title": "Machine Learning Fundamentals",
            "description": "An introduction to machine learning algorithms",
        },
        {
            "title": "Deep Neural Networks",
            "description": "Advanced study of deep learning architectures",
        },
        {
            "title": "Natural Language Processing",
            "description": "Text analysis and language understanding",
        },
    ]

    for data in test_data:
        record_data = minimal_record.copy()
        record_data["metadata"]["title"] = data["title"]
        if "description" in data:
            record_data["metadata"]["description"] = data["description"]

        # Create record
        record = RDMRecord.create(record_data)
        db.session.commit()

        # Index the record
        record.index()
        records.append(record)

    # Refresh index to make records available for search
    current_search_client.indices.refresh()

    yield records

    # Cleanup
    for record in records:
        record.delete()
    db.session.commit()
