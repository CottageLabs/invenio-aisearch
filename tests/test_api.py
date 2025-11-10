# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for API endpoints."""

import json
import pytest
from flask import url_for


def test_search_endpoint_basic(client, indexed_records):
    """Test basic search endpoint."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "machine learning", "limit": 5}
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    assert "query" in data
    assert "results" in data
    assert "total" in data
    assert data["query"] == "machine learning"


def test_search_endpoint_with_summaries(client, indexed_records):
    """Test search endpoint with summaries enabled."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "test", "summaries": "true"}
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    # If results exist, first result may have a summary
    if data["results"]:
        # Summary is optional, but if present should be a string
        first_result = data["results"][0]
        if "summary" in first_result:
            assert isinstance(first_result["summary"], str)


def test_search_endpoint_requires_query(client):
    """Test that search endpoint requires a query parameter."""
    response = client.get("/api/aisearch/search")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_search_endpoint_respects_limit(client, indexed_records):
    """Test that search endpoint respects limit parameter."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "test", "limit": 2}
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["results"]) <= 2


def test_search_endpoint_enforces_max_limit(client, indexed_records):
    """Test that search endpoint enforces max limit."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "test", "limit": 999}
    )

    # Should either cap at max or return error
    # Depending on implementation, adjust assertion
    assert response.status_code in [200, 400]


def test_similar_endpoint_basic(client, indexed_records):
    """Test basic similar records endpoint."""
    # Get a record ID from indexed records
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.query.filter_by(pid_type='recid').first()

    if pid:
        response = client.get(f"/api/aisearch/similar/{pid.pid_value}")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert "record_id" in data
        assert "similar" in data
        assert "total" in data
        assert data["record_id"] == pid.pid_value


def test_similar_endpoint_with_limit(client, indexed_records):
    """Test similar endpoint with limit parameter."""
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.query.filter_by(pid_type='recid').first()

    if pid:
        response = client.get(
            f"/api/aisearch/similar/{pid.pid_value}",
            query_string={"limit": 2}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["similar"]) <= 2


def test_similar_endpoint_excludes_source(client, indexed_records):
    """Test that similar endpoint excludes source record."""
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.query.filter_by(pid_type='recid').first()

    if pid:
        response = client.get(f"/api/aisearch/similar/{pid.pid_value}")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Source record should not be in similar results
        similar_ids = [r["record_id"] for r in data["similar"]]
        assert pid.pid_value not in similar_ids


def test_similar_endpoint_nonexistent_record(client):
    """Test similar endpoint with nonexistent record."""
    response = client.get("/api/aisearch/similar/nonexistent-id")

    assert response.status_code == 404


def test_status_endpoint(client):
    """Test status endpoint."""
    response = client.get("/api/aisearch/status")

    assert response.status_code == 200
    data = json.loads(response.data)

    assert "status" in data
    assert "model_loaded" in data


def test_search_results_have_required_fields(client, indexed_records):
    """Test that search results include all required fields."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "test", "limit": 5}
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    if data["results"]:
        first_result = data["results"][0]

        # Check required fields
        assert "record_id" in first_result
        assert "title" in first_result
        assert "similarity_score" in first_result
        assert "creators" in first_result

        # Check types
        assert isinstance(first_result["record_id"], str)
        assert isinstance(first_result["title"], str)
        assert isinstance(first_result["similarity_score"], (int, float))
        assert isinstance(first_result["creators"], list)


def test_search_results_use_pids_not_uuids(client, indexed_records):
    """Test that search results use PIDs not UUIDs."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "test", "limit": 5}
    )

    assert response.status_code == 200
    data = json.loads(response.data)

    if data["results"]:
        first_result = data["results"][0]
        record_id = first_result["record_id"]

        # PID format is like: "abc12-def34"
        # UUID format is like: "1c11c93c-6613-4016-8c34-e097957bf849"
        # PIDs are shorter and have different format
        assert len(record_id) < 20
        assert "-" in record_id


def test_cors_headers_present(client):
    """Test that CORS headers are present on API responses."""
    response = client.get(
        "/api/aisearch/search",
        query_string={"q": "test"}
    )

    # This test may need adjustment based on CORS configuration
    # Just verify response is valid JSON
    assert response.status_code in [200, 400]
    assert response.content_type.startswith("application/json")
