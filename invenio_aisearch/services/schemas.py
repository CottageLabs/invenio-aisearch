# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Marshmallow schemas for AI search service."""

from marshmallow import Schema, fields, validate, ValidationError, validates_schema


class SearchRequestSchema(Schema):
    """Schema for search request parameters."""

    q = fields.Str(required=False, allow_none=True)
    query = fields.Str(required=False, allow_none=True)
    limit = fields.Int(
        required=False,
        allow_none=True,
        validate=validate.Range(min=1, max=100)
    )
    summaries = fields.Bool(required=False, missing=False)
    semantic_weight = fields.Float(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0.0, max=1.0)
    )
    metadata_weight = fields.Float(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0.0, max=1.0)
    )

    @validates_schema
    def validate_query(self, data, **kwargs):
        """Ensure either q or query is provided."""
        if not data.get('q') and not data.get('query'):
            raise ValidationError("Either 'q' or 'query' parameter is required")


class SimilarRequestSchema(Schema):
    """Schema for similar records request parameters."""

    limit = fields.Int(
        required=False,
        missing=10,
        validate=validate.Range(min=1, max=100)
    )


class SearchResponseSchema(Schema):
    """Schema for search response."""

    query = fields.Str(required=True)
    parsed = fields.Dict(required=True)
    results = fields.List(fields.Dict(), required=True)
    total = fields.Int(required=True)


class SimilarResponseSchema(Schema):
    """Schema for similar records response."""

    record_id = fields.Str(required=True)
    similar = fields.List(fields.Dict(), required=True)
    total = fields.Int(required=True)


class StatusResponseSchema(Schema):
    """Schema for status response."""

    status = fields.Str(required=True)
    embeddings_loaded = fields.Bool(required=True)
    embeddings_count = fields.Int(required=True)
    embeddings_file = fields.Str(required=False, allow_none=True)
    message = fields.Str(required=False, allow_none=True)
