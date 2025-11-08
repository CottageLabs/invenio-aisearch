# Invenio-AIS Search Integration Guide

This guide explains how to integrate the invenio-aisearch module into your InvenioRDM instance.

## Installation

### 1. Install the module

From your InvenioRDM instance directory (e.g., `v13-ai`):

```bash
# Using invenio-cli (recommended)
invenio-cli packages install ../invenio-aisearch

# Or manually with pipenv
pipenv install -e ../invenio-aisearch
```

### 2. Configure the module

Add to your `invenio.cfg`:

```python
# Path to embeddings file
INVENIO_AISEARCH_EMBEDDINGS_FILE = "/path/to/instance/embeddings.json"

# Optional: Adjust search weights
INVENIO_AISEARCH_SEMANTIC_WEIGHT = 0.7  # 70% semantic similarity
INVENIO_AISEARCH_METADATA_WEIGHT = 0.3  # 30% metadata matching

# Optional: API URL for background tasks
INVENIO_AISEARCH_API_URL = "https://127.0.0.1:5000/api"
```

### 3. Generate embeddings

Generate embeddings for all your records:

```bash
# Interactive (see progress)
pipenv run invenio aisearch generate-embeddings

# Or as background task
pipenv run invenio aisearch generate-embeddings --async
```

### 4. Restart your application

```bash
# If using containers
invenio-cli containers restart

# If running locally
# Restart your web and worker processes
```

## Usage

### CLI Commands

**Check status:**
```bash
pipenv run invenio aisearch status
```

**Test a query:**
```bash
pipenv run invenio aisearch test-query "books with female protagonists"
pipenv run invenio aisearch test-query "social injustice" --limit 5
```

**Regenerate embeddings:**
```bash
pipenv run invenio aisearch generate-embeddings
```

### API Endpoints

Once integrated, the following REST API endpoints are available:

#### 1. Search

```bash
# GET request
curl "https://127.0.0.1:5000/api/aisearch/search?q=books+with+female+protagonists&limit=3"

# POST request
curl -X POST https://127.0.0.1:5000/api/aisearch/search \
  -H "Content-Type: application/json" \
  -d '{"q": "books with female protagonists", "limit": 3, "summaries": false}'
```

**Response:**
```json
{
  "query": "books with female protagonists",
  "parsed": {
    "original_query": "books with female protagonists",
    "intent": "search",
    "limit": 3,
    "attributes": ["female_protagonist"],
    "search_terms": ["female", "women", "protagonist"],
    "semantic_query": "books with female protagonists"
  },
  "results": [
    {
      "record_id": "abc123",
      "title": "Little Women",
      "semantic_score": 0.486,
      "metadata_score": 0.250,
      "hybrid_score": 0.415
    },
    ...
  ],
  "total": 3
}
```

#### 2. Find Similar Records

```bash
curl "https://127.0.0.1:5000/api/aisearch/similar/abc123?limit=5"
```

**Response:**
```json
{
  "record_id": "abc123",
  "similar": [
    {
      "record_id": "def456",
      "title": "Sense and Sensibility",
      "similarity": 0.571
    },
    ...
  ],
  "total": 5
}
```

#### 3. Service Status

```bash
curl "https://127.0.0.1:5000/api/aisearch/status"
```

**Response:**
```json
{
  "status": "ready",
  "embeddings_loaded": true,
  "embeddings_count": 92,
  "embeddings_file": "/path/to/embeddings.json"
}
```

### Query Parser Features

The natural language parser understands:

**Limits:**
- "show me 3 books"
- "find 5 novels"
- "get me ten stories"

**Attributes:**
- "female protagonist" / "male protagonist"
- "by women" / "female author"
- "romance" / "love story"
- "adventure" / "quest"
- "tragedy" / "tragic"
- "social injustice" / "inequality"
- "about war" / "warfare"
- "Victorian" / "19th century"

