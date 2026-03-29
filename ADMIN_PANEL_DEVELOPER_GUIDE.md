# Admin Panel Developer Guide

## Architecture Overview

The admin panel is designed as a modular, extensible feature with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│  app.py (orchestrator)                                  │
│  - Calls show_admin_panel()                              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  ui/admin_panel.py (presentation layer)                 │
│  - Streamlit UI components                              │
│  - Three-branch conditional rendering:                  │
│    ├─ Not logged in → show admin_login_block()          │
│    ├─ Logged in (non-admin) → show "admin only" msg     │
│    └─ Logged in (admin) → show full form + suggestions  │
│  - Form state management                                │
│  - Calls utility and suggestion functions               │
└──────┬────────────────────────────┬──────────┬──────────┘
       │                            │          │
       ▼                            ▼          ▼
┌──────────────┐   ┌──────────────────┐  ┌─────────────────┐
│ auth.py      │   │ utils.py         │  │ ai_suggestions.py│
│ - admin_     │   │ (business logic) │  │ (helpers)       │
│   login_block│   │ - Validation     │  │ - generate_     │
│ - OTP        │   │ - Normalization  │  │   search_queries│
│   verification│  │ - Storage I/O    │  │ - search_       │
└──────────────┘   │ - Orchestration  │  │   youtube()     │
                   └────────┬─────────┘  │ - filter_       │
                            │            │   candidates()  │
                            ▼            │ - rank_         │
                   ┌──────────────────┐  │   candidates()  │
                   │ config.py        │  │ - suggest_      │
                   │ - ADMIN_EMAILS   │  │   videos()      │
                   │ - MIN_VERSIONS_  │  │ - find_similar_ │
                   │   REQUIRED       │  │   works()       │
                   │ - DATA_PATH      │  └─────────────────┘
                   └──────────────────┘
```

## Key Design Principles

### 1. Security Through Layering
- UI layer checks `is_admin_user()` before rendering
- Business logic also checks before persisting
- Frontend hiding is not security; backend validation is

### 2. Data Flow
```
User Input (UI) → Normalize → Validate → Create → Persist → Clear Cache → Success
                                    ↓
                           Error Message ← Validation Fail
```

### 3. Extensibility Points (Marked with TODO)

#### A. Metadata Inference
**Location**: `ui/admin_panel.py` - Currently users manually enter title/composer

**Future**: Add query input that AI or search can process:
```python
# TODO: AI-assisted metadata inference
# query = st.text_input("Search for aria or describe it...")
# if query:
#     title, composer = infer_metadata_from_query(query)
#     aliases = suggest_aliases(title, composer)
```

#### B. YouTube Integration ✅ IMPLEMENTED
**Location**: `ui/ai_suggestions.py` and `ui/admin_panel.py`

**Implementation:**
- `generate_search_queries()` creates 3 refined search queries
- `search_youtube()` calls YouTube Data API v3 /search endpoint
- `filter_candidates()` removes instrumental/karaoke/tutorial videos
- `rank_candidates()` scores by source (Lebendige Vergangenheit +3, Preiser +2, live +1)
- `suggest_videos()` runs full pipeline and returns top results
- UI shows checkboxes with pre-selected top 3–5 results
- User clicks "Use selected videos" to merge into form

**Environment Requirements:**
```python
# Set in environment or .streamlit/secrets.toml
os.getenv("YOUTUBE_API_KEY")  # YouTube Data API v3 key
```

**Extending with Caching:**
```python
# Add to search_youtube() for quota efficiency:
@st.cache_data(ttl=3600)
def search_youtube(query: str) -> list[dict]:
    ...
```

#### C. Duplicate Detection ✅ IMPLEMENTED
**Location**: `ui/ai_suggestions.py`

**Implementation:**
- `find_similar_works()` detects suspiciously similar titles/composers
- Uses substring matching (title_lower in existing_title, etc.)
- Checks against all three fields: title, composer, _search (aliases)

**Future Enhancement:**
```python
# Replace substring matching with fuzzy:
from rapidfuzz import fuzz

def find_similar_works(title: str, composer: str, works: list[dict]) -> list[dict]:
    threshold = 80
    matches = []
    for w in works:
        if (fuzz.ratio(title.lower(), w['title'].lower()) > threshold or
            fuzz.ratio(composer.lower(), w['composer'].lower()) > threshold):
            matches.append(w)
    return matches
