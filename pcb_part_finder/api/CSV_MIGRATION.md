
Okay, let's create a detailed blueprint and then break it down into iterative, actionable steps suitable for generating prompts for a code-generation LLM.

## Detailed Blueprint

1.  **Database Layer:**
    *   **Objective:** Define the storage structure for cached Mouser API responses.
    *   **Tasks:**
        *   Modify `init.sql` to add a new table `mouser_api_cache`.
        *   Define columns: `cache_id` (PK, auto-incrementing), `search_term` (text, indexed), `search_type` (text, e.g., 'keyword' or 'mpn', indexed), `response_data` (JSONB for efficient storage and potential querying of JSON content), `cached_at` (timestamp with timezone, indexed, defaults to current time).
        *   Create a composite index on `(search_term, search_type)` for fast lookups.
        *   Create an index on `cached_at` for potential cleanup tasks.
    *   **SQLAlchemy Model:**
        *   Create a new file `pcb_part_finder/core/models.py` (if it doesn't exist).
        *   Define a declarative base if one doesn't already exist centrally (e.g., in `database.py`).
        *   Define the `MouserApiCache` model mapping to the `mouser_api_cache` table, including appropriate SQLAlchemy types (`Integer`, `String`, `JSONB` from `sqlalchemy.dialects.postgresql`, `TIMESTAMP`).

2.  **Cache Manager Logic:**
    *   **Objective:** Encapsulate the logic for checking, retrieving, and storing cache entries.
    *   **Tasks:**
        *   Create a new file `pcb_part_finder/core/cache_manager.py`.
        *   Define a class `MouserApiCacheManager`.
        *   Implement `get_cached_response(self, search_term: str, search_type: str, db: Session, max_age_seconds: int = 86400)`:
            *   Queries the `MouserApiCache` model.
            *   Filters by `search_term` and `search_type`.
            *   Filters by `cached_at` being within the `max_age_seconds`.
            *   Orders by `cached_at` descending and takes the first result.
            *   Returns the `response_data` (as a Python dict/list) if a valid entry is found, else `None`.
        *   Implement `cache_response(self, search_term: str, search_type: str, response_data: dict, db: Session)`:
            *   Creates a new `MouserApiCache` instance.
            *   Populates it with the provided data.
            *   Adds the instance to the session (`db.add()`).
            *   Commits the session (`db.commit()`).
            *   Includes error handling (e.g., `try...except...finally` with `db.rollback()` in case of commit errors).

3.  **Mouser API Integration:**
    *   **Objective:** Modify the existing Mouser API functions to utilize the cache manager.
    *   **Tasks:**
        *   Refactor `search_mouser_by_keyword` and `search_mouser_by_mpn` in `pcb_part_finder/core/mouser_api.py`.
        *   Add `cache_manager: MouserApiCacheManager` and `db: Session` as parameters to both functions.
        *   **Inside each function:**
            *   Call `cache_manager.get_cached_response` first.
            *   If a cached response is returned:
                *   **Crucially:** Parse this raw cached JSON *exactly* as the original API response would be parsed later in the function (extracting specific fields, formatting price/availability etc. for `search_mouser_by_mpn`, returning the list of parts for `search_mouser_by_keyword`).
                *   Return the parsed data.
            *   If no cached response:
                *   Proceed with the `requests.post` call to the Mouser API.
                *   Handle API errors (`MouserApiError`).
                *   If the API call is successful (status 200, no errors in JSON):
                    *   Get the raw JSON response (`response.json()`).
                    *   Call `cache_manager.cache_response` with the search term, type, *raw JSON response*, and the db session.
                    *   **Crucially:** Parse the *freshly fetched* raw JSON response (the same parsing logic as used for the cached path).
                    *   Return the parsed data.
                *   If the API call fails or returns errors, raise `MouserApiError` as before (do not cache errors).

4.  **API Endpoint Wiring:**
    *   **Objective:** Connect the database session and cache manager instance to the API endpoints that trigger Mouser searches.
    *   **Tasks:**
        *   Identify the FastAPI endpoints (likely in `pcb_part_finder/api/main.py` or similar) that call `search_mouser_by_keyword` or `search_mouser_by_mpn`.
        *   Ensure these endpoints use FastAPI's dependency injection to get a database session: `db: Session = Depends(get_db)`.
        *   Instantiate the `MouserApiCacheManager`. For simplicity initially, this could be a module-level instance in the API endpoint file or passed down from the application creation logic. A dependency provider function would be cleaner long-term.
        *   Pass the `cache_manager` instance and the `db` session to the calls to `search_mouser_by_keyword` and `search_mouser_by_mpn`.

## Iterative Steps & LLM Prompts

Here's the breakdown into smaller steps, each followed by a prompt for a code-generation LLM.

---

### Step 1: Database Schema Update

**Context:** Define the database table structure in the initialization script.

**LLM Prompt:**

```text
Modify the `init.sql` file. Add a new table definition for `mouser_api_cache` at the end of the file, before the index creation statements.

The table should have the following columns:
- `cache_id`: SERIAL PRIMARY KEY
- `search_term`: TEXT, NOT NULL
- `search_type`: VARCHAR(50), NOT NULL (e.g., 'keyword', 'mpn')
- `response_data`: JSONB (stores the raw JSON response from Mouser)
- `cached_at`: TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT CURRENT_TIMESTAMP

After the existing index definitions, add two new indexes for this table:
1. A unique index named `idx_mouser_cache_term_type` on (`search_term`, `search_type`).
2. An index named `idx_mouser_cache_cached_at` on the `cached_at` column.
```

---

### Step 2: SQLAlchemy Model Definition

**Context:** Create the Python representation of the database table using SQLAlchemy. This might involve creating a new `models.py` file.

**LLM Prompt:**

```text
1. Check if the file `pcb_part_finder/core/models.py` exists. If not, create it.
2. Ensure the file imports necessary components: `Column`, `Integer`, `String`, `TIMESTAMP` from `sqlalchemy`, and `JSONB` from `sqlalchemy.dialects.postgresql`.
3. Also, ensure it imports or defines a SQLAlchemy `declarative_base`. Assume a base named `Base` is available, potentially imported from `pcb_part_finder.core.database` if that's where SQLAlchemy setup resides, otherwise define `Base = declarative_base()`.
4. Define a new SQLAlchemy model class `MouserApiCache` that inherits from `Base`.
5. Set the `__tablename__` attribute to `'mouser_api_cache'`.
6. Define class attributes corresponding to the table columns created in `init.sql` in Step 1, using the appropriate SQLAlchemy types:
    - `cache_id`: `Column(Integer, primary_key=True)`
    - `search_term`: `Column(String, nullable=False)`
    - `search_type`: `Column(String(50), nullable=False)`
    - `response_data`: `Column(JSONB)`
    - `cached_at`: `Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())` (Requires importing `func` from `sqlalchemy.sql`).
7. Include necessary table arguments for the indexes defined in Step 1: `Index('idx_mouser_cache_term_type', 'search_term', 'search_type', unique=True)` and `Index('idx_mouser_cache_cached_at', 'cached_at')`. (Requires importing `Index` from `sqlalchemy`).
```

