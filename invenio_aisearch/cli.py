# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI commands for AI search management."""

import click
import json
import re
import requests
import urllib3
from pathlib import Path
from flask import current_app
from flask.cli import with_appcontext
from invenio_search import current_search_client
from invenio_rdm_records.records.api import RDMRecord

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


@aisearch.command("create-chunks-index")
@with_appcontext
def create_chunks_index_cmd():
    """Create OpenSearch index for document chunks.

    Example:
        invenio aisearch create-chunks-index
    """
    import json

    index_name = current_app.config.get('INVENIO_AISEARCH_CHUNKS_INDEX', 'document-chunks-v1')

    click.echo("=" * 60)
    click.echo("Creating Document Chunks Index")
    click.echo("=" * 60)
    click.echo(f"Index: {index_name}")
    click.echo()

    # Index mapping with KNN vector field
    index_mapping = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 512,
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        },
        "mappings": {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "record_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "creators": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "chunk_index": {"type": "integer"},
                "chunk_count": {"type": "integer"},
                "text": {"type": "text", "analyzer": "english"},
                "char_start": {"type": "integer"},
                "char_end": {"type": "integer"},
                "word_count": {"type": "integer"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 384,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }
                    }
                }
            }
        }
    }

    # Check if index exists
    try:
        if current_search_client.indices.exists(index=index_name):
            click.echo(f"⚠️  Index '{index_name}' already exists")
            if not click.confirm("Delete and recreate?"):
                click.echo("Aborted.")
                return

            click.echo("Deleting existing index...")
            current_search_client.indices.delete(index=index_name)
            click.echo("✓ Index deleted")

        # Create index
        click.echo("Creating index with KNN vectors (384 dimensions)...")
        current_search_client.indices.create(
            index=index_name,
            body=index_mapping
        )

        click.echo("✓ Index created successfully")
        click.echo()
        click.echo("Index Configuration:")
        click.echo("  - KNN vectors: 384 dimensions (cosine similarity)")
        click.echo("  - HNSW algorithm with nmslib engine")
        click.echo("  - Text analysis: English analyzer")
        click.echo("  - Fields: chunk_id, record_id, title, creators, text, embedding")

    except Exception as e:
        click.echo(f"✗ Failed to create index")
        click.echo(f"Error: {e}")
        import traceback
        traceback.print_exc()

    click.echo("=" * 60)


@aisearch.command("chunks-status")
@with_appcontext
def chunks_status_cmd():
    """Check status of document chunks index.

    Example:
        invenio aisearch chunks-status
    """
    index_name = current_app.config.get('INVENIO_AISEARCH_CHUNKS_INDEX', 'document-chunks-v1')

    click.echo("=" * 60)
    click.echo("Document Chunks Status")
    click.echo("=" * 60)
    click.echo(f"Index: {index_name}")
    click.echo()

    try:
        # Check if index exists
        if not current_search_client.indices.exists(index=index_name):
            click.echo("Status: INDEX NOT FOUND ✗")
            click.echo()
            click.echo("Create the index with:")
            click.echo("  invenio aisearch create-chunks-index")
            click.echo("=" * 60)
            return

        # Get index stats
        stats = current_search_client.indices.stats(index=index_name)
        index_stats = stats['indices'][index_name]['total']

        doc_count = index_stats['docs']['count']
        store_size = index_stats['store']['size_in_bytes'] / (1024 * 1024)  # MB

        click.echo(f"Status: INDEX EXISTS ✓")
        click.echo(f"Documents indexed: {doc_count:,}")
        click.echo(f"Index size: {store_size:.2f} MB")

        # Count documents with embeddings
        count_query = {
            "query": {
                "exists": {
                    "field": "embedding"
                }
            }
        }
        count_response = current_search_client.count(index=index_name, body=count_query)
        chunks_with_embeddings = count_response['count']

        click.echo(f"Chunks with embeddings: {chunks_with_embeddings:,}")

        if chunks_with_embeddings < doc_count:
            click.echo(f"\nℹ️  {doc_count - chunks_with_embeddings:,} chunks missing embeddings")

        # Get sample chunk
        if doc_count > 0:
            sample = current_search_client.search(
                index=index_name,
                body={"size": 1, "_source": ["chunk_id", "title", "creators", "word_count"]}
            )

            if sample['hits']['hits']:
                hit = sample['hits']['hits'][0]['_source']
                click.echo("\nSample chunk:")
                click.echo(f"  ID: {hit.get('chunk_id')}")
                click.echo(f"  Title: {hit.get('title')}")
                click.echo(f"  Creators: {hit.get('creators')}")
                click.echo(f"  Words: {hit.get('word_count')}")

        # Configuration
        click.echo("\nConfiguration:")
        click.echo(f"  Chunk size: {current_app.config.get('INVENIO_AISEARCH_CHUNK_SIZE', 600)} words")
        click.echo(f"  Chunk overlap: {current_app.config.get('INVENIO_AISEARCH_CHUNK_OVERLAP', 150)} words")
        click.echo(f"  Chunks enabled: {current_app.config.get('INVENIO_AISEARCH_CHUNKS_ENABLED', False)}")

    except Exception as e:
        click.echo(f"Error: {e}")
        import traceback
        traceback.print_exc()

    click.echo("=" * 60)


