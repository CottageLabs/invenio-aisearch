# AI Search Architecture for InvenioRDM

## Overview

This module adds AI-powered natural language search capabilities to InvenioRDM, enabling queries like "get me 3 books with female protagonists" and providing AI-generated summaries of results.

## Core Features

1. **Natural Language Query Parsing** - Convert conversational queries into structured searches
2. **Semantic Search** - Find books by meaning, not just keywords
3. **AI-Generated Summaries** - Provide context-aware summaries of search results
4. **Full-Text Search** - Search within book content, not just metadata

## Architecture Components

### 1. Backend Services (Python)

#### A. Query Parser Service (`services/query_parser.py`)
**Purpose**: Parse natural language queries into structured search parameters

**Models**:
- **Intent Classification**: `facebook/bart-large-mnli` (zero-shot classification)
  - Classify query intent: filter by attributes, semantic search, count request, etc.
- **Entity Extraction**: `dslim/bert-base-NER` (Named Entity Recognition)
  - Extract: author names, genres, themes, character types, etc.

**Input**: "get me 3 books with female protagonists"
**Output**:
```python
{
    "intent": "filtered_search",
    "limit": 3,
    "filters": {
        "protagonist_gender": "female"
    },
    "query_type": "semantic"  # vs "keyword"
}
```

#### B. Semantic Search Service (`services/semantic_search.py`)
**Purpose**: Generate and search embeddings for semantic similarity

**Models**:
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim embeddings)
  - Fast, lightweight, good quality
  - Alternative: `sentence-transformers/all-mpnet-base-v2` (768-dim, slower, better)

**Storage**: OpenSearch dense vector field
```json
{
  "book_embedding": {
    "type": "dense_vector",
    "dims": 384
  }
}
```

**Operations**:
- Index full book text as embeddings (background job)
- Convert query to embedding
- K-NN search in OpenSearch

#### C. Summary Generation Service (`services/summarizer.py`)
**Purpose**: Generate AI summaries of search results

**Models**:
- **Summarization**: `facebook/bart-large-cnn` (for longer summaries)
  - Alternative: `google/pegasus-xsum` (for shorter summaries)

**Input**: Book text + search context
**Output**: 2-3 sentence summary relevant to the query

#### D. Content Extractor Service (`services/text_extractor.py`)
**Purpose**: Extract and index full text from uploaded files

**Operations**:
- Extract text from .txt files
- Clean and tokenize content
- Store in OpenSearch for full-text search
- Generate embeddings for semantic search

### 2. API Endpoints (`views.py`)

```python
# Search endpoint
POST /api/aisearch/query
{
    "query": "books with female protagonists",
    "limit": 10,
    "include_summaries": true
}

# Response
{
    "results": [
        {
            "record_id": "...",
            "title": "Pride and Prejudice",
            "relevance_score": 0.95,
            "summary": "...",
            "metadata": {...}
        }
    ],
    "total": 15,
    "query_interpretation": {
        "intent": "filtered_search",
        "filters_applied": ["protagonist_gender: female"]
    }
}

# Embedding generation endpoint (admin)
POST /api/aisearch/admin/generate-embeddings
{
    "record_ids": ["id1", "id2"] # or "all"
}

# Model info endpoint
GET /api/aisearch/models
{
    "query_parser": "facebook/bart-large-mnli",
    "embeddings": "sentence-transformers/all-MiniLM-L6-v2",
    "summarizer": "facebook/bart-large-cnn",
    "status": "loaded"
}
```

### 3. Frontend Components

#### A. Search Interface (`templates/aisearch/search.html`)
**Components**:
- Natural language search input (conversational)
- Toggle between AI search and standard search
- Query suggestions/examples
- Results with AI summaries
- Facets/filters (standard InvenioRDM)

#### B. Search Results Display
**Features**:
- AI-generated summary for each result
- Relevance score indicator
- Highlighted query terms
- "Why this result?" explanation
- Link to full record

#### C. Admin Interface (`templates/aisearch/admin.html`)
**Features**:
- Trigger embedding generation
- View indexing status
- Model management
- Query analytics

### 4. Background Jobs (`tasks.py`)

```python
# Celery tasks
@celery.task
def generate_embeddings(record_id):
    """Generate embeddings for a record's full text."""

@celery.task
def index_full_text(record_id):
    """Extract and index full text from record files."""

@celery.task
def batch_process_records(record_ids):
    """Process multiple records in batch."""
```

### 5. Configuration (`config.py`)

```python
# Model configuration
AISEARCH_QUERY_PARSER_MODEL = "facebook/bart-large-mnli"
AISEARCH_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
AISEARCH_SUMMARIZER_MODEL = "facebook/bart-large-cnn"

# Model cache directory
AISEARCH_MODEL_CACHE_DIR = "/path/to/models"

# Search configuration
AISEARCH_MAX_RESULTS = 100
AISEARCH_DEFAULT_LIMIT = 10
AISEARCH_EMBEDDING_DIMS = 384

# OpenSearch configuration
AISEARCH_EMBEDDING_FIELD = "ai_embedding"
AISEARCH_FULLTEXT_FIELD = "full_text"

# Feature flags
AISEARCH_ENABLE_SEMANTIC_SEARCH = True
AISEARCH_ENABLE_SUMMARIES = True
AISEARCH_ENABLE_QUERY_PARSING = True
```

## OpenSearch Index Mapping

```json
{
  "mappings": {
    "properties": {
      "ai_embedding": {
        "type": "dense_vector",
        "dims": 384,
        "index": true,
        "similarity": "cosine"
      },
      "full_text": {
        "type": "text",
        "analyzer": "english"
      },
      "full_text_chunks": {
        "type": "nested",
        "properties": {
          "text": {"type": "text"},
          "embedding": {
            "type": "dense_vector",
            "dims": 384
          },
          "position": {"type": "integer"}
        }
      }
    }
  }
}
```

