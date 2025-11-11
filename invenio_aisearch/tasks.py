# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for AI search operations.

Note: With the k-NN approach, embeddings are generated automatically
during record indexing via EmbeddingDumperExt. No separate task needed.

For document chunks, embeddings must be generated separately since chunks
are not part of the standard record indexing flow.
"""

import json
from pathlib import Path
from celery import shared_task
from flask import current_app
from invenio_search import current_search_client


@shared_task(bind=True, max_retries=3)
def generate_chunk_embeddings(self, chunks_file, batch_size=100, start_offset=0):
    """Generate embeddings for document chunks and index them.

    Args:
        chunks_file: Path to JSONL file containing chunks
        batch_size: Number of chunks to process in one batch
        start_offset: Line number to start from (for resuming)

    Returns:
        Dict with statistics about the operation
    """
    current_app.logger.info(f"Starting chunk embedding generation from {chunks_file}")
    current_app.logger.info(f"Batch size: {batch_size}, Start offset: {start_offset}")

    # Get extension and model manager
    ext = current_app.extensions.get("invenio-aisearch")
    if not ext or not ext.model_manager:
        current_app.logger.error("invenio-aisearch extension not initialized")
        raise RuntimeError("AI search extension not available")

    model_manager = ext.model_manager
    index_name = current_app.config.get('INVENIO_AISEARCH_CHUNKS_INDEX', 'document-chunks-v1')

    chunks_path = Path(chunks_file)
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

    # Read chunks from JSONL file
    chunks = []
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < start_offset:
                continue
            if len(chunks) >= batch_size:
                break
            chunks.append(json.loads(line))

    if not chunks:
        current_app.logger.info("No chunks to process")
        return {
            'processed': 0,
            'indexed': 0,
            'errors': 0
        }

    current_app.logger.info(f"Processing {len(chunks)} chunks")

    # Generate embeddings
    texts = [chunk['text'] for chunk in chunks]
    try:
        embeddings = model_manager.encode_batch(texts)
        current_app.logger.info(f"Generated {len(embeddings)} embeddings")
    except Exception as e:
        current_app.logger.error(f"Error generating embeddings: {e}")
        raise

    # Index chunks with embeddings
    bulk_body = []
    indexed = 0
    errors = 0

    for chunk, embedding in zip(chunks, embeddings):
        # Create index action
        bulk_body.append({
            "index": {
                "_index": index_name,
                "_id": chunk['chunk_id']
            }
        })

        # Add chunk data with embedding
        chunk_doc = {
            'chunk_id': chunk['chunk_id'],
            'record_id': chunk['record_id'],
            'title': chunk.get('book_title', chunk.get('title')),
            'creators': chunk.get('author', chunk.get('creators', '')),
            'chunk_index': chunk['chunk_index'],
            'chunk_count': chunk['chunk_count'],
            'text': chunk['text'],
            'char_start': chunk['char_start'],
            'char_end': chunk['char_end'],
            'word_count': chunk['word_count'],
            'embedding': embedding.tolist()
        }
        bulk_body.append(chunk_doc)

    # Bulk index
    try:
        response = current_search_client.bulk(body=bulk_body, refresh=True)

        if response.get('errors'):
            errors = sum(1 for item in response['items'] if 'error' in item.get('index', {}))
            current_app.logger.warning(f"Bulk indexing had {errors} errors")

        indexed = len(chunks) - errors
        current_app.logger.info(f"Indexed {indexed} chunks successfully")

    except Exception as e:
        current_app.logger.error(f"Error indexing chunks: {e}")
        raise

    # If there are more chunks, chain the next batch
    next_offset = start_offset + len(chunks)

    # Check if there are more chunks to process
    with open(chunks_path, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f)

    if next_offset < total_lines:
        current_app.logger.info(f"Chaining next batch starting at offset {next_offset}")
        generate_chunk_embeddings.apply_async(
            args=[chunks_file, batch_size, next_offset],
            countdown=2  # Small delay between batches
        )

    return {
        'processed': len(chunks),
        'indexed': indexed,
        'errors': errors,
        'next_offset': next_offset,
        'total_lines': total_lines,
        'complete': next_offset >= total_lines
    }
