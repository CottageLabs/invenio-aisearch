# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for k-NN index template configuration."""

import pytest
from flask import current_app
from invenio_search import current_search_client
from invenio_rdm_records.records.api import RDMRecord


def test_index_template_exists(app):
    """Test that k-NN index template is registered."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Check if template exists
    templates = current_search_client.indices.get_index_template()
    template_names = [t['name'] for t in templates.get('index_templates', [])]

    assert template_name in template_names, f"Template {template_name} not found"


def test_index_template_has_knn_settings(app):
    """Test that index template includes k-NN settings."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Get template configuration
    template = current_search_client.indices.get_index_template(name=template_name)

    # Navigate to settings
    template_data = template['index_templates'][0]['index_template']
    settings = template_data.get('template', {}).get('settings', {})

    # Check k-NN is enabled
    assert settings.get('index', {}).get('knn') == 'true', "k-NN not enabled in template"


def test_index_template_has_embedding_mapping(app):
    """Test that index template includes embedding field mapping."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Get template configuration
    template = current_search_client.indices.get_index_template(name=template_name)

    # Navigate to mappings
    template_data = template['index_templates'][0]['index_template']
    mappings = template_data.get('template', {}).get('mappings', {})
    properties = mappings.get('properties', {})

    # Check aisearch field exists
    assert 'aisearch' in properties, "aisearch field not in template mappings"

    # Check embedding subfield
    aisearch_props = properties['aisearch'].get('properties', {})
    assert 'embedding' in aisearch_props, "embedding field not in aisearch properties"

    # Check embedding is knn_vector type
    embedding_config = aisearch_props['embedding']
    assert embedding_config.get('type') == 'knn_vector', "embedding is not knn_vector type"
    assert embedding_config.get('dimension') == 384, "embedding dimension is not 384"


def test_index_template_embedding_uses_hnsw(app):
    """Test that embedding field uses HNSW algorithm."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Get template configuration
    template = current_search_client.indices.get_index_template(name=template_name)

    # Navigate to embedding field
    template_data = template['index_templates'][0]['index_template']
    mappings = template_data.get('template', {}).get('mappings', {})
    embedding_config = mappings.get('properties', {}).get('aisearch', {}).get('properties', {}).get('embedding', {})

    # Check HNSW method
    method = embedding_config.get('method', {})
    assert method.get('name') == 'hnsw', "embedding does not use HNSW algorithm"


def test_index_template_embedding_uses_cosine(app):
    """Test that embedding field uses cosine similarity."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Get template configuration
    template = current_search_client.indices.get_index_template(name=template_name)

    # Navigate to embedding field
    template_data = template['index_templates'][0]['index_template']
    mappings = template_data.get('template', {}).get('mappings', {})
    embedding_config = mappings.get('properties', {}).get('aisearch', {}).get('properties', {}).get('embedding', {})

    # Check space type
    space_type = embedding_config.get('method', {}).get('space_type')
    assert space_type == 'cosinesimil', "embedding does not use cosine similarity"


def test_record_index_has_knn_enabled(app, db, minimal_record):
    """Test that actual record index has k-NN enabled."""
    # Create a record to ensure index exists
    record = RDMRecord.create(minimal_record)
    db.session.commit()
    record.index()

    # Get index name
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    base_index_name = RDMRecord.index._name
    index_name = f"{prefix}{base_index_name}"

    # Get index settings
    index_settings = current_search_client.indices.get_settings(index=index_name)
    first_index = list(index_settings.keys())[0]
    settings = index_settings[first_index]['settings']['index']

    # Check k-NN is enabled
    assert settings.get('knn') == 'true', f"k-NN not enabled on index {first_index}"

    # Cleanup
    record.delete()
    db.session.commit()


def test_record_index_has_embedding_mapping(app, db, minimal_record):
    """Test that actual record index has embedding field mapping."""
    # Create a record to ensure index exists
    record = RDMRecord.create(minimal_record)
    db.session.commit()
    record.index()

    # Get index name
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    base_index_name = RDMRecord.index._name
    index_name = f"{prefix}{base_index_name}"

    # Get index mappings
    index_mappings = current_search_client.indices.get_mapping(index=index_name)
    first_index = list(index_mappings.keys())[0]
    properties = index_mappings[first_index]['mappings']['properties']

    # Check aisearch.embedding field exists
    assert 'aisearch' in properties, "aisearch field not in index"
    aisearch_props = properties['aisearch'].get('properties', {})
    assert 'embedding' in aisearch_props, "embedding field not in aisearch"

    # Check it's a knn_vector
    embedding_config = aisearch_props['embedding']
    assert embedding_config.get('type') == 'knn_vector', "embedding is not knn_vector"
    assert embedding_config.get('dimension') == 384, "embedding dimension is not 384"

    # Cleanup
    record.delete()
    db.session.commit()


def test_template_pattern_matches_index(app):
    """Test that template pattern matches RDM record index."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Get template configuration
    template = current_search_client.indices.get_index_template(name=template_name)
    template_data = template['index_templates'][0]['index_template']
    patterns = template_data.get('index_patterns', [])

    # Check pattern includes rdmrecords
    assert any('rdmrecords-records-record-v' in p for p in patterns), \
        "Template pattern does not match rdmrecords index"


def test_template_priority_is_set(app):
    """Test that template has proper priority."""
    prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
    template_name = f"{prefix}rdmrecords-records-record-v7.0.0-knn"

    # Get template configuration
    template = current_search_client.indices.get_index_template(name=template_name)
    template_data = template['index_templates'][0]['index_template']

    # Check priority exists and is reasonable
    priority = template_data.get('priority')
    assert priority is not None, "Template priority not set"
    assert priority >= 0, "Template priority is negative"
