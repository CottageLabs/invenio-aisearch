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
from invenio_search import current_search_client
from invenio_rdm_records.records.api import RDMRecord


@click.group()
def aisearch():
    """AI search management commands."""
    pass


@aisearch.command("status")
@with_appcontext
def status_cmd():
    """Check AI search service status.

    Example:
        invenio aisearch status
    """
    click.echo("=" * 60)
    click.echo("AI Search Service Status (k-NN)")
    click.echo("=" * 60)

    try:
        # Get OpenSearch info
        info = current_search_client.info()
        opensearch_version = info.get('version', {}).get('number', 'unknown')

        click.echo(f"OpenSearch version: {opensearch_version}")

        # Check k-NN plugin
        plugins_response = current_search_client.cat.plugins(format='json')
        knn_plugin = any(p.get('component') == 'opensearch-knn' for p in plugins_response)

        if knn_plugin:
            click.echo("k-NN plugin: INSTALLED ✓")
        else:
            click.echo("k-NN plugin: NOT FOUND ✗")
            click.echo("\nWarning: k-NN plugin required for AI search")
            return

        # Get index info
        prefix = current_app.config.get('SEARCH_INDEX_PREFIX', '')
        base_index_name = RDMRecord.index._name
        index_name = f"{prefix}{base_index_name}"

        # Check if index exists and has k-NN enabled
        try:
            index_settings = current_search_client.indices.get_settings(index=index_name)
            first_index = list(index_settings.keys())[0]
            knn_enabled = index_settings[first_index]['settings']['index'].get('knn') == 'true'

            click.echo(f"Index: {first_index}")
            click.echo(f"k-NN enabled: {'YES ✓' if knn_enabled else 'NO ✗'}")

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

            # Total records
            total_response = current_search_client.count(index=index_name)
            total_records = total_response['count']

            click.echo(f"Records indexed: {total_records}")
            click.echo(f"Records with embeddings: {records_with_embeddings}")

            if records_with_embeddings < total_records:
                click.echo(f"\nℹ️  {total_records - records_with_embeddings} records missing embeddings")
                click.echo("   Run: invenio index reindex --yes-i-know -t recid")
                click.echo("        invenio index run")

        except Exception as e:
            click.echo(f"Index error: {e}")

        # Show model info
        ext = current_app.extensions.get("invenio-aisearch")
        if ext and ext.model_manager:
            click.echo(f"Embedding model: {ext.model_manager.model_name}")
            click.echo(f"Embedding dimension: {ext.model_manager.embedding_dim}")
            click.echo("Status: READY ✓")
        else:
            click.echo("Status: MODEL NOT LOADED ✗")

        # Show API endpoints
        click.echo("\nAvailable endpoints:")
        click.echo("  Search: /api/aisearch/search?q=<query>")
        click.echo("  Similar: /api/aisearch/similar/<record_id>")
        click.echo("  Status: /api/aisearch/status")

        # Show configuration
        click.echo("\nConfiguration:")
        click.echo(f"  Search index prefix: {prefix}")
        click.echo(f"  Default limit: {current_app.config.get('INVENIO_AISEARCH_DEFAULT_LIMIT', 10)}")
        click.echo(f"  Max limit: {current_app.config.get('INVENIO_AISEARCH_MAX_LIMIT', 100)}")

    except Exception as e:
        click.echo(f"Status: ERROR ✗")
        click.echo(f"\nError: {e}")

    click.echo("=" * 60)


@aisearch.command("test-query")
@click.argument("query")
@click.option("--limit", default=5, help="Number of results")
@with_appcontext
def test_query_cmd(query, limit):
    """Test a search query using k-NN semantic search.

    Example:
        invenio aisearch test-query "books with female protagonists"
        invenio aisearch test-query "social injustice" --limit 3
    """
    try:
        from invenio_access.permissions import system_identity

        # Get service from extension
        ext = current_app.extensions.get("invenio-aisearch")
        if not ext:
            click.echo("Error: invenio-aisearch extension not initialized")
            return

        service = ext.search_service

        # Use system identity for CLI operations
        result_obj = service.search(
            identity=system_identity,
            query=query,
            limit=limit,
            include_summaries=False,
        )

        # Convert to dict
        results = result_obj.to_dict()

        click.echo("=" * 60)
        click.echo(f"Query: \"{query}\"")
        click.echo("=" * 60)

        if results.get('parsed'):
            if results['parsed'].get('intent'):
                click.echo(f"\nIntent: {results['parsed']['intent']}")
            if results['parsed'].get('attributes'):
                click.echo(f"Attributes: {results['parsed']['attributes']}")
            if results['parsed'].get('search_terms'):
                click.echo(f"Search terms: {results['parsed']['search_terms']}")

        click.echo(f"\nResults ({results['total']}):")
        click.echo()

        for i, result in enumerate(results['results'], 1):
            click.echo(f"{i}. {result['title']}")
            click.echo(f"   ID: {result['record_id']}")
            click.echo(f"   Similarity: {result['similarity_score']:.3f}")
            if result.get('creators'):
                click.echo(f"   Creators: {', '.join(result['creators'][:3])}")
            click.echo()

        click.echo("=" * 60)

    except Exception as e:
        click.echo(f"Error: {e}")
        import traceback
        traceback.print_exc()


@aisearch.command("reindex")
@click.option(
    "--async",
    "run_async",
    is_flag=True,
    help="Run as background task (requires Celery)"
)
@with_appcontext
def reindex_cmd(run_async):
    """Reindex all records with embeddings.

    This is a convenience wrapper around Invenio's built-in reindex commands.

    Example:
        invenio aisearch reindex
        invenio aisearch reindex --async
    """
    import subprocess

    click.echo("=" * 60)
    click.echo("Reindexing Records with Embeddings")
    click.echo("=" * 60)
    click.echo()
    click.echo("This will:")
    click.echo("1. Queue all records for reindexing")
    click.echo("2. Generate embeddings during indexing")
    click.echo("3. Index records with embeddings into OpenSearch")
    click.echo()

    if not click.confirm("Continue?"):
        click.echo("Cancelled.")
        return

    try:
        # Run reindex command
        click.echo("\nQueueing records for reindex...")
        result = subprocess.run(
            ["invenio", "index", "reindex", "--yes-i-know", "-t", "recid"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            click.echo(f"Error: {result.stderr}")
            return

        click.echo(result.stdout)

        if not run_async:
            click.echo("\nProcessing reindex queue...")
            result = subprocess.run(
                ["invenio", "index", "run"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                click.echo(f"Error: {result.stderr}")
                return

            click.echo(result.stdout)
            click.echo("\n✓ Reindexing complete!")
        else:
            click.echo("\n✓ Records queued for reindexing")
            click.echo("Celery workers will process the queue in the background.")
            click.echo("Run 'invenio aisearch status' to check progress.")

    except Exception as e:
        click.echo(f"Error: {e}")

    click.echo("=" * 60)
