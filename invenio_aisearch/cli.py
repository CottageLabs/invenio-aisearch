# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI commands for AI search management."""

import click
from flask import current_app
from flask.cli import with_appcontext

from .tasks import regenerate_all_embeddings


@click.group()
def aisearch():
    """AI search management commands."""
    pass


@aisearch.command("generate-embeddings")
@click.option(
    "--async",
    "run_async",
    is_flag=True,
    help="Run as background Celery task"
)
@with_appcontext
def generate_embeddings_cmd(run_async):
    """Generate embeddings for all records.

    Example:
        invenio aisearch generate-embeddings
        invenio aisearch generate-embeddings --async
    """
    if run_async:
        click.echo("Starting embedding generation as background task...")
        result = regenerate_all_embeddings.delay()
        click.echo(f"Task ID: {result.id}")
        click.echo("Use 'celery inspect active' to check task status")
    else:
        click.echo("Generating embeddings for all records...")
        click.echo("This may take several minutes...")

        result = regenerate_all_embeddings()

        click.echo("\n" + "=" * 60)
        click.echo("Embedding Generation Complete")
        click.echo("=" * 60)
        click.echo(f"Total records: {result['total_records']}")
        click.echo(f"Embeddings generated: {result['embeddings_generated']}")
        click.echo(f"Errors: {result['errors']}")
        click.echo(f"File size: {result['file_size_mb']} MB")
        click.echo(f"Saved to: {result['file_path']}")
        click.echo("=" * 60)


@aisearch.command("status")
@with_appcontext
def status_cmd():
    """Check AI search service status.

    Example:
        invenio aisearch status
    """
    embeddings_file = current_app.config.get("INVENIO_AISEARCH_EMBEDDINGS_FILE")

    click.echo("=" * 60)
    click.echo("AI Search Service Status")
    click.echo("=" * 60)

    if not embeddings_file:
        click.echo("Status: NOT CONFIGURED")
        click.echo("\nConfiguration missing:")
        click.echo("  Set INVENIO_AISEARCH_EMBEDDINGS_FILE in invenio.cfg")
        click.echo("\nExample:")
        click.echo("  INVENIO_AISEARCH_EMBEDDINGS_FILE = '/path/to/embeddings.json'")
        return

    click.echo(f"Embeddings file: {embeddings_file}")

    try:
        # Get service from extension
        service = current_app.extensions["invenio-aisearch"].search_service

        if service.embeddings:
            click.echo("Status: READY ✓")
            click.echo(f"Embeddings loaded: {len(service.embeddings)}")

            # Show API endpoints
            api_url = current_app.config.get("INVENIO_AISEARCH_API_URL", "https://127.0.0.1:5000/api")
            click.echo("\nAvailable endpoints:")
            click.echo(f"  Search: {api_url}/aisearch/search?q=<query>")
            click.echo(f"  Similar: {api_url}/aisearch/similar/<record_id>")
            click.echo(f"  Status: {api_url}/aisearch/status")

            # Show configuration
            click.echo("\nConfiguration:")
            click.echo(f"  Semantic weight: {current_app.config.get('INVENIO_AISEARCH_SEMANTIC_WEIGHT', 0.7)}")
            click.echo(f"  Metadata weight: {current_app.config.get('INVENIO_AISEARCH_METADATA_WEIGHT', 0.3)}")
            click.echo(f"  Default limit: {current_app.config.get('INVENIO_AISEARCH_DEFAULT_LIMIT', 10)}")
        else:
            click.echo("Status: NO EMBEDDINGS")
            click.echo("\nRun 'invenio aisearch generate-embeddings' to create embeddings")

    except FileNotFoundError:
        click.echo("Status: EMBEDDINGS FILE NOT FOUND")
        click.echo(f"\nFile does not exist: {embeddings_file}")
        click.echo("\nRun 'invenio aisearch generate-embeddings' to create it")
    except Exception as e:
        click.echo(f"Status: ERROR")
        click.echo(f"\nError: {e}")

    click.echo("=" * 60)


@aisearch.command("test-query")
@click.argument("query")
@click.option("--limit", default=5, help="Number of results")
@with_appcontext
def test_query_cmd(query, limit):
    """Test a search query.

    Example:
        invenio aisearch test-query "books with female protagonists"
        invenio aisearch test-query "social injustice" --limit 3
    """
    embeddings_file = current_app.config.get("INVENIO_AISEARCH_EMBEDDINGS_FILE")

    if not embeddings_file:
        click.echo("Error: INVENIO_AISEARCH_EMBEDDINGS_FILE not configured")
        return

    try:
        from flask import g
        from invenio_access.permissions import system_identity

        # Get service from extension
        service = current_app.extensions["invenio-aisearch"].search_service

        # Use system identity for CLI operations
        result_obj = service.search(
            identity=system_identity,
            query=query,
            limit=limit,
        )

        # Convert to dict
        results = result_obj.to_dict()

        click.echo("=" * 60)
        click.echo(f"Query: \"{query}\"")
        click.echo("=" * 60)
        click.echo(f"\nIntent: {results['parsed']['intent']}")
        click.echo(f"Attributes: {results['parsed']['attributes']}")
        click.echo(f"Search terms: {results['parsed']['search_terms']}")
        click.echo(f"\nResults ({results['total']}):")
        click.echo()

        for i, result in enumerate(results['results'], 1):
            click.echo(f"{i}. {result['title']}")
            click.echo(f"   Semantic: {result['semantic_score']:.3f} | "
                      f"Metadata: {result['metadata_score']:.3f} | "
                      f"Hybrid: {result['hybrid_score']:.3f}")
            click.echo()

        click.echo("=" * 60)

    except Exception as e:
        click.echo(f"Error: {e}")