```

#### D. Storage Backend
**Location**: `utils.py` - Currently uses `load_catalog_file()` and `save_catalog_file()`

**Future**: Migrate from JSON file to Supabase:
```python
# TODO: Replace with Supabase

# Option 1: In load_catalog_file()
def load_catalog_file() -> dict:
    # sb = supabase.create_client(...)
    # response = sb.table('works').select('*').execute()
    # return {"works": response.data}
    ...

# Option 2: In save_catalog_file()
def save_catalog_file(catalog_data: dict) -> None:
    # sb.table('works').insert(new_work).execute()
    ...

# Option 3: Create separate functions
def add_work_to_supabase(work: dict):
    sb = get_supabase_client()
    result = sb.table('works').insert([work]).execute()
    return result.data
```

#### E. Admin User Management
**Location**: `config.py` - Currently hardcoded `ADMIN_EMAILS`

**Future**: Move to Supabase table:
```python
# TODO: Replace ADMIN_EMAILS with Supabase query

def is_admin_user() -> bool:
    email = st.session_state.get("sb_auth", {}).get("email")
    if not email:
        return False
    
    # Query Supabase instead of hardcoded list
    sb = get_supabase_client()
    result = sb.table('admin_users').select('*').eq('email', email).execute()
    return len(result.data) > 0
