# Community Tab - Obsolete Code Analysis

## Summary
This document outlines obsolete, deprecated, or unused code found in the Community tab (Community Pulse) across frontend and backend.

---

## BACKEND - Obsolete Code

### 1. Database Schema (`backend/database/community_pulse_schema.py`)

#### Builder Profile Functions (Lines 1840-2120)
**Status: DEPRECATED (Not removed)**

| Function | Lines | Status |
|----------|-------|--------|
| `create_builder_profile()` | 1840 | ⚠️ Deprecated |
| `get_builder_profile()` | 1905 | ⚠️ Deprecated |
| `search_builders()` | 1939 | ⚠️ Deprecated |
| `update_builder_profile()` | 2015 | ⚠️ Deprecated |
| `update_builder_aggregates()` | 2069 | ⚠️ Deprecated |
| `create_builder_review()` | 2125 | ⚠️ Deprecated |
| `get_builder_reviews()` | 2202 | ⚠️ Deprecated |
| `update_builder_review()` | 2255 | ⚠️ Deprecated |
| `delete_builder_review()` | 2323 | ⚠️ Deprecated |

#### RERA Verification Functions (Lines 2524-2700)
**Status: DEPRECATED (Not removed)**

| Function | Lines | Status |
|----------|-------|--------|
| `create_rera_verification()` | 2524 | ⚠️ Deprecated |
| `get_rera_verification()` | 2593 | ⚠️ Deprecated |
| `update_rera_verification()` | 2650 | ⚠️ Deprecated |

**Note:** The schema file has comments (lines 27-32) stating these were "DEPRECATED/REMOVED" but the code still exists.

---

### 2. Review Routes (`backend/routes/review_routes.py`)

#### Pydantic Models (Lines 177-314)
**Status: OBSOLETE (Not removed)**

- `CreateBuilderProfileRequest` (lines 177-190)
- `UpdateBuilderProfileRequest` (lines 192-209)
- `CreateBuilderReviewRequest` (lines 211-226)
- `UpdateBuilderReviewRequest` (lines 228-241)
- `BuilderProfileResponse` (lines 296-319)
- `BuilderReviewResponse` (lines 321-341)

#### Route Endpoints (Lines 517-733)
**Status: OBSOLETE (Still active but should be removed)**

| Endpoint | Method | Lines | Status |
|----------|--------|-------|--------|
| `/builder` | POST | 517-546 | ⚠️ Obsolete |
| `/builder/{builder_id}` | GET | 552-562 | ⚠️ Obsolete |
| `/builders` | GET | 567-589 | ⚠️ Obsolete |
| `/builder/{builder_id}` | PUT | 592-618 | ⚠️ Obsolete |
| `/builder/{builder_id}/review` | POST | 625-673 | ⚠️ Obsolete |
| `/builder/{builder_id}/reviews` | GET | 676-697 | ⚠️ Obsolete |
| `/builder/review/{review_id}` | PUT | 699-721 | ⚠️ Obsolete |
| `/builder/review/{review_id}` | DELETE | 724-745 | ⚠️ Obsolete |

**Note:** Line 812-814 contains comment "Builder profiles/reviews and RERA verification have been removed" but code still exists!

---

## FRONTEND - Obsolete Code

### 1. Community Components (`src/components/community/`)

#### Files Present but NOT Exported
**Status: OBSOLETE (Dead code)**

| File | Status | Reason |
|------|--------|--------|
| `BuilderProfile.jsx` | ❌ Dead Code | Not exported in index.js |
| `RERAVerification.jsx` | ❌ Dead Code | Not exported in index.js |

The `index.js` file (lines 14-17) explicitly states:
```
* REMOVED (Not aligned with product thesis):
* - BuilderProfile - Generic builder directory
* - RERAVerification - Not core to broker workflow
```

But these files remain in the directory, taking up space.

---

## RECOMMENDATIONS

### High Priority - Remove Dead Code

1. **Frontend:**
   - Delete `src/components/community/BuilderProfile.jsx`
   - Delete `src/components/community/RERAVerification.jsx`

2. **Backend Routes:**
   - Remove Builder profile endpoints from `review_routes.py` (lines 517-733)
   - Remove Builder-related Pydantic models (lines 177-341)
   - Remove unused `ReviewType.BUILDER` enum (line 64)

3. **Backend Schema:**
   - Remove Builder profile functions from `community_pulse_schema.py` (lines 1840-2367)
   - Remove RERA verification functions (lines 2524-2700)
   - Or add proper deprecation warnings and mark them as `@deprecated`

### Medium Priority - Clean Up

4. **Documentation:**
   - Update comments in `review_routes.py` to accurately reflect current state
   - Remove conflicting comments (line 812-814 vs actual code)

---

## Code Statistics

| Category | Count |
|----------|-------|
| Obsolete frontend files | 2 |
| Obsolete backend functions | 12 |
| Obsolete backend routes | 8 |
| Obsolete Pydantic models | 6 |
| Total obsolete items | ~28 |

---

*Analysis completed: 2026-03-11*
