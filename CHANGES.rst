..
    Copyright (C) 2025 Cottage Labs.

    invenio-aisearch is free software; you can redistribute it and/or
    modify it under the terms of the MIT License; see LICENSE file for more
    details.

Changes
=======

Version 0.1.0 (released TBD)

- Initial public release.

Version 0.0.2 (released 2025-01-10)

Major architectural refactoring to use OpenSearch k-NN for semantic search.

Breaking Changes
~~~~~~~~~~~~~~~~

- **Removed embeddings file dependency**: Version 0.0.1 used a separate embeddings file
  that had to be generated and maintained. Version 0.0.2 stores embeddings directly in
  OpenSearch using k-NN vector fields.

- **Index structure changes**: The search index now includes a dedicated ``aisearch.embedding``
  field configured as a ``knn_vector`` with HNSW algorithm support.

- **Removed deprecated parameters**: The ``semantic_weight`` and ``metadata_weight``
  parameters have been removed from the search API. The service now uses pure k-NN
  semantic search instead of hybrid search.

New Features
~~~~~~~~~~~~

- **OpenSearch k-NN Integration**: Embeddings are now stored directly in OpenSearch as
  384-dimensional vectors using the HNSW (Hierarchical Navigable Small World) algorithm
  for efficient nearest-neighbor search.

- **Automatic Embedding Generation**: The ``EmbeddingDumperExt`` dumper extension
  automatically generates and includes embeddings when records are indexed, eliminating
  the need for separate embedding file management.

- **Improved Search Performance**: OpenSearch k-NN provides native vector similarity
  search with optimized performance compared to the previous embeddings file approach.

- **Dedicated AI Search Index**: Introduced a separate ``aisearch`` index for AI-powered
  searches, allowing independent scaling and configuration from the main InvenioRDM index.

Technical Details
~~~~~~~~~~~~~~~~~

**Index Configuration**:

- Vector dimension: 384 (using ``all-MiniLM-L6-v2`` sentence transformer model)
- k-NN method: HNSW with ``cosinesimil`` distance metric
- Engine: nmslib
- HNSW parameters: ``ef_construction=128``, ``m=24``

**New Components**:

- ``services/index.py``: OpenSearch index management for the AI search index
- ``records/dumpers/embedding_dumper.py``: Automatic embedding generation during record dumps
- Enhanced ``AISearchService`` with k-NN query building

**Modified Components**:

- ``AISearchService.search()``: Now uses OpenSearch k-NN queries instead of embeddings file
- ``AISearchResource``: Updated to match new service method signatures
- Index creation: Automatic index setup with k-NN enabled settings

Migration Notes
~~~~~~~~~~~~~~~

When upgrading from 0.0.1 to 0.0.2:

1. **Delete old embeddings file**: The embeddings file is no longer used and can be removed.

2. **Recreate search indices**: The AI search index structure has changed:

   .. code-block:: bash

      # Destroy old indices
      pipenv run invenio index destroy --force --yes-i-know

      # Recreate indices with new k-NN structure
      pipenv run invenio index init

3. **Reindex all records**: Records must be reindexed to generate embeddings:

   .. code-block:: bash

      # Reindex main RDM records (generates embeddings automatically)
      pipenv run invenio index reindex --yes-i-know -t recid

      # Run the queue to process indexing
      pipenv run invenio index run

4. **Update API calls**: If using the API directly, remove any ``semantic_weight`` or
   ``metadata_weight`` parameters from search requests.

Known Issues
~~~~~~~~~~~~

- The ``init_index_patch()`` method in ``ext.py`` is currently disabled (line 30-31)
  as it causes issues with index creation. Manual index setup is required.

- Embeddings are generated using CPU by default. For production deployments with large
  numbers of records, consider GPU-accelerated embedding generation.

Version 0.0.1 (released 2025-01-05)

- Initial development release
- Hybrid search using embeddings file
- Sentence transformer model integration (``all-MiniLM-L6-v2``)
- Basic API endpoints: ``/api/aisearch/search``, ``/api/aisearch/similar``, ``/api/aisearch/status``
- UI integration with search box and results display
