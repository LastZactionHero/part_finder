
Okay, let's architect this refactoring process.

**Blueprint: Refactoring `queue.py` from Filesystem to Database**

1.  **Goal:** Transition the project processing queue (`pcb_part_finder/core/queue.py`) from a filesystem-based approach (monitoring `projects/queue` for directories containing CSVs) to a database-driven approach. The queue processor will query a `projects` table (managed by the already refactored API) for projects with a specific status (e.g., 'queued'), process them, and update their status and results in the database.
2.  **Current State:**
    *   API (`pcb_part_finder/api`) interacts with a database (schema defined in `init.sql`) for project creation, status tracking, and storing BOM data (`projects`, `bom_items`, `components`, `bom_item_matches` tables).
    *   Queue Processor (`pcb_part_finder/core/queue.py`) monitors `projects/queue/`, validates `initial_bom.csv` and `project_details.txt`, calls a core processing function (currently commented out, was passed CSV paths), moves processed projects to `projects/finished/`, and writes `results.json`.
    *   Core processing logic (invoked by `queue.py`, likely involving `data_loader.py`, `llm_handler.py`, `mouser_api.py`, `output_writer.py`) expects input/output via CSV files.
3.  **Target State:**
    *   `queue.py` queries the `projects` table for `project_id`s with `status='queued'`.
    *   Upon finding a project, `queue.py` updates its status to `status='processing'` and records `start_time`.
    *   `queue.py` invokes a core processing function, passing the `project_id`.
    *   The core processing function uses the `project_id` to fetch input data (BOM items, project details) from the database (likely via refactored `data_loader` or new DB access functions).
    *   The core processing function (including `llm_handler`, `mouser_api`) performs its tasks. Any internal CSV *formatting* for LLMs remains in-memory, not using files.
    *   The core processing function writes results (matched components, potentially updated BOM item details) back to the database (likely via refactored `output_writer` or new DB access functions).
    *   Upon completion (success or failure) of the core processing function, `queue.py` updates the project's status (`status='complete'` or `status='failed'`) and records `end_time` in the database.
    *   Filesystem operations (`projects/queue`, `projects/finished`, `initial_bom.csv`, `bom_matched.csv`, `results.json`) are removed from `queue.py` and related core logic.
4.  **Key Components Involved:**
    *   `pcb_part_finder/core/queue.py` (Main focus)
    *   `pcb_part_finder/core/data_loader.py` (Needs DB reading logic)
    *   `pcb_part_finder/core/output_writer.py` (Needs DB writing logic)
    *   `pcb_part_finder/core/llm_handler.py` (Ensure no file I/O)
    *   A new or existing module for shared database access logic/models (possibly leveraging code from `pcb_part_finder/api`).
    *   The core processing function itself (needs interface change: `project_id` instead of file paths).

**Iterative Steps & Refined Plan:**

*   **Phase 1: Database Foundation & Queue Polling**
    *   **Step 1.1:** Establish DB Connection & Model Access in `core`. Make DB configuration (e.g., connection string) available to the `core` module (likely via environment variables, mirroring the API setup). Ensure necessary SQLAlchemy models (Project, BomItem, etc.) and session management utilities from the API/shared location are importable and usable within `core`. Write a basic test confirming connection.
    *   **Step 1.2:** Refactor `get_next_project` in `queue.py`. Replace filesystem directory scanning with a database query to find one `project_id` where `status='queued'`, ordered by `created_at`. Return the `project_id` or `None`. Write unit tests mocking the DB query.
    *   **Step 1.3:** Implement Project Status Update (Start). In `queue.py`'s main loop, after successfully getting a `project_id` from `get_next_project`, update that project's record in the database: set `status='processing'` and `start_time=datetime.now()`. Write unit tests mocking the DB update.

