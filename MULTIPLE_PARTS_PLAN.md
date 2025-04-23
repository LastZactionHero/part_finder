Okay, understood. We'll remove the specific prompts and guidance related to writing unit tests and integration tests for now, focusing on the core implementation steps. Manual testing guidance will remain important.

Here is the revised blueprint and set of LLM prompts, omitting the detailed unit/integration test descriptions:

## High-Level Blueprint: Displaying 5 Potential Parts

1.  **Database Layer:** Define and implement the new table (`potential_bom_matches`) to store the 5 potential matches per BOM item, including rank, MPN, reason, and selection state. Create necessary CRUD functions.
2.  **LLM Layer:** Modify the LLM evaluation prompt to request 5 diverse candidates in JSON format. Implement a parser for this JSON response.
3.  **Core Processing Layer:** Adapt the `_process_single_bom_item` worker function to use the updated LLM interaction, look up details for each potential MPN via the Mouser API, and save the results to the new database table using the CRUD functions.
4.  **API Layer:** Update the API schemas (`PotentialMatch`, `MatchedComponent`) to include the potential matches. Modify the `GET /project/{project_id}` endpoint to fetch potential matches from the database, retrieve associated component details, populate the response schema, and send it to the frontend.
5.  **Frontend Layer:** Modify the JavaScript table rendering logic to display the primary BOM item row followed by styled secondary rows for each potential match, pulling data from the updated API response. Update CSS for styling. Perform manual UI testing.

## Iterative Breakdown and LLM Prompts

---

### Chunk 1: Database Foundation

**Goal:** Establish the database structure and access functions for storing potential matches.

**Prompt 1.1: Define SQLAlchemy Model**

```text
Modify init.sql to include the new tables and fields. Don't worry about migrations
Modify the file `pcb_part_finder/db/models.py`.
Define a new SQLAlchemy model class named `PotentialBomMatch`.
It should map to a table named `potential_bom_matches`.
Include the following columns based on the existing `Base`:
- `potential_match_id`: Integer, primary key, autoincrement.
- `bom_item_id`: Integer, ForeignKey referencing `bom_items.bom_item_id`, nullable=False, add an index.
- `rank`: Integer, nullable=False (representing 1-5).
- `manufacturer_part_number`: String(255), nullable=False (the suggested MPN).
- `reason`: Text, nullable=True (the LLM's justification).
- `selection_state`: String(50), nullable=False, default='proposed'.
- `created_at`: TIMESTAMP, default=datetime.datetime.utcnow.

Add an appropriate relationship back to the `BomItem` model (e.g., `bom_item = relationship("BomItem", back_populates="potential_matches")`). Also, update the `BomItem` model in the same file to include the corresponding `potential_matches = relationship("PotentialBomMatch", back_populates="bom_item")`. Ensure necessary imports (`Column`, `Integer`, `String`, `Text`, `TIMESTAMP`, `ForeignKey`, `Index`, `relationship`, `datetime`) are present.
```

**Prompt 1.2: Generate DB Migration (Manual Step Indication)**

```text
Note: This step typically requires manual intervention using a migration tool like Alembic. The prompt assumes Alembic is configured for the project.

Indicate that a database migration script needs to be generated based on the new `PotentialBomMatch` model defined in `pcb_part_finder/db/models.py`. The developer should run the appropriate Alembic command (e.g., `alembic revision --autogenerate -m "Add potential_bom_matches table"` and then `alembic upgrade head`) to apply the changes to the database schema. This prompt serves as a placeholder/reminder in the workflow.
```

**Prompt 1.3: Create CRUD Functions**

```text
Modify the file `pcb_part_finder/db/crud.py`.
1.  Import the `PotentialBomMatch` model.
2.  Create a new function `create_potential_bom_match`.
    -   Accepts `db: Session`, `bom_item_id: int`, `rank: int`, `mpn: str`, `reason: Optional[str]`, `selection_state: str = 'proposed'`.
    -   Creates an instance of the new `PotentialBomMatch` model with the provided data.
    -   Adds the instance to the session `db`.
    -   Does NOT commit the session (to allow batching).
    -   Returns the created `PotentialBomMatch` instance.
    -   Include necessary imports (`Session`, `PotentialBomMatch`, `Optional`).
3.  Create a new function `get_potential_matches_for_bom_item`.
    -   Accepts `db: Session`, `bom_item_id: int`.
    -   Queries the database for all `PotentialBomMatch` records where `bom_item_id` matches the input.
    -   Orders the results by `rank` (ascending).
    -   Returns a list of `PotentialBomMatch` instances.
```