**Intents:**
- "how many books..." (count)
- "list all..." (list)
- "show me..." / "find me..." (search)

## Configuration Reference

All configuration options:

```python
# Required: Path to embeddings file
INVENIO_AISEARCH_EMBEDDINGS_FILE = None

# API URL for record fetching (used by background tasks)
INVENIO_AISEARCH_API_URL = "https://127.0.0.1:5000/api"

# Hybrid search weights (must sum to 1.0)
INVENIO_AISEARCH_SEMANTIC_WEIGHT = 0.7
INVENIO_AISEARCH_METADATA_WEIGHT = 0.3

# Result limits
INVENIO_AISEARCH_DEFAULT_LIMIT = 10
INVENIO_AISEARCH_MAX_LIMIT = 100
```

## Architecture

### Components

1. **Search Service** (`search_service.py`)
   - Combines NL parsing, semantic search, and hybrid scoring
   - Singleton pattern for efficient embedding loading

2. **API Views** (`api_views.py`)
   - REST endpoints for search and similar records
   - JSON request/response handling

3. **Celery Tasks** (`tasks.py`)
   - Background embedding generation
   - Async processing for large datasets

4. **Query Parser** (`query_parser.py`)
   - Natural language to structured query
   - Intent detection and attribute extraction

5. **Model Manager** (`models.py`)
   - HuggingFace model management
   - Lazy loading and caching

### Data Flow

```
User Query
    ↓
Natural Language Parser
    ↓
Query Embedding (sentence-transformers)
    ↓
Cosine Similarity Calculation
    ↓
Hybrid Scoring (semantic + metadata)
    ↓
Ranked Results
```

## Embedding Generation

### Manual Script

From `v13-ai/scripts/gutenberg/`:

```bash
python generate_embeddings.py -u https://127.0.0.1:5000 -o ../../embeddings.json
```

### CLI Command

```bash
pipenv run invenio aisearch generate-embeddings
```

### Celery Task

```python
from invenio_aisearch.tasks import regenerate_all_embeddings

# Async
result = regenerate_all_embeddings.delay()

# Sync
result = regenerate_all_embeddings()
```

## Troubleshooting

### Embeddings not loading

```bash
# Check status
pipenv run invenio aisearch status

# Verify file exists
ls -lh $EMBEDDINGS_FILE_PATH

# Check permissions
# File must be readable by application user
```

### API returns 503 "not configured"

Ensure `INVENIO_AISEARCH_EMBEDDINGS_FILE` is set in `invenio.cfg` and restart the application.

### Poor search results

Adjust hybrid search weights:

```python
# More semantic (understands concepts)
INVENIO_AISEARCH_SEMANTIC_WEIGHT = 0.9
INVENIO_AISEARCH_METADATA_WEIGHT = 0.1

# More metadata (exact matches)
INVENIO_AISEARCH_SEMANTIC_WEIGHT = 0.5
INVENIO_AISEARCH_METADATA_WEIGHT = 0.5
```

### Models not downloading

Check internet connection and disk space (~3.3GB required):

```bash
# Models cached to:
~/.cache/invenio_aisearch/

# Manual model download
python -c "from invenio_aisearch.models import get_model_manager; get_model_manager().preload_models()"
```

## Development

### Running Tests

```bash
cd invenio-aisearch
pipenv install --dev
pipenv run pytest
```

### Code Style

```bash
pipenv run black invenio_aisearch/
pipenv run isort invenio_aisearch/
```

## Performance Notes

- **Embedding generation**: ~1-2 seconds per record
- **Search latency**: ~100-300ms for 100 records (after model loading)
- **Model loading**: ~5-10 seconds on first request (then cached)
- **Memory usage**: ~500MB for models + embeddings

## Support

- GitHub Issues: https://github.com/CottageLabs/invenio-aisearch/issues
- Documentation: https://github.com/CottageLabs/invenio-aisearch

## License

MIT License - Copyright (C) 2025 Cottage Labs
