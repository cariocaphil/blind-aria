# Admin Panel User Guide

## Who Can Use It?

Only users with emails in the `ADMIN_EMAILS` list (in `config.py`) can see and use the admin panel. Currently that includes:
- `phil.dijon@gmail.com`

To add more admins, edit `config.py` and add emails to the `ADMIN_EMAILS` list.

## How to Access

The **"📚 Catalogue Admin"** section appears to all users, but the content varies by login status:

### If You're NOT Logged In
1. Scroll down past the header in the main app
2. You'll see an expandable section labeled **"📚 Catalogue Admin"**
3. Click to expand it
4. You'll see a message: "👤 Log in to contribute to the catalogue..."
5. Click **"Send code"** to log in directly from this section
6. Enter your email and verify with the code sent to you
7. After logging in, refresh or continue to see the full form

### If You're Logged In (But Not Admin)
1. Scroll down past the header
2. Click the **"📚 Catalogue Admin"** expander
3. You'll see: "🔒 Adding songs is admin-only. If you'd like to contribute, please contact the maintainers."

### If You're an Admin
1. Scroll down past the header
2. Click the **"📚 Catalogue Admin"** expander
3. The full form is displayed

## How to Add a Song

### Step 1: Enter Basic Metadata

**Title**: The aria/song title
- Example: "Fin ch'han dal vino"

**Composer**: The composer's name
- Example: "Mozart"

**ID**: A unique identifier (lowercase with underscores)
- Example: `mozart_don_giovanni_champagne`
- Used internally for searching and linking
- Must be unique (cannot duplicate existing IDs)

### Step 2: Add Aliases (Optional)

Alternative names users might search for:
- Click "Add alias" to add more fields
- Examples:
  - "Champagne Aria"
  - "Don Giovanni Champagne"
  - "Fin ch'han dal vino"

Click the **✕** button to remove an alias.

### Step 3: Add YouTube Video IDs (Required)

You need at least **3 YouTube videos** for the system to accept the entry.

**How to get a YouTube ID:**
1. Open the YouTube video
2. Copy the video ID from the URL:
   - URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - ID: `dQw4w9WgXcQ`
3. Paste into the form

**Tips:**
- Different singers, different interpretations
- Different recordings (live vs studio)
- Leave blank fields empty (they're ignored)
- Click "Add YouTube ID" to add more than 5

### Step 4: Review the Preview

As you fill in the metadata, you'll see a **JSON preview** showing exactly what will be saved. This is the exact format used internally.

### Step 5: Save

Click **💾 Save to Catalogue** when ready.

The system will:
- Validate all required fields are filled
- Check that you have at least 3 YouTube videos
- Verify the ID is unique
- Add the work to the catalogue
- Clear the cache so it appears immediately

## Validation Rules

| Rule | Requirement | Error Message |
|------|-------------|---------------|
| Title | Required | "Title is required." |
| Composer | Required | "Composer is required." |
| ID | Required & Unique | "ID is required." / "ID '...' already exists" |
| Videos | Min 3 required | "Need at least 3 YouTube IDs" |

## After Saving

✓ You'll see a success message
✓ The form will reset
✓ The new aria will immediately appear in:
  - Solo mode search results
  - Solo mode random selection

## Example Entry

```json
{
  "id": "donizetti_la_donna_e_mobile",
  "title": "La donna è mobile",
  "composer": "Donizetti",
  "aliases": [
    "Rigoletto",
    "donna e mobile"
  ],
  "videos": [
    { "yt": "jV1tEKxU5Do" },
    { "yt": "W5Nh5D3R_s8" },
    { "yt": "bqTFfLXC8qc" },
    { "yt": "jLHoWOwdMHY" }
  ]
}
```

## Troubleshooting

### "Admin panel doesn't appear"
- Make sure you're logged in with an admin email
- Check that your email is in `ADMIN_EMAILS` in `config.py`
- Try logging out and back in

### "ID '...' already exists"
- That ID is already in the catalogue
- Use a different ID (e.g., add `_v2` to the end)

### "Need at least 3 YouTube IDs"
- You're not providing enough YouTube video links
- Verify the YouTube IDs are correct (no spaces, correct format)
- Blank fields are ignored, so remove empty ones or fill them in

### "Title/Composer/ID is required"
- Make sure all three required fields are filled in
- Check for trailing spaces that might be treated as empty

## Future Features (Coming Soon)

- ☐ YouTube search integration (type query, get video suggestions)
- ☐ AI-assisted metadata (auto-fill composer, aliases)
- ☐ Bulk import from CSV
- ☐ Admin dashboard with statistics
- ☐ Approval workflow for suggested works

## Questions?

If something isn't working, check:
1. Are you logged in with the correct email?
2. Are all required fields filled?
3. Do you have at least 3 valid YouTube IDs?
4. Are there any validation error messages in red?