*   **Phase 2: Core Processing Interface & Data Flow**
    *   **Step 2.1:** Define and Call New Core Processing Function. Create a new function signature, e.g., `process_project_from_db(project_id: str, db_session: Session) -> bool:`, within the appropriate core module (maybe a new `processor.py` or refactoring the old entry point). This function will contain the main logic. Modify `queue.py` to call this function, passing the `project_id` and a DB session. Initially, this function can be a stub that just logs the `project_id` and returns `True`. Test that `queue.py` calls this function correctly.
    *   **Step 2.2:** Implement Data Loading from DB. Refactor `data_loader.py` or add functions callable by `process_project_from_db` to fetch the project details and the list of `BomItem` objects associated with the given `project_id` from the database. Write unit tests mocking DB queries.
    *   **Step 2.3:** Adapt LLM Handler (If Necessary). Review `llm_handler.py`. Ensure it takes structured data (like lists of `BomItem` objects or dictionaries) as input, performs any necessary internal formatting (e.g., to a CSV-like string *in memory* if required by the LLM prompt structure), processes the LLM call, and returns structured data. Remove any residual file read/write operations. Write unit tests for its data transformation logic.
    *   **Step 2.4:** Implement Data Writing to DB. Refactor `output_writer.py` or add functions callable by `process_project_from_db` to save the results. This involves creating/updating `bom_item_matches` records and potentially updating fields in the original `bom_items` records based on the processing outcome. Write unit tests mocking DB writes.

*   **Phase 3: Completion & Cleanup**
    *   **Step 3.1:** Implement Project Status Update (End). Modify the `try...except` block in `queue.py` that calls `process_project_from_db`. On successful return, update the project status to `'complete'`. On exception, update the status to `'failed'`. In both cases, set the `end_time`. Write unit tests mocking the DB updates for both success and failure scenarios.
    *   **Step 3.2:** Remove Filesystem Logic from `queue.py`. Delete the `validate_project_files` function. Remove all code related to `Path` objects for queue/finished directories, `shutil.move`, `results.json` creation, and the `sys.argv` manipulation used to call the old processing function. Clean up unused imports.
    *   **Step 3.3:** Remove Filesystem Logic from Core Processing. Ensure `data_loader.py`, `output_writer.py`, and the main `process_project_from_db` function no longer reference or expect `initial_bom.csv` or `bom_matched.csv` file paths or perform file I/O for the main data flow.
    *   **Step 3.4:** Integration Test. Perform an end-to-end test: Create a project via the API (which should set status to 'queued'). Run the `queue.py` worker. Observe logs and verify in the database that the project status transitions correctly (`queued` -> `processing` -> `complete`/`failed`), timestamps are set, and results (e.g., `bom_item_matches`) are populated.

---

**LLM Prompts for Implementation:**

**Context:** We are refactoring the `pcb_part_finder/core/queue.py` script and related core modules (`data_loader.py`, `output_writer.py`, etc.) to use a database for project queuing and data handling, instead of the current filesystem/CSV-based approach. The API (`pcb_part_finder/api`) already handles database interactions and defines SQLAlchemy models (`Project`, `BomItem`, etc.) and potentially session management. Assume database connection details are available via environment variables (e.g., `DATABASE_URL`).

---

**Prompt 1: Setup Database Access in Core**

```text
Goal: Enable database access within the `pcb_part_finder.core` module using the same settings and models as the `pcb_part_finder.api` module.

Task:
1.  Create a new file `pcb_part_finder/core/database.py`.
2.  In `database.py`, set up SQLAlchemy core components (engine, SessionLocal) using the `DATABASE_URL` environment variable. This setup should mirror the database setup in the API module (look for how the engine and SessionLocal are created there, likely in `api/database.py` or similar).
3.  Define a dependency function `get_db()` in `database.py` that yields a database session and ensures it's closed afterwards, similar to how it's likely done for FastAPI dependencies in the API.
4.  Ensure necessary SQLAlchemy models (e.g., `Project`, `BomItem` from `api.models` or a shared `models.py`) can be imported and are recognized by the engine/session (e.g., via `Base.metadata.create_all(bind=engine)` if necessary, though table creation might be handled elsewhere).
5.  Add basic configuration loading (e.g., using `python-dotenv`) to load `.env` files if present.
6.  In `pcb_part_finder/core/__init__.py`, ensure the core modules can access the components defined in `pcb_part_finder.core.database`.

Context Files:
- `pcb_part_finder/api/database.py` (or similar, for reference)
- `pcb_part_finder/api/models.py` (or similar, for models)
- `init.sql` (for table structure reference)
- `.env` (example, for `DATABASE_URL`)
```

