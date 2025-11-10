# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Basic tests for invenio-aisearch components."""

import pytest


def test_extension_initialization():
    """Test that the extension can be initialized."""
    from flask import Flask
    from invenio_aisearch import invenioaisearch

    app = Flask('testapp')
    ext = invenioaisearch(app)

    assert 'invenio-aisearch' in app.extensions
    assert ext.model_manager is not None


def test_model_manager_loads():
    """Test that model manager initializes."""
    from invenio_aisearch.models import ModelManager

    manager = ModelManager()

    assert manager is not None
    assert manager.cache_dir is not None


def test_generate_embedding():
    """Test that embeddings can be generated."""
    from invenio_aisearch.models import ModelManager

    manager = ModelManager()
    text = "This is a test document about machine learning"

    embedding = manager.generate_embedding(text)

    # The method returns a numpy array, convert to list
    embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

    assert isinstance(embedding_list, list)
    assert len(embedding_list) == 384
    assert all(isinstance(v, float) for v in embedding_list)


def test_generate_embedding_from_title_and_description():
    """Test embedding generation from title and description."""
    from invenio_aisearch.models import ModelManager

    manager = ModelManager()

    title = "Machine Learning Fundamentals"
    description = "An introduction to neural networks and deep learning"

    # Test combined text
    combined_text = f"{title}. {description}"
    embedding = manager.generate_embedding(combined_text)

    assert len(embedding) == 384


def test_config_defaults():
    """Test that configuration defaults are set."""
    from invenio_aisearch import config

    assert hasattr(config, 'INVENIO_AISEARCH_DEFAULT_LIMIT')
    assert hasattr(config, 'INVENIO_AISEARCH_MAX_LIMIT')
    assert hasattr(config, 'INVENIO_AISEARCH_BASE_TEMPLATE')

    assert config.INVENIO_AISEARCH_DEFAULT_LIMIT == 10
    assert config.INVENIO_AISEARCH_MAX_LIMIT == 100


def test_search_result_structure():
    """Test SearchResult class structure."""
    from invenio_aisearch.services.results import SearchResult

    result_data = {
        'query': 'test query',
        'total': 5,
        'parsed': {},
        'results': [
            {
                'record_id': 'test-123',
                'title': 'Test Record',
                'similarity_score': 0.95,
                'creators': ['John Doe']
            }
        ]
    }

    result = SearchResult(**result_data)
    result_dict = result.to_dict()

    assert result_dict['query'] == 'test query'
    assert result_dict['total'] == 5
    assert len(result_dict['results']) == 1
    assert result_dict['results'][0]['record_id'] == 'test-123'


def test_similar_result_structure():
    """Test SimilarResult class structure."""
    from invenio_aisearch.services.results import SimilarResult

    result_data = {
        'record_id': 'source-123',
        'total': 3,
        'similar': [
            {
                'record_id': 'similar-456',
                'title': 'Similar Record',
                'similarity_score': 0.85,
                'creators': ['Jane Smith']
            }
        ]
    }

    result = SimilarResult(**result_data)
    result_dict = result.to_dict()

    assert result_dict['record_id'] == 'source-123'
    assert result_dict['total'] == 3
    assert len(result_dict['similar']) == 1


def test_status_result_structure():
    """Test StatusResult class structure."""
    from invenio_aisearch.services.results import StatusResult

    result = StatusResult(
        status='ok',
        model_loaded=True,
        opensearch_version='2.0.0',
        knn_plugin_available=True
    )

    result_dict = result.to_dict()

    assert result_dict['status'] == 'ok'
    assert result_dict['model_loaded'] is True
    assert result_dict['opensearch_version'] == '2.0.0'
    assert result_dict['knn_plugin_available'] is True


def test_index_template_name_format():
    """Test index template naming."""
    # Template should follow pattern: {prefix}rdmrecords-records-record-v7.0.0-knn
    template_suffix = "rdmrecords-records-record-v7.0.0-knn"

    # With prefix
    prefix = "test-"
    full_name = f"{prefix}{template_suffix}"

    assert "rdmrecords" in full_name
    assert "knn" in full_name
    assert full_name.endswith("-knn")
