# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for AI search operations."""

import json
import os
from celery import shared_task
from flask import current_app

from .models import get_model_manager


@shared_task(ignore_result=True)
def generate_embedding_for_record(record_id, record_data):
    """Generate embedding for a single record.

    Args:
        record_id: InvenioRDM record ID
        record_data: Record metadata dict with title, description, etc.

    Returns:
        dict: Embedding data
    """
    try:
        # Extract text from record
        text_parts = []

        # Title
        if 'title' in record_data:
            text_parts.append(record_data['title'])

        # Description
        if 'description' in record_data:
            text_parts.append(record_data['description'])

        # Subjects
        if 'subjects' in record_data:
            subjects = [s.get('subject', '') for s in record_data['subjects']]
            text_parts.append(' '.join(subjects))

        # Additional descriptions
        if 'additional_descriptions' in record_data:
            for desc in record_data['additional_descriptions']:
                if 'description' in desc:
                    text_parts.append(desc['description'])

        text = ' '.join(text_parts)

        if not text or len(text.strip()) < 10:
            current_app.logger.warning(
                f"Record {record_id} has insufficient text for embedding"
            )
            return None

        # Generate embedding
        model_manager = get_model_manager()
        embedding = model_manager.generate_embedding(text)

        return {
            'record_id': record_id,
            'embedding': embedding.tolist(),
            'title': record_data.get('title', 'Unknown'),
            'text_length': len(text),
        }

    except Exception as e:
        current_app.logger.error(
            f"Error generating embedding for record {record_id}: {e}",
            exc_info=True
        )
        return None


@shared_task(ignore_result=True)
def generate_embeddings_batch(records):
    """Generate embeddings for a batch of records.

    Args:
        records: List of (record_id, record_data) tuples

    Returns:
        int: Number of embeddings generated
    """
    count = 0

    for record_id, record_data in records:
        result = generate_embedding_for_record(record_id, record_data)
        if result:
            count += 1

    current_app.logger.info(f"Generated {count} embeddings from {len(records)} records")
    return count


@shared_task(ignore_result=True)
def regenerate_all_embeddings():
    """Regenerate embeddings for all records in InvenioRDM.

    This task:
    1. Fetches all published records from InvenioRDM
    2. Generates embeddings for each
    3. Saves to configured embeddings file

    Returns:
        dict: Statistics about the operation
    """
    try:
        import requests
        from urllib3 import disable_warnings
        from urllib3.exceptions import InsecureRequestWarning

        disable_warnings(InsecureRequestWarning)

        # Get configuration
        api_url = current_app.config.get('INVENIO_AISEARCH_API_URL', 'https://127.0.0.1:5000/api')
        embeddings_file = current_app.config.get('INVENIO_AISEARCH_EMBEDDINGS_FILE')

        if not embeddings_file:
            raise ValueError("INVENIO_AISEARCH_EMBEDDINGS_FILE not configured")

        current_app.logger.info("Starting embedding regeneration for all records")

        # Fetch all records
        all_records = []
        url = f"{api_url}/records?size=100"

        while url:
            response = requests.get(url, verify=False)
            response.raise_for_status()

            data = response.json()
            all_records.extend(data['hits']['hits'])

            # Check for next page
            url = data['links'].get('next')

        current_app.logger.info(f"Found {len(all_records)} records to process")

        # Generate embeddings
        model_manager = get_model_manager()
        embeddings = {}
        success_count = 0
        error_count = 0

        for record in all_records:
            record_id = record['id']
            metadata = record.get('metadata', {})

            try:
                # Extract text
                text_parts = []

                if 'title' in metadata:
                    text_parts.append(metadata['title'])

                if 'description' in metadata:
                    text_parts.append(metadata['description'])

                if 'subjects' in metadata:
                    subjects = [s.get('subject', '') for s in metadata['subjects']]
                    text_parts.append(' '.join(subjects))

                if 'additional_descriptions' in metadata:
                    for desc in metadata['additional_descriptions']:
                        if 'description' in desc:
                            text_parts.append(desc['description'])

                text = ' '.join(text_parts)

                if not text or len(text.strip()) < 10:
                    current_app.logger.warning(f"Record {record_id}: insufficient text")
                    error_count += 1
                    continue

                # Generate embedding
                embedding = model_manager.generate_embedding(text)

                embeddings[record_id] = {
                    'embedding': embedding.tolist(),
                    'title': metadata.get('title', 'Unknown'),
                    'text_length': len(text),
                }

                success_count += 1

            except Exception as e:
                current_app.logger.error(
                    f"Error processing record {record_id}: {e}",
                    exc_info=True
                )
                error_count += 1

        # Save embeddings
        os.makedirs(os.path.dirname(embeddings_file), exist_ok=True)

        with open(embeddings_file, 'w') as f:
            json.dump(embeddings, f, indent=2)

        file_size = os.path.getsize(embeddings_file) / (1024 * 1024)  # MB

        result = {
            'total_records': len(all_records),
            'embeddings_generated': success_count,
            'errors': error_count,
            'file_size_mb': round(file_size, 2),
            'file_path': embeddings_file,
        }

        current_app.logger.info(
            f"Embedding regeneration complete: {success_count} generated, "
            f"{error_count} errors"
        )

        return result

    except Exception as e:
        current_app.logger.error(f"Embedding regeneration failed: {e}", exc_info=True)
        raise