---

**Prompt 2: Refactor `get_next_project` to Query Database**

```text
Goal: Modify `queue.py` to find the next project to process by querying the database instead of scanning the filesystem.

Task:
1.  Import necessary components from `core.database` (e.g., `SessionLocal`, models like `Project`) into `pcb_part_finder/core/queue.py`.
2.  Rewrite the `get_next_project()` function in `queue.py`.
3.  Inside `get_next_project()`, acquire a database session (e.g., using `SessionLocal()`).
4.  Query the `projects` table for one project where the `status` column is equal to 'queued'. Order the results by `created_at` ascending and take the first result (`.first()`).
5.  If a project is found, return its `project_id`.
6.  If no project is found, return `None`.
7.  Ensure the database session is closed properly (e.g., using a `try...finally` block or context manager if not handled by a dependency injector).
8.  Remove the old filesystem scanning logic (using `Path`, `iterdir`, `sorted`) from `get_next_project`.

Context Files:
- `pcb_part_finder/core/queue.py`
- `pcb_part_finder/core/database.py` (created in Prompt 1)
- `pcb_part_finder/api/models.py` (or shared models file)
```

---

**Prompt 3: Update Project Status to 'Processing'**

```text
Goal: When `queue.py` successfully finds a project ID, update its status to 'processing' and set the `start_time` in the database before attempting to process it.

Task:
1.  In the main `process_queue()` loop within `pcb_part_finder/core/queue.py`, immediately after `project_name = get_next_project()` returns a valid project ID (i.e., not `None`):
    a. Acquire a new database session.
    b. Query the `projects` table to fetch the project object corresponding to `project_name` (which is the `project_id`).
    c. If the project is found:
        i. Set its `status` attribute to 'processing'.
        ii. Set its `start_time` attribute to `datetime.now()`.
        iii. Commit the session.
        iv. Log an info message indicating the project is now being processed.
    d. If the project is *not* found (edge case, shouldn't happen if `get_next_project` worked but good to handle), log an error and continue the loop.
    e. Ensure the session is closed properly.
2.  Keep the rest of the loop structure (the `try...except` block for actual processing) for now, but ensure the status update happens *before* entering the main processing logic.
3.  Remove the `validate_project_files` function and its call, as file validation is no longer relevant.
4.  Remove the filesystem path setup code (`queue_path = ...`, `finished_path = ...`).


Context Files:
- `pcb_part_finder/core/queue.py`
- `pcb_part_finder/core/database.py`
- `pcb_part_finder/api/models.py` (or shared models file)
```

---

**Prompt 4: Define and Call New Core Processing Function**

```text
Goal: Define a new function signature for the core project processing logic that accepts a `project_id` and a DB session. Modify `queue.py` to call this new function instead of manipulating `sys.argv`.

Task:
1.  Create a new file `pcb_part_finder/core/processor.py`.
2.  In `processor.py`, define a function `process_project_from_db(project_id: str, db: Session) -> bool:`. Import `Session` from `sqlalchemy.orm`.
3.  For now, implement `process_project_from_db` as a stub:
    - Log an INFO message indicating it's processing `project_id`.
    - Include comments outlining the future steps: Load data, call LLM handler, call Mouser API, write results.
    - Return `True` (simulating successful processing for now).
4.  In `pcb_part_finder/core/queue.py`:
    - Import `process_project_from_db` from `core.processor`.
    - Import `SessionLocal` from `core.database`.
    - Inside the main `try` block of the `process_queue` loop (after the status has been updated to 'processing'), acquire a DB session.
    - Call `success = process_project_from_db(project_id=project_name, db=session)`.
    - Remove the commented-out `process_project()` call and the `sys.argv` manipulation code.
    - Store the boolean result (`success`) for later use in status updates (Prompt 3.1).
    - Ensure the session is closed properly after the call.

Context Files:
- `pcb_part_finder/core/queue.py`
- `pcb_part_finder/core/processor.py` (new)
- `pcb_part_finder/core/database.py`
- `pcb_part_finder/api/models.py` (or shared models file)
```

---

