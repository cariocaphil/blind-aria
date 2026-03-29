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
│    └─ Logged in (admin) → show full form                │
│  - Form state management                                │
│  - Calls utility functions for logic                     │
└────────────┬──────────────────────────┬────────────────┘
             │                          │
             ▼                          ▼
┌──────────────────────┐   ┌──────────────────────────┐
│  auth.py             │   │  utils.py                │
│  - admin_login_      │   │  (business logic layer)  │
│    block()           │   │  - Validation            │
│  - OTP verification  │   │  - Normalization         │
└──────────────────────┘   │  - Storage I/O           │
                           │  - Orchestration         │
                           └──────────┬───────────────┘
                                      │
                                      ▼
                           ┌──────────────────────────┐
                           │  config.py               │
                           │  - ADMIN_EMAILS          │
                           │  - MIN_VERSIONS_REQUIRED │
                           │  - DATA_PATH             │
                           └──────────────────────────┘
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

#### B. YouTube Integration
**Location**: `ui/admin_panel.py` - Currently users manually paste YouTube IDs

**Future**: Search YouTube and auto-suggest videos:
```python
# TODO: YouTube search integration
# if st.button("🔍 Search YouTube"):
#     results = search_youtube(title, composer)
#     for result in results:
#         if st.button(f"Add: {result['title']}"):
#             video_ids.append(result['id'])
```

#### C. Storage Backend
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

#### D. Admin User Management
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
- JSON preview (admin only)
- Validation error display (admin only)
**Status**: ✓ Complete, all features working
**Future**: Could split into smaller helper functions if UI grows

## State Management

The admin panel uses Streamlit's `st.session_state` for form management:

```python
st.session_state.admin_title       # str
st.session_state.admin_composer    # str
st.session_state.admin_id          # str
st.session_state.admin_aliases     # list[str]
st.session_state.admin_videos      # list[str]
```

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