---

### Step 3: Cache Manager Class Structure

**Context:** Create the file and class structure for the cache manager, defining methods but leaving implementation for the next steps.

**LLM Prompt:**

```text
1. Create a new file named `pcb_part_finder/core/cache_manager.py`.
2. Add the necessary imports at the top:
   - `from datetime import datetime, timedelta, timezone`
   - `from typing import Optional, Dict, Any`
   - `from sqlalchemy.orm import Session`
   - `from .models import MouserApiCache` # Assumes models.py is in the same directory
3. Define a class named `MouserApiCacheManager`.
4. Define the `__init__` method (it can be empty for now: `pass`).
5. Define the method signature for getting cached data:
   `get_cached_response(self, search_term: str, search_type: str, db: Session, max_age_seconds: int = 86400) -> Optional[Dict[str, Any]]:`
   - Add a docstring explaining its purpose (checks cache, returns parsed JSON data or None).
   - Use `pass` as the method body for now.
6. Define the method signature for saving data to the cache:
   `cache_response(self, search_term: str, search_type: str, response_data: Dict[str, Any], db: Session) -> None:`
   - Add a docstring explaining its purpose (saves raw response data to cache).
   - Use `pass` as the method body for now.
```

---

### Step 4: Implement Cache Retrieval Logic