**Prompt 5: Implement Data Loading from Database**

```text
Goal: Implement the logic within `core.processor` (or refactor `core.data_loader`) to fetch project details and BOM items from the database using the `project_id`.

Task:
1.  Refactor or add functions in `pcb_part_finder/core/data_loader.py`. Alternatively, implement directly in `pcb_part_finder/core/processor.py` initially. Let's assume refactoring `data_loader.py`.
2.  Create a function `load_project_data_from_db(project_id: str, db: Session) -> Tuple[Project | None, List[BomItem]]`:
    - Takes `project_id` and `db` session as input.
    - Queries the database to fetch the `Project` object matching `project_id`.
    - Queries the database to fetch all `BomItem` objects where `project_id` matches the input `project_id`.
    - Returns the fetched `Project` object (or `None` if not found) and the list of `BomItem` objects.
3.  In `pcb_part_finder/core/processor.py`, modify `process_project_from_db`:
    - Import `load_project_data_from_db` from `core.data_loader`.
    - Call `project, bom_items = load_project_data_from_db(project_id, db)`.
    - Add error handling: If `project` is `None`, log an error and return `False`.
    - Log the loaded project name and the number of BOM items found.
    - Pass the `project` details (like description/notes) and `bom_items` list to subsequent processing steps (which are still stubs or need implementation).
4.  Remove any old CSV-reading functions from `data_loader.py` if they are no longer needed anywhere.
5.  Write unit tests for `load_project_data_from_db`:
    - Mock the DB session and queries.
    - Verify it correctly fetches and returns a `Project` and a list of `BomItem`s based on mock data.
    - Verify it returns `(None, [])` if the project query returns nothing.
6.  Update unit tests for `process_project_from_db` to mock `load_project_data_from_db` and verify it's called correctly.

Context Files:
- `pcb_part_finder/core/processor.py`
- `pcb_part_finder/core/data_loader.py`
- `pcb_part_finder/core/database.py`
- `pcb_part_finder/api/models.py` (or shared models file)
```

---

**Prompt 6: Adapt LLM Handler for Database Objects**

```text
Goal: Ensure the `llm_handler.py` can process `BomItem` objects loaded from the database, format them as needed for the LLM (potentially using an in-memory CSV-like string format), and parse the results back without using filesystem I/O.

Task:
1.  Review `pcb_part_finder/core/llm_handler.py`. Identify the main function(s) responsible for interacting with the LLM (e.g., `format_bom_for_llm`, `parse_llm_response`, `process_bom_with_llm`).
2.  Modify these functions to accept a list of `BomItem` objects (or relevant data derived from them) instead of reading from a file path or expecting a pre-formatted string from a file.
3.  If the LLM interaction relies on a specific string format (like CSV):
    - Implement the logic *within* the handler function to format the input `BomItem` data into this string format *in memory* (e.g., using `io.StringIO` and `csv.writer` if helpful, or simple string concatenation).
    - Ensure the LLM response parsing logic takes the LLM's string output and converts it back into structured data (e.g., dictionaries or updated `BomItem` fields).
4.  Remove any code within `llm_handler.py` that performs file read or write operations.
5.  In `pcb_part_finder/core/processor.py`, update the call to the LLM handler within `process_project_from_db`. Pass the loaded `bom_items` list (or relevant parts) to it. Capture the structured results.
6.  Write/update unit tests for the relevant functions in `llm_handler.py`:
    - Test the in-memory formatting logic with sample `BomItem` data.
    - Test the response parsing logic with sample LLM string outputs.
    - Ensure no file I/O is attempted.

Context Files:
- `pcb_part_finder/core/processor.py`
- `pcb_part_finder/core/llm_handler.py`
- `pcb_part_finder/api/models.py` (specifically `BomItem`)
```

---

**Prompt 7: Implement Data Writing to Database**