@aisearch.command("generate-chunk-embeddings")
@click.argument("chunks_file")
@click.option("--batch-size", default=100, help="Number of chunks to process per batch")
@click.option("--async", "run_async", is_flag=True, help="Run as background Celery task")
@with_appcontext
def generate_chunk_embeddings_cmd(chunks_file, batch_size, run_async):
    """Generate embeddings for document chunks and index them.

    This command reads chunks from a JSONL file, generates embeddings using
    the AI model, and indexes them into OpenSearch for full-text search.

    Example:
        invenio aisearch generate-chunk-embeddings book_chunks.jsonl
        invenio aisearch generate-chunk-embeddings book_chunks.jsonl --batch-size 50 --async
    """
    from pathlib import Path

    chunks_path = Path(chunks_file)
    if not chunks_path.exists():
        click.echo(f"✗ File not found: {chunks_file}")
        return

    # Count total chunks
    with open(chunks_path, 'r', encoding='utf-8') as f:
        total_chunks = sum(1 for _ in f)

    click.echo("=" * 60)
    click.echo("Generate Document Chunk Embeddings")
    click.echo("=" * 60)
    click.echo(f"Chunks file: {chunks_file}")
    click.echo(f"Total chunks: {total_chunks:,}")
    click.echo(f"Batch size: {batch_size}")
    click.echo(f"Mode: {'Async (Celery)' if run_async else 'Synchronous'}")
    click.echo()

    # Check if index exists
    index_name = current_app.config.get('INVENIO_AISEARCH_CHUNKS_INDEX', 'document-chunks-v1')
    if not current_search_client.indices.exists(index=index_name):
        click.echo(f"✗ Index '{index_name}' does not exist")
        click.echo("Create it with: invenio aisearch create-chunks-index")
        return

    # Check model is loaded
    ext = current_app.extensions.get("invenio-aisearch")
    if not ext or not ext.model_manager:
        click.echo("✗ AI search extension not initialized")
        return

    click.echo(f"Model: {ext.model_manager.model_name}")
    click.echo(f"Embedding dimension: {ext.model_manager.embedding_dim}")
    click.echo()

    estimated_batches = (total_chunks + batch_size - 1) // batch_size
    click.echo(f"This will process {estimated_batches} batches")
    click.echo()

    if not click.confirm("Continue?"):
        click.echo("Cancelled.")
        return

    if run_async:
        # Queue task with Celery
        from invenio_aisearch.tasks import generate_chunk_embeddings

        click.echo("Queuing Celery task...")
        task = generate_chunk_embeddings.apply_async(
            args=[str(chunks_path.absolute()), batch_size, 0]
        )

        click.echo(f"✓ Task queued: {task.id}")
        click.echo()
        click.echo("The task will process batches automatically.")
        click.echo("Check progress with:")
        click.echo("  invenio aisearch chunks-status")
        click.echo()
        click.echo("Monitor Celery logs for detailed progress.")

    else:
        # Run synchronously
        from invenio_aisearch.tasks import generate_chunk_embeddings

        click.echo("Processing chunks (this may take a while)...")
        click.echo()

        offset = 0
        total_processed = 0
        total_indexed = 0
        total_errors = 0

        with click.progressbar(length=total_chunks, label='Generating embeddings') as bar:
            while offset < total_chunks:
                result = generate_chunk_embeddings(
                    str(chunks_path.absolute()),
                    batch_size,
                    offset
                )

                total_processed += result['processed']
                total_indexed += result['indexed']
                total_errors += result['errors']

                bar.update(result['processed'])

                if result['complete']:
                    break

                offset = result['next_offset']

        click.echo()
        click.echo("=" * 60)
        click.echo("Summary:")
        click.echo(f"  Processed: {total_processed:,}")
        click.echo(f"  Indexed: {total_indexed:,}")
        click.echo(f"  Errors: {total_errors}")
        click.echo("=" * 60)