```

## Function Reference

### In `auth.py`

#### `admin_login_block() -> None`
**Purpose**: Render OTP login form with catalogue contribution context
**Used by**: `show_admin_panel()` when user is not logged in
**Messaging**: "Log in to contribute" (distinct from party mode's "Sign in to play with someone")
**Implementation**: Wraps existing OTP flow with contextual heading and description
**Returns**: None (renders UI, sets `st.session_state["sb_auth"]` on successful verification)

### In `utils.py`

#### `is_admin_user() -> bool`
**Purpose**: Check if current logged-in user is an admin
**Current**: Checks `st.session_state["sb_auth"]["email"]` against `ADMIN_EMAILS`
**Future**: Could query Supabase table

#### `load_catalog_file() -> dict`
**Purpose**: Load entire catalogue from storage
**Current**: Reads works.json
**Future**: Read from Supabase `works` table
**Error Handling**: Raises `FileNotFoundError` or `ValueError`

#### `save_catalog_file(catalog_data: dict) -> None`
**Purpose**: Persist catalogue to storage
**Current**: Writes to works.json with 3-space indentation
**Future**: Write to Supabase (or use transaction)
**Error Handling**: Raises `IOError`

#### `validate_work_entry(...) -> tuple[bool, str]`
**Purpose**: Comprehensive validation of work data
**Returns**: `(is_valid, error_message)`
**Rules Checked**:
- Required: title, composer, id
- Unique: id not in existing_ids
- Minimum: 3+ videos
**Status**: ✓ Complete, no changes needed
**Future**: Could add more rules (e.g., language checks)

#### `create_work_entry(...) -> dict`
**Purpose**: Create properly-formatted work dict
**Returns**: Dict with keys: id, title, composer, aliases, videos
**Status**: ✓ Complete, handles schema correctly
**Future**: Could add timestamps, metadata

#### `add_work_to_catalog(...) -> tuple[bool, str]`
**Purpose**: Main orchestration - validate, create, persist
**Returns**: `(success, message)`
**Flow**: 
1. Load current catalogue
2. Check against existing IDs
3. Validate
4. Create entry
5. Append
6. Save
7. Clear cache
**Status**: ✓ Complete, well-encapsulated
**Future**: Could return new work dict instead of just message

### In `ui/admin_panel.py`

#### `show_admin_panel() -> None`
**Purpose**: Render the entire admin UI to all users with contextual content
**Visibility**: Always renders as an expandable section; content changes based on auth status:
  - **Not logged in**: Shows `admin_login_block()` for contextual login
  - **Logged in (non-admin)**: Shows "admin only" message
  - **Logged in (admin)**: Shows full form
**Features**:
- Expander for clean layout
- Form state management via `st.session_state`
- Dynamic list management (aliases, videos)
- YouTube search suggestion UI with checkboxes
- JSON preview (admin only)
- Validation error display (admin only)
**Status**: ✓ Complete, all features working
**Future**: Could split into smaller helper functions if UI grows

### In `ui/ai_suggestions.py`

#### `generate_search_queries(query: str) -> list[str]`
**Purpose**: Create 3 progressively-specific search queries from base string
**Returns**: List of 3 strings with suffixes: "Lied", "live recital", "Lebendige Vergangenheit"
**Examples**: 
- Input: "Schumann Die alten bösen Lieder"
- Output: ["Schumann Die alten bösen Lieder Lied", "Schumann Die alten bösen Lieder live recital", ...]
**Status**: ✓ Complete
**Future**: Could add more suffix variants based on user feedback

#### `search_youtube(query: str) -> list[dict]`
**Purpose**: Call YouTube Data API v3 /search endpoint
**Returns**: List of dicts: `{"videoId": str, "title": str, "channel": str}`
**Requirements**: `YOUTUBE_API_KEY` environment variable must be set
**Behavior**:
- Returns empty list if key missing or API errors (never crashes)
- Deduplicates by videoId
- Fetches up to 5 results per query
- Shows warning in Streamlit on API errors
**Status**: ✓ Complete, production-ready
**Future**: Add `@st.cache_data(ttl=3600)` for quota reduction

#### `filter_candidates(videos: list[dict]) -> list[dict]`
**Purpose**: Remove noise videos (instrumental, piano, karaoke, etc.)
**Returns**: Filtered list (never empty if input not empty)
**Filters**: Title/channel matching (case-insensitive): instrumental, piano, violin, karaoke, tutorial, score, sheet music, backing track, arrangement
**Status**: ✓ Complete, effective for typical searches
**Future**: Could add user-configurable filter terms

#### `rank_candidates(videos: list[dict]) -> list[dict]`
**Purpose**: Score and sort videos by quality indicators
**Returns**: Sorted list (highest score first)
**Scoring**:
- +3: "lebendige vergangenheit" (classic vocal label)
- +2: "preiser" (high-quality label)
- +1: "live" | "recital" | "liederabend"
- -2: soft penalty if instrumental/piano/violin still present
**Status**: ✓ Complete
**Future**: Could use real ML model for scoring

#### `suggest_videos(query: str, max_results: int = 8) -> list[dict]`
**Purpose**: Full pipeline - generate queries → fetch → filter → rank
**Returns**: List of top results with attached `_score` for debugging
**Flow**:
1. `generate_search_queries(query)` → 3 queries
2. For each query: `search_youtube()` and deduplicate by videoId
3. `filter_candidates()` → remove noise
4. `rank_candidates()` → sort by quality
5. Return top `max_results` with scores
**Status**: ✓ Complete, ready for production
**Future**: Could add duplicate detection across pipelines

#### `find_similar_works(title: str, composer: str, works: list[dict]) -> list[dict]`
**Purpose**: Detect duplicate or suspiciously similar works
**Returns**: List of existing works that are similar
**Matching**: Substring matching (case-insensitive) on:
- title (both directions: substring and contains)
- composer (if given)
- _search index (pre-built field covering aliases)
**Status**: ✓ Complete, basic functionality working
**Future**: Replace substring with fuzzy matching (e.g., rapidfuzz) for robustness

## State Management

The admin panel uses Streamlit's `st.session_state` for form management:

```python
st.session_state.admin_title       # str
st.session_state.admin_composer    # str
st.session_state.admin_id          # str
st.session_state.admin_aliases     # list[str]
st.session_state.admin_videos      # list[str]
st.session_state.admin_suggest_results    # list[dict] (AI suggestions)
st.session_state.admin_suggest_selected   # dict[str, bool] (checkbox state)
```

### Initialization Pattern

**Critical**: All session_state keys must be initialized BEFORE any widgets are created:

```python
def show_admin_panel():
    # ✅ Initialize ALL state at function entry
    if "admin_title" not in st.session_state:
        st.session_state.admin_title = ""
    # ... more keys ...
    _init_suggestion_state()  # AI suggestion state
    
    # ❌ THEN create widgets (now safe, keys already exist)
    title = st.text_input(..., key="admin_title")
