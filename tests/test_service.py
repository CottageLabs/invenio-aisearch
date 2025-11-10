# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for AI search service."""

import pytest
from invenio_access.permissions import system_identity
from invenio_rdm_records.records.api import RDMRecord
from invenio_search import current_search_client


def test_search_service_basic_query(app, indexed_records):
    """Test basic k-NN search query."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    # Search for something semantically related to the test data
    result = service.search(
        identity=system_identity,
        query="machine learning",
        limit=5,
        include_summaries=False
    )

    # Convert to dict
    data = result.to_dict()

    # Should return results
    assert 'query' in data
    assert 'results' in data
    assert 'total' in data
    assert data['query'] == "machine learning"


def test_search_service_returns_similarity_scores(app, indexed_records):
    """Test that search returns similarity scores."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="test query",
        limit=5,
        include_summaries=False
    )

    data = result.to_dict()

    if data['results']:
        # Check first result has similarity_score
        first_result = data['results'][0]
        assert 'similarity_score' in first_result
        assert isinstance(first_result['similarity_score'], float)
        assert first_result['similarity_score'] > 0


def test_search_service_returns_pids(app, indexed_records):
    """Test that search returns PIDs not UUIDs."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="test",
        limit=5,
        include_summaries=False
    )

    data = result.to_dict()

    if data['results']:
        first_result = data['results'][0]
        record_id = first_result['record_id']

        # PID format is like: "abc12-def34"
        # UUID format is like: "1c11c93c-6613-4016-8c34-e097957bf849"
        # PIDs are shorter and have different format
        assert len(record_id) < 20  # PIDs are much shorter than UUIDs
        assert '-' in record_id  # Both have hyphens, but PIDs have fewer


def test_search_service_respects_limit(app, indexed_records):
    """Test that limit parameter works."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="test",
        limit=3,
        include_summaries=False
    )

    data = result.to_dict()
    assert len(data['results']) <= 3


def test_search_service_includes_metadata(app, indexed_records):
    """Test that results include record metadata."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.search(
        identity=system_identity,
        query="test",
        limit=5,
        include_summaries=False
    )

    data = result.to_dict()

    if data['results']:
        first_result = data['results'][0]
        # Check expected fields
        assert 'record_id' in first_result
        assert 'title' in first_result
        assert 'creators' in first_result
        assert 'similarity_score' in first_result


def test_similar_service_finds_similar_records(app, indexed_records):
    """Test similar records functionality."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    # Get a record ID from indexed records
    # We need to get an actual PID from the test data
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.query.filter_by(pid_type='recid').first()

    if pid:
        result = service.similar(
            identity=system_identity,
            record_id=pid.pid_value,
            limit=5
        )

        data = result.to_dict()

        # Check structure
        assert 'record_id' in data
        assert 'similar' in data
        assert 'total' in data
        assert data['record_id'] == pid.pid_value


def test_similar_service_excludes_source_record(app, indexed_records):
    """Test that similar records excludes the source record."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.query.filter_by(pid_type='recid').first()

    if pid:
        result = service.similar(
            identity=system_identity,
            record_id=pid.pid_value,
            limit=10
        )

        data = result.to_dict()

        # Source record should not be in results
        similar_ids = [r['record_id'] for r in data['similar']]
        assert pid.pid_value not in similar_ids


def test_service_handles_empty_results(app):
    """Test service handles queries with no results gracefully."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    # Query on empty index
    result = service.search(
        identity=system_identity,
        query="nonexistent query xyz123",
        limit=5,
        include_summaries=False
    )

    data = result.to_dict()
    assert data['results'] == []
    assert data['total'] == 0


def test_status_service(app):
    """Test status service method."""
    ext = app.extensions.get("invenio-aisearch")
    service = ext.search_service

    result = service.status()
    data = result.to_dict()

    # Check status response structure
    assert 'status' in data
    assert 'model_loaded' in data