---

### Chunk 2: LLM Interaction Update

**Goal:** Modify the LLM prompt and create a parser for the new JSON response format.

**Prompt 2.1: Modify LLM Evaluation Prompt**

```text
Modify the function `format_evaluation_prompt` in `pcb_part_finder/core/llm_handler.py`.
Change the core instruction: Instead of asking for the single best part, instruct the LLM to:
-   Select the top 5 most suitable and diverse candidate parts from the provided Mouser Search Results.
-   Consider the original part details, project context (name, notes), the full BOM list, and factors like availability, cost, specs (tolerance, package), and manufacturer reputation.
-   Aim for diversity in the suggestions (e.g., include low-cost, high-availability, high-spec options). Rank them from 1 (best) to 5.
-   Return the result ONLY as a valid JSON list of objects. Each object should have two keys: "mpn" (containing the exact Manufacturer Part Number from the search results) and "reason" (containing a brief justification for selecting that part, max 1-2 sentences).
-   Provide a clear example of the expected JSON output format within the prompt itself, like: ```json\n[\n  {\"mpn\": \"MPN_ABC\", \"reason\": \"Lowest cost option\"},\n  {\"mpn\": \"MPN_DEF\", \"reason\": \"Best availability\"},\n  ...\n]\n```
-   Update the function's docstring to reflect the new behavior and JSON output format. Ensure the function signature still accepts necessary arguments like `part_info`, `project_name`, `project_notes`, `bom_list`, `mouser_results`.
```

**Prompt 2.2: Create LLM Response Parser**

```text
Modify the file `pcb_part_finder/core/llm_handler.py`.
1.  Import necessary modules (`json`, `logging`, `List`, `Dict`, `Optional`). Add `LlmApiError` if a custom parsing error is desired.
2.  Create a new function `parse_potential_matches_json`.
    -   Accepts `llm_response: Optional[str]`.
    -   If `llm_response` is None or empty, log a warning and return an empty list `[]`.
    -   Attempt to parse the input string as JSON using `json.loads()`. Handle potential `json.JSONDecodeError`. If parsing fails, log an error and return `[]`.
    -   Validate that the parsed result `data` is a list (`isinstance(data, list)`). If not, log an error and return `[]`.
    -   Iterate through the items in the `data` list. For each `item`:
        -   Validate that `item` is a dictionary (`isinstance(item, dict)`).
        -   Validate that the dictionary contains both 'mpn' and 'reason' keys, and their values are strings (`isinstance(item.get('mpn'), str)` and `isinstance(item.get('reason'), str)`).
        -   If any validation fails for an item, log a warning for that specific item and skip it (do not include it in the final result).
    -   Return the list containing only the validated dictionary items (`List[Dict[str, str]]`).
3.  Remove or comment out the old `extract_mpn_from_eval` function.
```

---

### Chunk 3: Core Processor Logic Adaptation

**Goal:** Modify the worker function to use the new LLM interaction, fetch details for potential parts, and save them to the new DB table.

**Prompt 3.1: Update Worker Function - LLM Call**

```text
Modify the function `_process_single_bom_item` in `pcb_part_finder/core/processor.py`.
1.  Import the new CRUD function: `from pcb_part_finder.db.crud import create_potential_bom_match`. Also import `SQLAlchemyError` from `sqlalchemy.exc`.
2.  Locate the section handling LLM evaluation (Step 4).
3.  Replace the call to `llm_handler.extract_mpn_from_eval` with a call to `llm_handler.parse_potential_matches_json`, passing the `llm_response_eval`. Store the result in `potential_matches_list`.
4.  Update the associated logging and status setting. If `potential_matches_list` is empty after parsing, set status to `'evaluation_failed'` (or a similar appropriate status) and proceed towards the end of the function (skipping the save attempt).
5.  Remove the old logic related to `chosen_mpn` and looking up/creating a single component (Old Step 5).
```

**Prompt 3.2: Update Worker Function - Process Potential Matches**

```text
Continuing modifications in `_process_single_bom_item` in `pcb_part_finder/core/processor.py`:
1.  After successfully obtaining a non-empty `potential_matches_list` (i.e., add an `if potential_matches_list:` check):
    -   Initialize a variable `saved_matches_count = 0`.
    -   Start a `for` loop using `enumerate(potential_matches_list, start=1)` to get both `rank` and `potential_match` (the dict `{'mpn': ..., 'reason': ...}`).
2.  Inside the loop:
    -   Extract `mpn = potential_match.get('mpn')` and `reason = potential_match.get('reason')`.
    -   Check if `mpn` is valid (not None or empty string). If not, continue to the next iteration.
    -   Call `crud.create_potential_bom_match`, passing `db`, `bom_item.bom_item_id`, `rank`, `mpn`, and `reason`. Wrap this call in a try-except block specifically for potential errors during *this single match creation* (though `create_potential_bom_match` itself doesn't commit). If an error occurs here (unlikely unless data is invalid), log it but continue the loop.
    -   If the call was successful (no exception), increment `saved_matches_count`.
3.  *After* the loop finishes, check if `saved_matches_count > 0`.
4.  If `saved_matches_count > 0`, attempt to commit the session:
    -   Wrap `db.commit()` in a `try...except SQLAlchemyError as db_err:`.
    -   On success, set `status = 'potential_matches_saved'`.
    -   On exception (`db_err`), log the error, call `db.rollback()`, and set `status = 'db_save_error'`.
5.  If `saved_matches_count` was 0 (even if `potential_matches_list` was not empty initially, e.g., all MPNs were invalid), set an appropriate status like `'no_valid_matches_processed'`.
6.  Remove the old Step 6 logic that created a single `BomItemMatch` record.
7.  Review all status assignment points (`status = '...'`) throughout the function to ensure they reflect the new logic (search term failure, keyword results failure, LLM error, evaluation failure, processing error, DB save error, success). Ensure a status is assigned in all code paths before the function returns.
```

---

### Chunk 4: API Layer Integration

**Goal:** Update the API schema and endpoint to fetch and return the potential matches.

**Prompt 4.1: Define PotentialMatch API Schema**

```text
Modify the file `pcb_part_finder/api/schemas.py`.
1.  Import `List`, `Optional`, `Dict`, `Any` from `typing` and `Field` from `pydantic`.
2.  Define a new Pydantic `BaseModel` named `PotentialMatch`.
3.  Include the following fields with descriptions using `Field()`:
    -   `rank: int` = Field(..., description="Rank assigned by LLM (1-5)")
    -   `manufacturer_part_number: str` = Field(..., description="Suggested Manufacturer Part Number")
    -   `reason: Optional[str]` = Field(None, description="LLM's reason for suggesting this part")
    -   `selection_state: str` = Field(..., description="Current state (proposed, selected, rejected)")
    -   `mouser_part_number: Optional[str]` = Field(None, description="Corresponding Mouser Part Number if found")
    -   `manufacturer_name: Optional[str]` = Field(None, description="Manufacturer Name")
    -   `mouser_description: Optional[str]` = Field(None, description="Mouser's description")
    -   `datasheet_url: Optional[str]` = Field(None, description="Datasheet URL")
    -   `price: Optional[float]` = Field(None, description="Unit price")
    -   `availability: Optional[str]` = Field(None, description="Availability information")
    -   `component_id: Optional[int]` = Field(None, description="Internal component DB ID, if applicable")
```

**Prompt 4.2: Update MatchedComponent API Schema**

```text
Modify the file `pcb_part_finder/api/schemas.py`.
1.  Locate the `MatchedComponent(BOMComponent)` schema.
2.  Import `PotentialMatch` and `List`, `Optional` from `typing` if not already present.
3.  Add a new field: `potential_matches: Optional[List[PotentialMatch]] = Field(None, description="List of potential matches suggested by the LLM")`.
4.  Review the existing fields directly on `MatchedComponent` (e.g., `mouser_part_number`, `manufacturer_part_number`, etc.). Mark them as `Optional` and update their descriptions to clarify they might represent a *final selected* part in future iterations (e.g., "Mouser part number *of the final selected component, if any*"). Keep `match_status` to reflect the status of finding potential matches for the parent BOM item (e.g., use the status returned by `_process_single_bom_item`).
```

**Prompt 4.3: Modify API Endpoint - Fetch Potential Matches**

```text
Modify the `get_project` endpoint function in `pcb_part_finder/api/projects.py`.
1.  Import the necessary CRUD functions and schemas: `from ..db.crud import get_potential_matches_for_bom_item, get_component_by_mpn` and `from ..schemas import PotentialMatch`.
2.  Locate the section handling the `'finished'` project status (and potentially the `'processing'` status if partial results should be shown there too).
3.  Inside the loop `for db_bom_item, db_match, db_component in results_data:` (Note: `db_match` and `db_component` might be less relevant now for the primary display but could still indicate old single matches or the status).
4.  After creating the base `component_dict` for the original BOM item:
    ```python
    # Fetch potential matches from the new table
    db_potential_matches = get_potential_matches_for_bom_item(db=db, bom_item_id=db_bom_item.bom_item_id)
    potential_matches_for_api = []
    if db_potential_matches:
        # (Logic from next prompt goes here)

    # Add the list (even if empty) to the dict for the original BOM item
    component_dict['potential_matches'] = potential_matches_for_api

    # Update the main match_status for the BOM item based on processing outcome
    # Find the status from the potential_bom_matches table if needed, or use db_match if it reflects the worker status
    # For now, let's assume db_match still holds the overall status from the worker.
    if db_match:
         component_dict["match_status"] = db_match.match_status
    else:
         # If no db_match record exists (shouldn't happen if worker ran), set a default
         component_dict["match_status"] = "processing_error" # Or a more specific status

    ```
5.  Remove or adapt the logic that previously populated the `component_dict` directly with `db_component` details, as those details now belong inside the `potential_matches` list items. Keep the original BOM item details (`qty`, `description`, `package`, `possible_mpn`).
```

**Prompt 4.4: Modify API Endpoint - Populate Potential Match Details**

```text
Continuing modifications in the `get_project` endpoint function in `pcb_part_finder/api/projects.py`, inside the `if db_potential_matches:` block added in the previous step:
1.  Start a loop: `for db_potential in db_potential_matches:`.
2.  Inside this loop:
    -   Initialize `potential_details = {}`.
    -   Try to find the corresponding component details in the `components` table: `linked_component = get_component_by_mpn(db, db_potential.manufacturer_part_number)`.
    -   Populate `potential_details` with data from `db_potential` (`rank`, `manufacturer_part_number`, `reason`, `selection_state`).
    -   If `linked_component` is found:
        -   Populate `potential_details['component_id'] = linked_component.component_id`
        -   Populate `potential_details['mouser_part_number'] = linked_component.mouser_part_number`
        -   Populate `potential_details['manufacturer_name'] = linked_component.manufacturer_name`
        -   Populate `potential_details['mouser_description'] = linked_component.description` # Map description field
        -   Populate `potential_details['datasheet_url'] = linked_component.datasheet_url`
        -   Populate `potential_details['price'] = float(linked_component.price) if linked_component.price is not None else None` # Convert Decimal
        -   Populate `potential_details['availability'] = linked_component.availability`
    -   Create a `PotentialMatch` Pydantic object using `potential_details`: `api_potential_match = PotentialMatch(**potential_details)`. Use `.model_validate()` if using Pydantic v2: `api_potential_match = PotentialMatch.model_validate(potential_details)`.
    -   Append `api_potential_match` to the `potential_matches_for_api` list.
3.  Ensure this loop correctly populates the `potential_matches_for_api` list. Fields in `PotentialMatch` are Optional, so missing `linked_component` details will result in `None` values in the API response, which is acceptable.
```

---

### Chunk 5: Frontend Display

**Goal:** Update the UI table to display the original BOM item row followed by rows for potential matches.

**Prompt 5.1: Modify JS - Handle Potential Matches List**

```text
Modify the `updateResultsTable` function in `pcb_part_finder/web/static/script.js`.
1.  Inside the main loop (`components.forEach(component => { ... })`):
    -   First, create and populate the primary row (`const row = resultsTable.insertRow();`) for the *original* BOM item (`component.qty`, `component.description`, etc.). Decide how to populate columns like 'Mouser Part', 'Manufacturer', 'Price', 'Availability', 'URL' for this primary row - perhaps leave them blank or display original `component.possible_mpn` / `component.package`. Populate the 'Status' cell with `component.match_status` (e.g., 'potential_matches_saved', 'evaluation_failed'). Apply appropriate status classes to this cell.
2.  After creating the primary row, add a check for the potential matches list: `if (component.potential_matches && Array.isArray(component.potential_matches) && component.potential_matches.length > 0) { ... }`.
3.  Inside this `if` block, start a nested loop: `component.potential_matches.forEach(potentialMatch => { ... });`.
```

**Prompt 5.2: Modify JS - Generate Secondary Rows**

```text
Continuing modifications inside the nested loop (`potential_matches.forEach(potentialMatch => { ... })`) within `updateResultsTable` in `pcb_part_finder/web/static/script.js`:
1.  Inside the loop, create a new table row: `const potentialRow = resultsTable.insertRow();`.
2.  Add a CSS class: `potentialRow.classList.add('potential-match-row');`. Add another class based on rank if desired: `potentialRow.classList.add('rank-' + potentialMatch.rank);`.
3.  Insert cells into `potentialRow` for all columns corresponding to the `<thead>`.
4.  Populate the cells using data from `potentialMatch`:
    -   Leave the first cell (Qty) blank or add rank: `potentialRow.insertCell().textContent = ' ';` or `'#' + potentialMatch.rank`.
    -   Populate Description/Reason cell: Use `potentialMatch.reason || ''`. Add appropriate styling/indentation via CSS.
    -   Populate Mouser Part cell: Use `potentialMatch.mouser_part_number`. Create a link to Mouser if available.
    -   Populate Manufacturer cell: Use `potentialMatch.manufacturer_name`.
    -   Populate Status cell: Display `potentialMatch.selection_state`. Apply status-based CSS classes (e.g., `status-proposed`).
    -   Populate Price cell: Format `potentialMatch.price`.
    -   Populate Availability cell: Use `potentialMatch.availability`.
    -   Populate URL cell: Create link to datasheet (`potentialMatch.datasheet_url`) or Mouser page using `potentialMatch.mouser_part_number`.
5.  Ensure `|| 'N/A'` or similar fallbacks are used for optional fields.
```

**Prompt 5.3: Update HTML Table Headers**

```text
Modify the `<thead>` section of the table with `id="resultsTable"` in `pcb_part_finder/web/templates/index.html`.
Review the existing headers: Qty, Description, Mouser Part, Manufacturer, Status, Price, Availability, URL.
Update them to better reflect the new structure. Suggested headers:
`<th>Qty</th>`
`<th>Description / Reason</th>`
`<th>Mouser Part</th>`
`<th>Manufacturer</th>`
`<th>Selection State</th>` `<th>Price</th>`
`<th>Availability</th>`
`<th>URL</th>`
Update the `<th>` elements accordingly.
```

**Prompt 5.4: Define CSS Styles**

```text
Modify the file `pcb_part_finder/web/static/style.css`.
1.  Add a new CSS rule for `.potential-match-row`.
2.  Define styles:
    -   `background-color: #2f2f2f;` (Or another subtle shade distinct from main rows/card background).
    -   Maybe slightly smaller font: `font-size: 0.95em;`
3.  Add styles for specific cells if needed (e.g., indenting the reason column if it's combined with Description): `.potential-match-row td:nth-child(2) { padding-left: 30px; font-style: italic; color: var(--text-secondary); }` (Adjust child index based on final column order).
4.  Add or ensure styles exist for selection states, e.g.: `.status-proposed { color: #ffc107; /* Amber */ }`, `.status-selected { color: var(--success-color); font-weight: bold; }`, `.status-rejected { color: #dc3545; /* Red */ text-decoration: line-through; }`. Update the status class names applied in the JS if necessary.
```