```text
Goal: Implement the logic to save the processing results (e.g., matched components from Mouser/LLM processing) back to the database, associating them with the original BOM items.

Task:
1.  Refactor or add functions in `pcb_part_finder/core/output_writer.py`. Alternatively, implement directly in `pcb_part_finder/core/processor.py`. Let's assume refactoring `output_writer.py`.
2.  Define database models if needed, e.g., ensure `BomItemMatch` and `Component` models exist and are accessible (they should be from `api/models.py`).
3.  Create a function `save_bom_results_to_db(project_id: str, bom_items_with_matches: List[Dict], db: Session)` (adjust input structure as needed based on preceding steps like LLM/Mouser output). This function should:
    - Iterate through the results.
    - For each result/match associated with an original `BomItem`:
        - Potentially find or create a `Component` record for the matched part (using Mouser PN, etc.). Handle potential uniqueness constraints.
        - Create a `BomItemMatch` record linking the `bom_item_id` (from the original `BomItem`) to the `component_id` of the matched component. Store relevant match details (status, confidence score, etc.) in this record.
        - Optionally, update the original `BomItem` record itself (e.g., setting a 'processed' flag or storing a primary match ID).
    - Commit the changes within the passed session `db`.
4.  In `pcb_part_finder/core/processor.py`, within `process_project_from_db`, after the LLM/Mouser processing steps yield results:
    - Call `save_bom_results_to_db`, passing the `project_id`, the processed results, and the `db` session.
5.  Remove any old CSV/JSON writing functions from `output_writer.py`.


Context Files:
- `pcb_part_finder/core/processor.py`
- `pcb_part_finder/core/output_writer.py`
- `pcb_part_finder/core/database.py`
- `pcb_part_finder/api/models.py` (or shared models file, especially `BomItem`, `Component`, `BomItemMatch`)
- `init.sql` (for table structure reference)
```

---

**Prompt 8: Update Final Project Status (Complete/Failed)**

```text
Goal: Update the project's status in the database to 'complete' or 'failed' and set the `end_time` in `queue.py` based on the outcome of the core processing function.

Task:
1.  In `pcb_part_finder/core/queue.py`, locate the `try...except...finally` block within the `process_queue` loop that calls `process_project_from_db`.
2.  Modify the logic *after* the call to `process_project_from_db`:
    a. Determine the final status: `'complete'` if the function returned `True` (or didn't raise an exception), `'failed'` if it returned `False` or an exception was caught.
    b. Acquire a database session.
    c. Query for the project object using `project_name` (the `project_id`).
    d. If found, update its `status` to the determined final status and set `end_time` to `datetime.now()`.
    e. Commit the session.
    f. Log the final status (completion or failure).
    g. Ensure the session is closed properly.
3.  Make sure the `Exception` handling logs the error appropriately.
4.  Remove the old `create_results_file` function and its call.
5.  Remove the old filesystem moving logic (`shutil.move`, `finished_path.mkdir`, `queue_path.rmdir`).


Context Files:
- `pcb_part_finder/core/queue.py`
- `pcb_part_finder/core/processor.py` (specifically its return value/exceptions)
- `pcb_part_finder/core/database.py`
- `pcb_part_finder/api/models.py` (or shared models file)
```

---

**Prompt 9: Final Cleanup and Integration Test Guidance**

```text
Goal: Perform final code cleanup, review, and prepare for integration testing.

Task:
1.  Review all modified files (`queue.py`, `processor.py`, `data_loader.py`, `output_writer.py`, `llm_handler.py`, `database.py`) for any remaining filesystem operations related to the old queue/CSV flow (e.g., `Path`, `shutil`, `os.path`, direct `open()` calls for project data CSVs/JSON). Remove any commented-out code related to the old flow.
2.  Ensure all necessary imports are present and unused imports are removed. Run a linter (like flake8 or ruff) and address any issues.
3.  Review logging messages across the modules to ensure they provide clear information about the queue polling, project processing stages, database interactions, and errors.
4.  Review the `Dockerfile.api`. Since the queue worker (`python -m pcb_part_finder queue`) no longer relies on the `projects/queue` and `projects/finished` directories for its core operation, consider if the `COPY projects/ projects/` line and the `RUN mkdir -p /app/projects/queue /app/projects/finished` lines are still necessary. *Decision: Keep them for now if the API might still use them for upload/download staging, but note they are not needed by `queue.py` itself.*


Context Files:
- All modified Python files in `pcb_part_finder/core/`
- `Dockerfile.api`
- `init.sql`
```
