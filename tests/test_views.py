# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for UI views."""

import pytest


def test_search_page_renders(client):
    """Test that AI search page renders."""
    response = client.get("/aisearch")

    assert response.status_code == 200
    assert b"AI Search" in response.data or b"ai-search" in response.data


def test_search_page_has_form(client):
    """Test that search page has search form."""
    response = client.get("/aisearch")

    assert response.status_code == 200
    # Check for form elements
    assert b"form" in response.data
    assert b"search" in response.data.lower()


def test_search_page_loads_javascript(client):
    """Test that search page loads JavaScript."""
    response = client.get("/aisearch")

    assert response.status_code == 200
    # Check for script tag or JS references
    assert b"script" in response.data or b".js" in response.data


def test_blueprint_registered(app):
    """Test that blueprint is registered."""
    assert "invenio_aisearch" in app.blueprints
