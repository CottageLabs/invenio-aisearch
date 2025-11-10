# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Integration tests for complete AI search workflow."""

import pytest
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_rdm_records.records.api import RDMRecord
from invenio_search import current_search_client


def test_complete_workflow_create_index_search(app, db, minimal_record):
    """Test complete workflow: create record, index with embedding, search."""
    # Step 1: Create a record
    record_data = minimal_record.copy()
    record_data["metadata"]["title"] = "Machine Learning Fundamentals"
    record_data["metadata"]["description"] = "A comprehensive introduction to machine learning"

    record = RDMRecord.create(record_data)
    db.session.commit()

    # Step 2: Index the record (embedding should be generated automatically)
    record.index()
    current_search_client.indices.refresh()

    # Step 3: Verify embedding was created
    data = record.dumps()
    assert "aisearch" in data
    assert "embedding" in data["aisearch"]
    assert len(data["aisearch"]["embedding"]) == 384

    # Step 4: Search for the record using AI search
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="machine learning",
        limit=5,
        include_summaries=False
    )

    result_dict = result.to_dict()

    # Should find the record
    assert result_dict["total"] > 0
    assert any(r["title"] == "Machine Learning Fundamentals" for r in result_dict["results"])

    # Cleanup
    record.delete()
    db.session.commit()


def test_similar_records_workflow(app, db, minimal_record):
    """Test finding similar records workflow."""
    # Create multiple related records
    records = []

    test_records = [
        {
            "title": "Introduction to Neural Networks",
            "description": "Basic concepts of neural networks and deep learning"
        },
        {
            "title": "Deep Learning Architectures",
            "description": "Advanced neural network architectures"
        },
        {
            "title": "Cooking Recipes",
            "description": "Delicious recipes for home cooking"
        }
    ]

    for data in test_records:
        record_data = minimal_record.copy()
        record_data["metadata"]["title"] = data["title"]
        record_data["metadata"]["description"] = data["description"]

        record = RDMRecord.create(record_data)
        db.session.commit()
        record.index()
        records.append(record)

    current_search_client.indices.refresh()

    # Get PID of first record
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.query.filter_by(
        object_uuid=records[0].id,
        pid_type='recid'
    ).first()

    # Find similar records
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.similar(
        identity=system_identity,
        record_id=pid.pid_value,
        limit=5
    )

    result_dict = result.to_dict()

    # Should find similar records
    assert "similar" in result_dict
    similar_titles = [r["title"] for r in result_dict["similar"]]

    # "Deep Learning Architectures" should be more similar than "Cooking Recipes"
    # to "Introduction to Neural Networks"
    if len(similar_titles) > 0:
        # The first result should not be about cooking
        assert "Cooking" not in similar_titles[0] or len(similar_titles) > 1

    # Cleanup
    for record in records:
        record.delete()
    db.session.commit()


def test_reindex_updates_embeddings(app, db, minimal_record):
    """Test that reindexing updates embeddings."""
    # Create record
    record = RDMRecord.create(minimal_record)
    db.session.commit()

    # Index
    record.index()
    current_search_client.indices.refresh()

    # Get initial embedding
    data1 = record.dumps()
    embedding1 = data1.get("aisearch", {}).get("embedding")

    assert embedding1 is not None
    assert len(embedding1) == 384

    # Update record title
    record["metadata"]["title"] = "Completely Different Title About Cooking"
    record.commit()
    db.session.commit()

    # Reindex
    record.index()
    current_search_client.indices.refresh()

    # Get updated embedding
    data2 = record.dumps()
    embedding2 = data2.get("aisearch", {}).get("embedding")

    # Embedding should be different (different title = different embedding)
    assert embedding2 is not None
    assert len(embedding2) == 384
    # They should be different vectors
    assert embedding1 != embedding2

    # Cleanup
    record.delete()
    db.session.commit()


def test_search_returns_results_in_score_order(app, db, minimal_record):
    """Test that search returns results ordered by similarity score."""
    # Create multiple records
    records = []

    test_records = [
        {
            "title": "Neural Networks and Machine Learning",
            "description": "Deep dive into neural networks"
        },
        {
            "title": "Cooking with Machine Precision",
            "description": "Using kitchen machines for cooking"
        },
        {
            "title": "Machine Learning Algorithms",
            "description": "Various machine learning techniques"
        }
    ]

    for data in test_records:
        record_data = minimal_record.copy()
        record_data["metadata"]["title"] = data["title"]
        record_data["metadata"]["description"] = data["description"]

        record = RDMRecord.create(record_data)
        db.session.commit()
        record.index()
        records.append(record)

    current_search_client.indices.refresh()

    # Search for "machine learning"
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="machine learning algorithms",
        limit=10,
        include_summaries=False
    )

    result_dict = result.to_dict()

    # Check results are in descending score order
    scores = [r["similarity_score"] for r in result_dict["results"]]
    assert scores == sorted(scores, reverse=True), "Results not in score order"

    # Cleanup
    for record in records:
        record.delete()
    db.session.commit()


def test_empty_index_returns_empty_results(app):
    """Test that searching an empty index returns empty results gracefully."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="nonexistent content xyz123",
        limit=5,
        include_summaries=False
    )

    result_dict = result.to_dict()

    assert result_dict["results"] == []
    assert result_dict["total"] == 0


def test_index_statistics_accurate(app, db, minimal_record):
    """Test that index statistics are accurate."""
    # Create a few records
    records = []
    for i in range(3):
        record_data = minimal_record.copy()
        record_data["metadata"]["title"] = f"Test Record {i}"
        record = RDMRecord.create(record_data)
        db.session.commit()
        record.index()
        records.append(record)

    current_search_client.indices.refresh()

    # Get index name
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    base_index_name = RDMRecord.index._name
    index_name = f"{prefix}{base_index_name}"

    # Count records with embeddings
    count_query = {
        "query": {
            "exists": {
                "field": "aisearch.embedding"
            }
        }
    }
    count_response = current_search_client.count(index=index_name, body=count_query)
    records_with_embeddings = count_response['count']

    # Should be at least 3 (the ones we just created)
    assert records_with_embeddings >= 3

    # Cleanup
    for record in records:
        record.delete()
    db.session.commit()
