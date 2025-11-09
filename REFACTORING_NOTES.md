# Refactoring to InvenioRDM Resource Pattern

## Summary

Refactored invenio-aisearch from plain Flask blueprints to InvenioRDM's resource/service pattern, following the same architecture as invenio-notify.

## Changes

### Architecture

**Before:**
- Plain Flask blueprint in `api_views.py`
- Direct service calls in view functions
- setup.py + setup.cfg configuration

**After:**
- Resource pattern with dependency injection
- Separated service/resource layers
- Pure pyproject.toml configuration

### New Structure

```
invenio_aisearch/
├── resources/
│   ├── config.py              # AISearchResourceConfig
│   └── resource/
│       └── ai_search_resource.py  # AISearchResource (HTTP layer)
├── services/
│   ├── config.py              # AISearchServiceConfig
│   ├── results.py             # Result objects
│   ├── schemas.py             # Marshmallow schemas
│   └── service/
│       └── ai_search_service.py   # AISearchService (business logic)
├── blueprints.py              # Blueprint factory functions
├── ext.py                     # Updated with init_services/init_resources
└── ...
```

### Key Files

**Removed:**
- `setup.py`
- `setup.cfg`

**Created:**
- `pyproject.toml` - Modern Python packaging
- `invenio_aisearch/resources/` - Resource layer
- `invenio_aisearch/services/` - Service layer
- `invenio_aisearch/blueprints.py` - Blueprint factories

**Updated:**
- `invenio_aisearch/ext.py` - Extension initialization pattern

### Benefits

1. **Separation of Concerns** - HTTP layer separate from business logic
2. **Dependency Injection** - Service injected into resource
3. **Schema Validation** - Marshmallow validates all requests
4. **Content Negotiation** - Response handlers support multiple formats
5. **Testability** - Services and resources independently testable
6. **InvenioRDM Native** - Follows official patterns

## API Endpoints

All endpoints remain functionally identical:

- `POST/GET /api/aisearch/search` - Natural language search
- `GET /api/aisearch/similar/<record_id>` - Find similar records
- `GET /api/aisearch/status` - Service status

## Migration Notes

Old `api_views.py` can be deprecated. All functionality moved to resource pattern.

Entry point changed from:
```toml
invenio_aisearch_api = "invenio_aisearch.api_views:create_api_blueprint"
```

To:
```toml
ai_search_api = "invenio_aisearch.blueprints:create_ai_search_api_bp"
```

## Pattern Reference

Based on invenio-notify implementation. See:
- `/home/steve/code/cl/Invenio/invenio-notify/`
- InvenioRDM docs: https://inveniordm.docs.cern.ch/maintenance/internals/resource/