**Context:** Fill in the logic for the `get_cached_response` method in the cache manager.

**LLM Prompt:**

```text
Modify the `pcb_part_finder/core/cache_manager.py` file. Implement the body of the `get_cached_response` method within the `MouserApiCacheManager` class.

The logic should perform the following:
1. Calculate the oldest acceptable timestamp (`datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)`).
2. Query the `MouserApiCache` model using the provided `db` session.
3. Filter the query:
   - `MouserApiCache.search_term == search_term`
   - `MouserApiCache.search_type == search_type`
   - `MouserApiCache.cached_at >= oldest_acceptable_timestamp`
4. Order the results by `MouserApiCache.cached_at` descending (`.order_by(MouserApiCache.cached_at.desc())`).
5. Get the first result (`.first()`).
6. If a result is found:
   - Return the `result.response_data` (which should already be a Python dict/list due to JSONB).
7. If no result is found or any exception occurs during the query, return `None`. Include basic error logging if an exception occurs.
```

---

### Step 5: Implement Cache Storage Logic

**Context:** Fill in the logic for the `cache_response` method in the cache manager.

**LLM Prompt:**

```text
Modify the `pcb_part_finder/core/cache_manager.py` file. Implement the body of the `cache_response` method within the `MouserApiCacheManager` class.

The logic should perform the following:
1. Create a new instance of the `MouserApiCache` model.
2. Populate its attributes: `search_term`, `search_type`, and `response_data` using the method arguments. `cached_at` will be set by the database default.
3. Use a `try...except...finally` block for database operations:
   - **Try:**
     - Add the new `MouserApiCache` instance to the session (`db.add(new_cache_entry)`).
     - Commit the session (`db.commit()`).
   - **Except:**
     - Catch potential database errors (e.g., `Exception as e`).
     - Log the error (e.g., `print(f"Error caching response: {e}")`).
     - Roll back the session (`db.rollback()`).
   - **Finally:**
     - This block is optional here but good practice if resources needed cleanup.
```

---

### Step 6: Integrate Cache into `search_mouser_by_mpn`

**Context:** Modify the first Mouser API function to use the cache manager for getting and setting cache data.

**LLM Prompt:**

```text
Modify the `pcb_part_finder/core/mouser_api.py` file. Refactor the `search_mouser_by_mpn` function:

1.  Add two new parameters to the function signature: `cache_manager: 'MouserApiCacheManager'` and `db: Session`. (You'll need `from pcb_part_finder.core.cache_manager import MouserApiCacheManager` and `from sqlalchemy.orm import Session`). Use a forward reference `'MouserApiCacheManager'` in the type hint if needed to avoid circular imports, although importing directly should be fine if `cache_manager.py` doesn't import from `mouser_api.py`. Also add `from datetime import datetime` if needed for timestamp comparisons later.
2.  **Cache Check:**
    *   At the beginning of the function, call `cached_data = cache_manager.get_cached_response(search_term=mpn, search_type='mpn', db=db)`.
    *   If `cached_data` is not `None`:
        *   Replicate the parsing logic that happens *after* a successful API call within this function (extracting Mouser Part Number, MPN, Manufacturer, Description, Datasheet URL, Price, Availability from the `cached_data`). This involves accessing keys like 'SearchResults', 'Parts', iterating if necessary (though MPN search usually returns one part), handling 'PriceBreaks', and 'AvailabilityInStock'/'LeadTime'.
        *   Return the formatted dictionary containing the parsed part details.
3.  **API Call & Cache Write:**
    *   If `cached_data` *is* `None`, proceed with the existing logic to prepare the API request payload and headers.
    *   Inside the `try` block for the `requests.post` call:
        *   After a successful response (`response.status_code == 200`) and *before* parsing the JSON:
            *   Get the raw JSON: `raw_response_data = response.json()`.
            *   Check if `raw_response_data` contains API-level errors (`'Errors'` key).
            *   If **no** API-level errors: Call `cache_manager.cache_response(search_term=mpn, search_type='mpn', response_data=raw_response_data, db=db)`. Handle potential exceptions from caching gracefully (e.g., log but don't fail the main API call).
        *   **Important:** Continue the existing logic to parse the `raw_response_data` (which you just potentially cached) to extract the required fields and return the formatted dictionary. Ensure this parsing logic is the *same* as the one used for the cache hit path.
4.  Ensure the rest of the error handling (API errors, network errors) remains the same. Only cache successful responses without API-level errors.
```

