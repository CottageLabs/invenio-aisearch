# Session 5 - "Show Similar Records" UI Feature

## Summary

Implemented a complete user-facing "Show Similar Records" feature, allowing users to click a button on any record detail page to view similar records based on k-NN semantic similarity.

## What Was Built

### 1. Enhanced Similar API Response

Extended the `/api/aisearch/similar/<record_id>` endpoint to include source record metadata:

**Before:**
```json
{
  "record_id": "abc123",
  "similar": [...],
  "total": 10
}
```

**After:**
```json
{
  "record_id": "abc123",
  "source_title": "Machine Learning in Practice",
  "source_creators": ["John Doe", "Jane Smith"],
  "similar": [...],
  "total": 10
}
```

### 2. Similar Records Page

Created `/aisearch/similar/<record_id>` route with:
- **Source record display** - Shows title and authors of the record being compared
- **Similar records list** - Shows up to 10 similar records with:
  - Title (linked to record)
  - Authors (first 3 + count)
  - Publication date, resource type, license/access status
  - Summary/description
  - Similarity score (0-1 scale)
- **Loading states** - "Finding similar records..." indicator
- **Error handling** - User-friendly error messages
- **Empty state** - "No similar records found" message

### 3. Instance Integration

Added "Show Similar Records" button to record detail pages in v13-ai instance:
- Button appears in its own segment below the main record content
- Uses Semantic UI styling consistent with InvenioRDM
- Icon-based design (clone outline icon)
- Links directly to similar records page

### 4. Frontend Assets

Created JavaScript client (`similar.js`) that:
- Automatically fetches similar records on page load
- Handles API errors gracefully
- Escapes HTML to prevent XSS
- Renders results dynamically with proper styling

## File Changes

### Created Files

**In `invenio-aisearch` extension:**
```
invenio_aisearch/
├── templates/invenio_aisearch/
│   └── similar.html                    # Similar records page template
└── assets/semantic-ui/js/invenio_aisearch/
    └── similar.js                       # Client-side JavaScript
```

**In `v13-ai` instance:**
```
site/v13_ai/templates/semantic-ui/invenio_app_rdm/records/
└── detail.html                          # Record detail page override
```

### Modified Files

**Service Layer:**
- `invenio_aisearch/services/results.py`
  - Updated `SimilarResult` class with `source_title` and `source_creators` properties
  - Updated `to_dict()` method to include source metadata in API response

- `invenio_aisearch/services/service/ai_search_service.py`
  - Modified `similar()` method to extract source record metadata from OpenSearch
  - Added creator name extraction logic
  - Pass source metadata to `SimilarResult` constructor

**UI Layer:**
- `invenio_aisearch/views.py`
  - Added `/aisearch/similar/<record_id>` route

- `invenio_aisearch/webpack.py`
  - Registered `invenio-aisearch-similar` JavaScript bundle

## Code Highlights

### Source Record Metadata Extraction

```python
# In ai_search_service.py
source_metadata = source_data.get('metadata', {})
source_title = source_metadata.get('title', 'Untitled')
source_creators_data = source_metadata.get('creators', [])
source_creators = [
    creator.get('person_or_org', {}).get('name', 'Unknown')
    for creator in source_creators_data
]

return SimilarResult(
    record_id=record_id,
    similar=similar_records,
    total=len(similar_records),
    source_title=source_title,
    source_creators=source_creators,
)
```

### Client-Side Rendering

```javascript
// In similar.js
async function fetchSimilarRecords(recordId) {
  const apiUrl = `/api/aisearch/similar/${recordId}?limit=10`;
  const response = await fetch(apiUrl);
  const data = await response.json();

  if (data.source_title) {
    sourceTitle.textContent = data.source_title;
    sourceCreators.textContent = data.source_creators.join('; ');
    sourceRecordInfo.style.display = 'block';
  }

  displayResults(data);
}
```

### Template Override Pattern

```html
<!-- In v13_ai/templates/.../records/detail.html -->
{% extends "invenio_app_rdm/records/detail.html" %}

{% block record_details %}
  {{ super() }}

  <div class="ui segment">
    <h3 class="ui header">Similar Records</h3>
    <a href="/aisearch/similar/{{ record.id }}" class="ui primary button">
      <i class="search icon"></i>
      Show Similar Records
    </a>
  </div>
{% endblock record_details %}
```

## User Workflow

1. User views any record detail page (e.g., `/records/abc123`)
2. Scrolls down to see "Show Similar Records" button
3. Clicks button → navigates to `/aisearch/similar/abc123`
4. Page loads and automatically fetches similar records via API
5. User sees:
   - Source record info at top
   - List of 10 most similar records
   - Can click any title to view that record
   - Can click "Show Similar" on that record to continue exploring

## Technical Notes

### Template Override Pattern

InvenioRDM uses Jinja2 template inheritance. To customize record pages:
1. Create matching path: `templates/semantic-ui/invenio_app_rdm/records/detail.html`
2. Extend base template: `{% extends "invenio_app_rdm/records/detail.html" %}`
3. Override specific blocks: `{% block record_details %}`
4. Call parent content: `{{ super() }}`

This pattern allows instance-specific customization without modifying the extension.

### Webpack Bundle Registration

JavaScript files in extensions must be registered in `webpack.py`:

```python
theme = WebpackThemeBundle(
    __name__,
    "assets",
    themes={
        "semantic-ui": dict(
            entry={
                "invenio-aisearch-search": "./js/invenio_aisearch/search.js",
                "invenio-aisearch-similar": "./js/invenio_aisearch/similar.js",
            },
        )
    },
)
```

Then included in templates:
```html
{% block javascript %}
{{ super() }}
{{ webpack['invenio-aisearch-similar.js'] }}
{% endblock javascript %}
```

### Asset Building

After modifying JavaScript or webpack config:
```bash
invenio-cli assets build
```

This compiles, bundles, and copies assets to the instance static directory.

## Benefits

1. **Discovery** - Users can explore related content easily
2. **Navigation** - Provides alternative pathways through the repository
3. **Validation** - Users can verify similarity algorithm quality
4. **Engagement** - Encourages exploration beyond single-record views
5. **Reusable** - Extension-based implementation works for any InvenioRDM instance

## Future Enhancements

Potential improvements for future sessions:

- **Filtering** - Allow users to filter by resource type, date range, etc.
- **Sorting** - Option to sort by date instead of similarity
- **Pagination** - Show more than 10 results with pagination
- **Explanations** - Show why records are similar (matching keywords, topics)
- **Export** - Allow exporting similar records list
- **Embedding** - Add similar records widget directly on detail page (without navigation)
- **Customization** - Configure similarity threshold, number of results per instance

## Related Files

See also:
- `ARCHITECTURE.md` - Overall system architecture
- `REFACTORING_NOTES.md` - Resource/service pattern refactoring
- `README_INTEGRATION.md` - Integration guide
- `tests/README.md` - Testing strategy

## Deployment

To deploy this feature:

1. **Extension** - Already in `invenio-aisearch` extension
2. **Instance** - Already in `v13-ai` instance
3. **Assets** - Run `invenio-cli assets build`
4. **Restart** - Restart web server to load new template
5. **Test** - Visit any record, click "Show Similar Records"

The feature is ready to use!
