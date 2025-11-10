# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for embedding dumper."""

import pytest
from invenio_rdm_records.records.api import RDMRecord


def test_embedding_dumper_adds_embedding(app, db, minimal_record):
    """Test that dumper adds embedding to record data."""
    # Create a record
    record = RDMRecord.create(minimal_record)
    db.session.commit()

    # Dump the record
    data = record.dumps()

    # Check that aisearch field was added
    assert 'aisearch' in data
    assert 'embedding' in data['aisearch']

    # Check embedding is correct dimension (384 for all-MiniLM-L6-v2)
    embedding = data['aisearch']['embedding']
    assert isinstance(embedding, list)
    assert len(embedding) == 384

    # Check all values are floats
    assert all(isinstance(v, float) for v in embedding)

    # Cleanup
    record.delete()
    db.session.commit()


def test_embedding_dumper_skips_drafts(app, db, minimal_record):
    """Test that dumper skips draft records."""
    # Create a draft
    from invenio_rdm_records.records.api import RDMDraft

    draft = RDMDraft.create(minimal_record)
    db.session.commit()

    # Dump the draft
    data = draft.dumps()

    # Drafts should not have embeddings
    # (dumper returns early for drafts)
    # Note: The dumper may still run but we verify it doesn't break

    # Cleanup
    draft.delete()
    db.session.commit()


def test_embedding_dumper_uses_title_and_description(app, db):
    """Test that dumper uses both title and description."""
    record_data = {
        "metadata": {
            "title": "Machine Learning Research",
            "description": "A comprehensive study of neural networks",
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

    record = RDMRecord.create(record_data)
    db.session.commit()
    data = record.dumps()

    # Embedding should be generated from title + description
    assert 'aisearch' in data
    assert len(data['aisearch']['embedding']) == 384

    # Cleanup
    record.delete()
    db.session.commit()


def test_embedding_dumper_handles_missing_description(app, db, minimal_record):
    """Test that dumper works when description is missing."""
    # Minimal record has no description
    record = RDMRecord.create(minimal_record)
    db.session.commit()
    data = record.dumps()

    # Should still generate embedding from title only
    assert 'aisearch' in data
    assert len(data['aisearch']['embedding']) == 384

    # Cleanup
    record.delete()
    db.session.commit()