@aisearch.command("chunk-documents")
@click.option("--output", "-o", default="book_chunks.jsonl", help="Output JSONL file")
@click.option("--base-url", default=None, help="InvenioRDM base URL (default: from app config)")
@with_appcontext
def chunk_documents_cmd(output, base_url):
    """Chunk documents into passages for full-text search.

    Downloads documents from InvenioRDM records and creates searchable chunks
    with metadata. Chunks are written to a JSONL file for later embedding generation.

    Example:
        invenio aisearch chunk-documents
        invenio aisearch chunk-documents --output my_chunks.jsonl
    """
    # Get configuration
    chunk_size = current_app.config.get('INVENIO_AISEARCH_CHUNK_SIZE', 600)
    chunk_overlap = current_app.config.get('INVENIO_AISEARCH_CHUNK_OVERLAP', 150)

    if base_url is None:
        base_url = current_app.config.get('SITE_UI_URL', 'https://127.0.0.1:5000')

    click.echo("=" * 60)
    click.echo("Chunk Documents for Full-Text Search")
    click.echo("=" * 60)
    click.echo(f"Base URL: {base_url}")
    click.echo(f"Chunk size: {chunk_size} words")
    click.echo(f"Chunk overlap: {chunk_overlap} words")
    click.echo(f"Output file: {output}")
    click.echo()

    # Fetch all records
    click.echo("Fetching records from InvenioRDM...")
    api_url = f"{base_url.rstrip('/')}/api"
    records = []
    url = f"{api_url}/records?size=100"

    while url:
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            data = response.json()
            records.extend(data['hits']['hits'])
            url = data['links'].get('next')
            click.echo(f"  Fetched {len(records)} records so far...")
        except Exception as e:
            click.echo(f"Error fetching records: {e}")
            break

    click.echo(f"Total records fetched: {len(records)}")
    click.echo()

    # Process each record
    output_path = Path(output)
    all_chunks = []
    successful = 0
    failed = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        with click.progressbar(records, label='Processing records') as bar:
            for record in bar:
                record_id = record['id']
                title = record['metadata'].get('title', record_id)

                # Download text file
                files = record.get('files', {}).get('entries', {})
                txt_files = {k: v for k, v in files.items() if k.endswith('.txt')}

                if not txt_files:
                    failed += 1
                    continue

                filename = list(txt_files.keys())[0]
                file_url = f"{api_url}/records/{record_id}/files/{filename}/content"

                try:
                    response = requests.get(file_url, verify=False)
                    response.raise_for_status()
                    text = response.text
                except Exception as e:
                    click.echo(f"\n  Error downloading {title}: {e}")
                    failed += 1
                    continue

                # Clean Gutenberg text
                text = _clean_gutenberg_text(text)

                # Chunk text
                chunks = _chunk_text(text, chunk_size, chunk_overlap)

                # Get metadata
                creators = record['metadata'].get('creators', [])
                author = creators[0]['person_or_org']['name'] if creators else 'Unknown Author'

                # Create chunk documents
                for i, (chunk_text, start_char, end_char) in enumerate(chunks):
                    chunk_doc = {
                        'chunk_id': f"{record_id}_{i}",
                        'record_id': record_id,
                        'book_title': title,
                        'author': author,
                        'chunk_index': i,
                        'chunk_count': len(chunks),
                        'text': chunk_text,
                        'char_start': start_char,
                        'char_end': end_char,
                        'word_count': len(chunk_text.split()),
                    }
                    f.write(json.dumps(chunk_doc) + '\n')
                    all_chunks.append(chunk_doc)

                successful += 1

    # Summary
    click.echo()
    click.echo("=" * 60)
    click.echo("Chunking Summary:")
    click.echo(f"  Books processed: {successful}/{len(records)}")
    click.echo(f"  Total chunks: {len(all_chunks):,}")
    click.echo(f"  Failed: {failed}")
    click.echo(f"  Output: {output_path}")

    if all_chunks:
        avg_chunk_size = sum(c['word_count'] for c in all_chunks) / len(all_chunks)
        click.echo()
        click.echo("Chunk Statistics:")
        click.echo(f"  Average chunk size: {avg_chunk_size:.0f} words")
        click.echo(f"  Chunk size range: {min(c['word_count'] for c in all_chunks)}-{max(c['word_count'] for c in all_chunks)} words")

    click.echo("=" * 60)


def _clean_gutenberg_text(text: str) -> str:
    """Remove Gutenberg headers/footers and clean text."""
    # Remove Gutenberg header
    start_patterns = [
        r'\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .+ \*\*\*',
    ]
    for pattern in start_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[match.end():]
            break

    # Remove Gutenberg footer
    end_patterns = [
        r'\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .+ \*\*\*',
    ]
    for pattern in end_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[:match.start()]
            break

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    return text


def _chunk_text(text: str, chunk_size: int, overlap: int):
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    step_size = chunk_size - overlap

    for i in range(0, len(words), step_size):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) < 100:  # Skip very small chunks at the end
            break

        chunk_text = ' '.join(chunk_words)
        start_char = len(' '.join(words[:i]))
        end_char = start_char + len(chunk_text)

        chunks.append((chunk_text, start_char, end_char))

    return chunks