## Workflow

### Indexing Workflow
```
1. New record created in InvenioRDM
   ↓
2. Hook: Post-create signal
   ↓
3. Background job triggered
   ↓
4. Extract full text from attached file
   ↓
5. Generate embedding using sentence-transformers
   ↓
6. Store embedding in OpenSearch
   ↓
7. Index ready for AI search
```

### Search Workflow
```
1. User enters: "books with female protagonists"
   ↓
2. Query Parser:
   - Intent: filtered_search
   - Extract: protagonist_gender=female
   - Limit: 3 (if specified)
   ↓
3. Semantic Search (if enabled):
   - Convert query to embedding
   - K-NN search in OpenSearch
   ↓
4. Apply filters:
   - Combine semantic results with filters
   - Rank by relevance
   ↓
5. Generate summaries:
   - For top N results
   - Context-aware based on query
   ↓
6. Return results with summaries
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [x] Set up module structure
- [ ] Configure HuggingFace models
- [ ] Implement text extractor
- [ ] Create OpenSearch mapping for embeddings
- [ ] Build embedding generation service

### Phase 2: Semantic Search (Week 2)
- [ ] Generate embeddings for all 89 books
- [ ] Implement K-NN search endpoint
- [ ] Test semantic search accuracy
- [ ] Optimize embedding generation

### Phase 3: Query Parsing (Week 2-3)
- [ ] Implement NLU query parser
- [ ] Build entity extraction
- [ ] Create filter mapping logic
- [ ] Test with example queries

### Phase 4: Summary Generation (Week 3)
- [ ] Implement summarization service
- [ ] Context-aware summary generation
- [ ] Cache summaries for performance
- [ ] Test summary quality

### Phase 5: Frontend (Week 3-4)
- [ ] Build AI search UI
- [ ] Integrate with InvenioRDM search
- [ ] Add result displays with summaries
- [ ] Create admin interface

### Phase 6: Testing & Demo (Week 4)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Demo queries preparation
- [ ] Documentation

## Technology Stack

### Python Packages Required
```python
# Add to setup.cfg [options]
install_requires =
    invenio-base>=1.2.5,<2.0.0
    invenio-records-rest>=2.2.0,<3.0.0
    invenio-search[opensearch2]>=2.1.0,<3.0.0
    torch>=2.0.0  # PyTorch for HuggingFace
    transformers>=4.30.0  # HuggingFace Transformers
    sentence-transformers>=2.2.0  # Sentence embeddings
    accelerate>=0.20.0  # Model acceleration
```

### Model Download Sizes
- `sentence-transformers/all-MiniLM-L6-v2`: ~90MB
- `facebook/bart-large-mnli`: ~1.6GB
- `facebook/bart-large-cnn`: ~1.6GB
- **Total**: ~3.3GB (models cached locally)

## Performance Considerations

### Embedding Generation
- **Time**: ~2-5 seconds per book (depending on size)
- **Strategy**: Background batch processing
- **Optimization**: Generate embeddings for chunks, not entire books

### Query Processing
- **Time**: <500ms for query parsing + search
- **Caching**: Cache parsed queries and embeddings
- **Optimization**: Pre-load models at startup

### Summary Generation
- **Time**: 2-10 seconds per summary
- **Strategy**: Generate on-demand, cache results
- **Optimization**: Generate for top 5 results only

## Example Queries to Support

1. **Attribute Filtering**:
   - "books with female protagonists"
   - "novels by American authors"
   - "works published in the 19th century"

2. **Semantic Search**:
   - "books about social injustice"
   - "stories with tragic endings"
   - "philosophical texts on ethics"

3. **Hybrid Queries**:
   - "Victorian novels with strong female characters"
   - "books about adventure in exotic locations"
   - "tragic love stories by Russian authors"

4. **Count Queries**:
   - "how many books by Shakespeare?"
   - "show me all dystopian novels"

## Integration with InvenioRDM

### Hooks
```python
# In ext.py
from invenio_records.signals import after_record_insert

def on_record_created(sender, record=None, **kwargs):
    """Trigger AI indexing when record is created."""
    from .tasks import generate_embeddings
    generate_embeddings.delay(record.id)

# Register signal
after_record_insert.connect(on_record_created)
```

### Search Override
```python
# Option 1: Parallel search (both systems)
# - Run AI search alongside standard search
# - Merge and rank results

# Option 2: Replacement (AI-first)
# - Replace default search with AI search
# - Fall back to standard for simple queries

# Option 3: Toggle (user choice)
# - UI toggle between AI and standard search
# - Preference stored per user
```

## Security Considerations

1. **Rate Limiting**: Limit AI search queries per user/IP
2. **Resource Management**: Limit concurrent model inference
3. **Input Validation**: Sanitize natural language inputs
4. **Model Access**: Restrict admin endpoints (embedding generation)

## Testing Strategy

### Unit Tests
- Query parser: test intent classification
- Embeddings: verify vector dimensions
- Summarizer: test summary length/quality

### Integration Tests
- End-to-end search workflow
- OpenSearch integration
- InvenioRDM hooks

### Performance Tests
- Query latency under load
- Embedding generation throughput
- Summary generation speed

### User Acceptance Tests
- Test example queries
- Evaluate result relevance
- Assess summary quality

---

## Next Steps

1. **Immediate**: Configure and download HuggingFace models
2. **Short-term**: Generate embeddings for 89 books
3. **Medium-term**: Implement query parsing and semantic search
4. **Long-term**: Build frontend and optimize performance