---

### Step 7: Integrate Cache into `search_mouser_by_keyword`

**Context:** Modify the second Mouser API function similarly.

**LLM Prompt:**

```text
Modify the `pcb_part_finder/core/mouser_api.py` file. Refactor the `search_mouser_by_keyword` function:

1.  Add the same two parameters as in Step 6: `cache_manager: 'MouserApiCacheManager'` and `db: Session`. Ensure necessary imports are present.
2.  **Cache Check:**
    *   At the beginning of the function, call `cached_data = cache_manager.get_cached_response(search_term=keyword, search_type='keyword', db=db)`.
    *   If `cached_data` is not `None`:
        *   This function expects to return a list of parts directly from the 'Parts' key. Extract this list: `parts = cached_data.get('SearchResults', {}).get('Parts', [])`.
        *   Return `parts` if it's not empty, otherwise return an empty list `[]`.
3.  **API Call & Cache Write:**
    *   If `cached_data` *is* `None`, proceed with the existing logic for the API call.
    *   Inside the `try` block for `requests.post`:
        *   After a successful response (`response.status_code == 200`) and *before* parsing:
            *   Get the raw JSON: `raw_response_data = response.json()`.
            *   Check for API-level errors (`'Errors'` key).
            *   If **no** API-level errors: Call `cache_manager.cache_response(search_term=keyword, search_type='keyword', response_data=raw_response_data, db=db)`. Handle potential exceptions gracefully.
        *   **Important:** Continue the existing logic to parse `raw_response_data`: extract the `parts` list (`raw_response_data.get('SearchResults', {}).get('Parts', [])`) and return it (or `[]`). Ensure this parsing logic is the same as for the cache hit path.
4.  Maintain existing error handling. Only cache successful responses without API-level errors.
```

---

### Step 8: Wire Dependencies in API Endpoints

**Context:** Update the API endpoints that use the Mouser search functions to provide the database session and the cache manager instance. This requires identifying the relevant endpoint file(s) first.

**LLM Prompt:**

```text
1.  **Identify:** Locate the Python file(s) containing the FastAPI endpoints that call `search_mouser_by_mpn` or `search_mouser_by_keyword`. Let's assume it's `pcb_part_finder/api/main.py` for this example.
2.  **Import necessary modules:** In `pcb_part_finder/api/main.py`, ensure these imports are present:
    *   `from sqlalchemy.orm import Session`
    *   `from fastapi import Depends, FastAPI, HTTPException` (or APIRouter)
    *   `from pcb_part_finder.core.database import get_db`
    *   `from pcb_part_finder.core.mouser_api import search_mouser_by_mpn, search_mouser_by_keyword, MouserApiError`
    *   `from pcb_part_finder.core.cache_manager import MouserApiCacheManager`
3.  **Instantiate Cache Manager:** Create a module-level instance of the cache manager near the top of the file (after imports):
    `mouser_cache_manager = MouserApiCacheManager()`
4.  **Modify Endpoints:** For *each* endpoint function that calls either `search_mouser_by_mpn` or `search_mouser_by_keyword`:
    *   Add `db: Session = Depends(get_db)` to its parameters if not already present.
    *   Update the call to the Mouser search function (e.g., `search_mouser_by_mpn(...)`) to pass the required `cache_manager` and `db` arguments:
        *   `result = search_mouser_by_mpn(mpn=..., cache_manager=mouser_cache_manager, db=db)`
        *   `results = search_mouser_by_keyword(keyword=..., records=..., cache_manager=mouser_cache_manager, db=db)`
5.  Ensure error handling in the endpoint (e.g., catching `MouserApiError` and raising `HTTPException`) remains appropriate.
```

---

This step-by-step approach with corresponding prompts provides a clear path to implement the caching feature incrementally, integrating each piece before moving to the next.