```

**Why**: Streamlit forbids modifying `st.session_state` values that are already bound to widgets. Initializing upfront prevents this error.

### Form Reset Pattern

On successful save, use `.pop()` instead of direct assignment:

```python
# ❌ Wrong - causes "cannot modify widget-bound session_state" error
st.session_state.admin_title = ""

# ✅ Correct - removes key, allows fresh initialization on next render
st.session_state.pop("admin_title", None)
st.rerun()  # Triggers new render with initialization check
```

**Why**: `.pop()` removes the key entirely, so the initialization check runs again on the next render, creating a fresh key with default values.

**Design**: Each field resets after successful save, allowing rapid entry of multiple works.

**Future**: Could persist form state to browser localStorage for recovery on page refresh.

## Testing Guide

### Unit Tests (Python)

```python
# test_admin_utils.py
def test_is_admin_user_true():
    st.session_state["sb_auth"] = {"email": "phil.dijon@gmail.com"}
    assert is_admin_user() == True

def test_is_admin_user_false():
    st.session_state["sb_auth"] = {"email": "user@example.com"}
    assert is_admin_user() == False

def test_validate_work_entry_missing_title():
    is_valid, msg = validate_work_entry(
        title="", composer="Mozart", work_id="test",
        aliases=[], video_ids=["a", "b", "c"], existing_ids=[]
    )
    assert is_valid == False
    assert "Title is required" in msg

def test_normalize_aliases_deduplicates():
    result = normalize_aliases(["alias1", "alias1", "alias2", ""])
    assert result == ["alias1", "alias2"]

def test_create_work_entry_schema():
    work = create_work_entry(
        "Title", "Composer", "id", ["alias"], ["vid1", "vid2"]
    )
    assert work["id"] == "id"
    assert work["videos"] == [{"yt": "vid1"}, {"yt": "vid2"}]
    assert work["aliases"] == ["alias"]
```

### Integration Tests (Streamlit)

```python
# Test via Streamlit app
# 1. Log in as admin
# 2. Expand admin panel
# 3. Fill form with valid data
# 4. Click save
# 5. Verify work appears in catalogue
# 6. Reload app, verify work persists
```

## Performance Considerations

1. **Cache Clearing**: `st.cache_data.clear()` after save may be expensive if catalogue is large
   - Future: Use targeted cache invalidation
   
2. **File I/O**: JSON read/write on every save
   - Future: Use Supabase for transactional writes

3. **Form Render**: Dynamic lists with many entries could be slow
   - Current: Limited to reasonable number of fields
   - Future: Add pagination if >20 items

## Error Handling Patterns

All functions that can fail return `(success, message)` tuples or raise exceptions:

```python
# Pattern 1: Boolean + message
success, message = add_work_to_catalog(...)
if success:
    st.success(message)
else:
    st.error(message)

# Pattern 2: Exceptions (for file I/O)
try:
    catalog = load_catalog_file()
except FileNotFoundError as e:
    st.error(f"Catalogue not found: {e}")
except ValueError as e:
    st.error(f"Catalogue corrupted: {e}")
```

## Migration Checklist

When ready to migrate from JSON to Supabase:

- [ ] Create `works` table in Supabase with columns: id, title, composer, aliases, videos
- [ ] Write migration script to import existing works.json into table
- [ ] Replace `load_catalog_file()` with Supabase query
- [ ] Replace `save_catalog_file()` with Supabase insert
- [ ] Update `validate_work_entry()` to query Supabase for existing IDs
- [ ] Add row-level security policies to Supabase
- [ ] Remove works.json from repo (or keep as backup)
- [ ] Update docs
- [ ] Test with actual Supabase data
- [ ] Deploy to production

## Code Quality Standards

- **Type hints**: All function signatures have type hints
- **Docstrings**: All public functions have docstrings with Args/Returns/Raises
- **Error messages**: User-friendly, not technical
- **Comments**: TODO markers for future work, explanations for complex logic
- **Tests**: Unit tests for validators, integration tests for UI
- **Logging**: Consider adding `st.write()` debug output for troubleshooting (can be wrapped in `if st.checkbox("Debug mode")`

## Links & References

- Streamlit docs: https://docs.streamlit.io/
- Supabase Python client: https://github.com/supabase/supabase-py
- YouTube API: https://developers.google.com/youtube/v3
- Works.json schema: See data/works.json examples
