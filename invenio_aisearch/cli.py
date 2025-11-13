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
from pathlib import Path
from flask import current_app
from flask.cli import with_appcontext
from invenio_search import current_search_client
from invenio_rdm_records.records.api import RDMRecord
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_access.permissions import system_identity


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
@click.argument("chunks_file", required=False)
@click.option("--batch-size", default=100, help="Number of chunks to process per batch")
@click.option("--async", "run_async", is_flag=True, help="Run as background Celery task")
@with_appcontext
def generate_chunk_embeddings_cmd(chunks_file, batch_size, run_async):
    """Generate embeddings for document chunks and index them.

    This command reads chunks from a JSONL file, generates embeddings using
    the AI model, and indexes them into OpenSearch for full-text search.

    If no chunks file is specified, uses the default from configuration.

    Example:
        invenio aisearch generate-chunk-embeddings
        invenio aisearch generate-chunk-embeddings book_chunks.jsonl --batch-size 50 --async
    """
    from pathlib import Path

    # Get configuration for default path
    if chunks_file is None:
        data_dir = current_app.config.get('INVENIO_AISEARCH_DATA_DIR', 'aisearch_data')
        chunks_filename = current_app.config.get('INVENIO_AISEARCH_CHUNKS_FILE', 'document_chunks.jsonl')

        # Build default path
        if Path(data_dir).is_absolute():
            chunks_path = Path(data_dir) / chunks_filename
        else:
            chunks_path = Path(data_dir) / chunks_filename
    else:
        chunks_path = Path(chunks_file)

    if not chunks_path.exists():
        click.echo(f"✗ File not found: {chunks_path}")
        return

    # Count total chunks
    with open(chunks_path, 'r', encoding='utf-8') as f:
        total_chunks = sum(1 for _ in f)

    click.echo("=" * 60)
    click.echo("Generate Document Chunk Embeddings")
    click.echo("=" * 60)
    click.echo(f"Chunks file: {chunks_path}")
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
@click.option("--output", "-o", default=None, help="Output JSONL file path (default: from config)")
@with_appcontext
def chunk_documents_cmd(output):
    """Chunk documents into passages for full-text search.

    Downloads documents from InvenioRDM records and creates searchable chunks
    with metadata. Chunks are written to a JSONL file for later embedding generation.

    Example:
        invenio aisearch chunk-documents
        invenio aisearch chunk-documents --output /path/to/custom_chunks.jsonl
    """
    # Get configuration
    chunk_size = current_app.config.get('INVENIO_AISEARCH_CHUNK_SIZE', 600)
    chunk_overlap = current_app.config.get('INVENIO_AISEARCH_CHUNK_OVERLAP', 150)
    data_dir = current_app.config.get('INVENIO_AISEARCH_DATA_DIR', 'gutenberg_data')
    chunks_file = current_app.config.get('INVENIO_AISEARCH_CHUNKS_FILE', 'book_chunks.jsonl')

    # Determine output path
    if output is None:
        # Build default path: data_dir/chunks_file
        if Path(data_dir).is_absolute():
            output_path = Path(data_dir) / chunks_file
        else:
            # Relative to current working directory (typically instance root)
            output_path = Path(data_dir) / chunks_file
    else:
        output_path = Path(output)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo("=" * 60)
    click.echo("Chunk Documents for Full-Text Search")
    click.echo("=" * 60)
    click.echo(f"Chunk size: {chunk_size} words")
    click.echo(f"Chunk overlap: {chunk_overlap} words")
    click.echo(f"Output file: {output_path}")
    click.echo()

    # Fetch all records using internal service
    click.echo("Fetching records from InvenioRDM (internal service)...")
    records = []
    page = 1
    size = 100

    while True:
        try:
            # Use internal service to search records
            result = current_rdm_records_service.search(
                identity=system_identity,
                params={'size': size, 'page': page}
            )

            hits = list(result.hits)
            if not hits:
                break

            records.extend(hits)
            click.echo(f"  Fetched {len(records)} records so far...")

            # Check if there are more pages
            if len(hits) < size:
                break
            page += 1

        except Exception as e:
            click.echo(f"Error fetching records: {e}")
            break

    click.echo(f"Total records fetched: {len(records)}")
    click.echo()

    # Process each record
    all_chunks = []
    successful = 0
    failed = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        with click.progressbar(records, label='Processing records') as bar:
            for record in bar:
                record_id = record['id']
                title = record.get('metadata', {}).get('title', record_id)

                # Get file entries
                files_entries = record.get('files', {}).get('entries', {})
                txt_files = {k: v for k, v in files_entries.items() if k.endswith('.txt')}

                if not txt_files:
                    failed += 1
                    continue

                filename = list(txt_files.keys())[0]

                try:
                    # Use internal service to read file content
                    file_item = current_rdm_records_service.files.get_file_content(
                        identity=system_identity,
                        id_=record_id,
                        file_key=filename
                    )

                    # Read file content using open_stream context manager
                    with file_item.open_stream('rb') as stream:
                        text = stream.read().decode('utf-8')

                except Exception as e:
                    click.echo(f"\n  Error reading {title}: {e}")
                    failed += 1
                    continue

                # Clean Gutenberg text
                text = _clean_gutenberg_text(text)

                # Chunk text
                chunks = _chunk_text(text, chunk_size, chunk_overlap)

                # Get metadata
                creators = record.get('metadata', {}).get('creators', [])
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


@aisearch.command("explain-similarity")
@click.argument("record_id_1")
@click.argument("record_id_2")
@click.option("--num-passages", default=5, help="Number of top passage pairs to analyze")
@with_appcontext
def explain_similarity_cmd(record_id_1, record_id_2, num_passages):
    """Explain why two books are semantically similar.

    Analyzes passage-level similarity between two books and extracts
    common themes, topics, and keywords from the most similar passages.

    Example:
        invenio aisearch explain-similarity abcd-1234 efgh-5678
        invenio aisearch explain-similarity abcd-1234 efgh-5678 --num-passages 10
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from collections import Counter
    import numpy as np

    click.echo("=" * 60)
    click.echo("Semantic Similarity Analysis")
    click.echo("=" * 60)

    # Get chunks index name
    chunks_index = current_app.config.get('INVENIO_AISEARCH_CHUNKS_INDEX', 'document-chunks-v1')

    # Check if chunks index exists
    if not current_search_client.indices.exists(index=chunks_index):
        click.echo(f"✗ Chunks index '{chunks_index}' does not exist")
        click.echo("Create it with: invenio aisearch create-chunks-index")
        return

    # Check if model is loaded
    ext = current_app.extensions.get("invenio-aisearch")
    if not ext or not ext.model_manager:
        click.echo("✗ AI search extension not initialized")
        return

    try:
        # Fetch metadata for both books
        click.echo(f"\nFetching book metadata...")

        book1_result = current_rdm_records_service.read(
            identity=system_identity,
            id_=record_id_1
        )
        book1 = book1_result.to_dict()
        book1_title = book1.get('metadata', {}).get('title', record_id_1)
        book1_creators = book1.get('metadata', {}).get('creators', [])
        book1_author = book1_creators[0]['person_or_org']['name'] if book1_creators else 'Unknown'

        book2_result = current_rdm_records_service.read(
            identity=system_identity,
            id_=record_id_2
        )
        book2 = book2_result.to_dict()
        book2_title = book2.get('metadata', {}).get('title', record_id_2)
        book2_creators = book2.get('metadata', {}).get('creators', [])
        book2_author = book2_creators[0]['person_or_org']['name'] if book2_creators else 'Unknown'

        click.echo(f"\nBook 1: {book1_title}")
        click.echo(f"  Author: {book1_author}")
        click.echo(f"  ID: {record_id_1}")

        click.echo(f"\nBook 2: {book2_title}")
        click.echo(f"  Author: {book2_author}")
        click.echo(f"  ID: {record_id_2}")

        # Fetch all passages for both books
        click.echo(f"\nFetching passages from chunks index...")

        book1_passages = _fetch_all_passages(record_id_1, chunks_index)
        book2_passages = _fetch_all_passages(record_id_2, chunks_index)

        if not book1_passages:
            click.echo(f"✗ No passages found for book 1")
            return
        if not book2_passages:
            click.echo(f"✗ No passages found for book 2")
            return

        click.echo(f"  Book 1: {len(book1_passages)} passages")
        click.echo(f"  Book 2: {len(book2_passages)} passages")

        # Calculate pairwise similarities
        click.echo(f"\nCalculating passage-level similarities...")

        similar_pairs = []
        for p1 in book1_passages:
            for p2 in book2_passages:
                # Cosine similarity between embeddings
                emb1 = np.array(p1['embedding'])
                emb2 = np.array(p2['embedding'])
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

                similar_pairs.append({
                    'similarity': similarity,
                    'passage1': p1,
                    'passage2': p2
                })

        # Sort by similarity and take top N
        similar_pairs.sort(key=lambda x: x['similarity'], reverse=True)
        top_pairs = similar_pairs[:num_passages]

        click.echo(f"  Found {len(similar_pairs)} passage pairs")
        click.echo(f"  Analyzing top {len(top_pairs)} pairs")

        # Extract themes from top matching passages
        click.echo(f"\n{'=' * 60}")
        click.echo("Theme Analysis")
        click.echo("=" * 60)

        # Combine text from top matching passages
        combined_texts = []
        for pair in top_pairs:
            combined_texts.append(pair['passage1']['text'])
            combined_texts.append(pair['passage2']['text'])

        # Extract key terms using TF-IDF
        click.echo("\nExtracting key themes using TF-IDF...")

        vectorizer = TfidfVectorizer(
            max_features=30,
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=2  # Must appear in at least 2 passages
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(combined_texts)
            feature_names = vectorizer.get_feature_names_out()

            # Get average TF-IDF scores across all passages
            avg_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            top_indices = avg_scores.argsort()[-15:][::-1]

            click.echo("\n🔑 Key Shared Themes/Topics:")
            for idx in top_indices:
                if avg_scores[idx] > 0:
                    click.echo(f"  • {feature_names[idx]} (relevance: {avg_scores[idx]:.3f})")

        except Exception as e:
            click.echo(f"  Note: Could not extract themes (too few passages or low overlap)")

        # Show top matching passage pairs
        click.echo(f"\n{'=' * 60}")
        click.echo("Top Matching Passage Pairs")
        click.echo("=" * 60)

        for i, pair in enumerate(top_pairs[:3], 1):  # Show top 3 pairs in detail
            click.echo(f"\n{i}. Similarity Score: {pair['similarity']:.3f}")
            click.echo(f"\n   From '{book1_title}' (chunk {pair['passage1']['chunk_index'] + 1}/{pair['passage1']['chunk_count']}):")
            passage1_preview = pair['passage1']['text'][:400] + "..." if len(pair['passage1']['text']) > 400 else pair['passage1']['text']
            click.echo(f"   {passage1_preview}")

            click.echo(f"\n   From '{book2_title}' (chunk {pair['passage2']['chunk_index'] + 1}/{pair['passage2']['chunk_count']}):")
            passage2_preview = pair['passage2']['text'][:400] + "..." if len(pair['passage2']['text']) > 400 else pair['passage2']['text']
            click.echo(f"   {passage2_preview}")
            click.echo()

        # Calculate overall book similarity
        click.echo(f"\n{'=' * 60}")
        click.echo("Overall Similarity")
        click.echo("=" * 60)

        # Average of top passage similarities
        avg_top_similarity = np.mean([p['similarity'] for p in top_pairs])
        click.echo(f"\nAverage similarity of top {len(top_pairs)} passage pairs: {avg_top_similarity:.3f}")

        # Distribution of similarities
        all_similarities = [p['similarity'] for p in similar_pairs]
        click.echo(f"Median passage similarity: {np.median(all_similarities):.3f}")
        click.echo(f"Max passage similarity: {np.max(all_similarities):.3f}")
        click.echo(f"Min passage similarity: {np.min(all_similarities):.3f}")

        # Interpretation
        click.echo("\n📊 Interpretation:")
        if avg_top_similarity > 0.8:
            click.echo("  Very high similarity - these books share very similar content and themes")
        elif avg_top_similarity > 0.7:
            click.echo("  High similarity - these books share significant thematic overlap")
        elif avg_top_similarity > 0.6:
            click.echo("  Moderate similarity - these books have some shared themes or topics")
        elif avg_top_similarity > 0.5:
            click.echo("  Low-moderate similarity - these books have limited thematic overlap")
        else:
            click.echo("  Low similarity - these books have minimal thematic connection")

    except Exception as e:
        click.echo(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    click.echo("\n" + "=" * 60)


def _fetch_all_passages(record_id: str, index_name: str):
    """Fetch all passage chunks for a given record."""
    passages = []

    query = {
        "query": {
            "term": {
                "record_id": record_id
            }
        },
        "size": 1000,  # Assume no book has more than 1000 chunks
        "_source": ["chunk_id", "text", "chunk_index", "chunk_count", "word_count", "embedding"]
    }

    try:
        response = current_search_client.search(index=index_name, body=query)

        for hit in response['hits']['hits']:
            source = hit['_source']
            passages.append(source)

        return passages

    except Exception as e:
        click.echo(f"Error fetching passages: {e}")
        return []
