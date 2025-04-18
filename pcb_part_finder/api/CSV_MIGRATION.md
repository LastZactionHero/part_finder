
Okay, let's build a detailed, iterative plan to migrate the FastAPI backend from CSV storage to a PostgreSQL database using SQLAlchemy.

**Project Goal:** Refactor the `pcb_part_finder` API service to use a PostgreSQL database via SQLAlchemy for storing and retrieving project and BOM data, replacing the current CSV file-based system. The external API contract (endpoints, request/response schemas) should remain unchanged.

**Core Technologies:** FastAPI, SQLAlchemy, PostgreSQL, Pydantic, Docker.

**High-Level Blueprint:**

1.  **Setup & Dependencies:** Integrate SQLAlchemy and database connection handling.
2.  **Database Models:** Define SQLAlchemy models corresponding to the `init.sql` schema.
3.  **CRUD Layer:** Create functions for database interactions (Create, Read, Update, Delete) to abstract database logic.
4.  **Endpoint Refactoring (Iterative):** Modify each API endpoint (`/project` POST, GET, DELETE, `/project/queue/length` GET) one by one to use the CRUD layer instead of filesystem/CSV operations.
5.  **Database State Management:** Ensure project `status` ('queued', 'processing', 'finished', 'error') is correctly managed in the database, enabling the (separate) background worker to function.
6.  **Cleanup:** Remove old filesystem code and configurations.

**Iterative Implementation Steps (Refined):**

*   **Phase 1: Foundation & Basic Read/Write**
    1.  **Step 1.1: Add Dependencies:** Update requirements for SQLAlchemy and the PostgreSQL driver.
    2.  **Step 1.2: Database Configuration & Session:** Set up SQLAlchemy engine, session factory, and a FastAPI dependency (`get_db`) to manage database sessions per request.
    3.  **Step 1.3: Define Core Models:** Create SQLAlchemy models for `Project` and `BomItem`.
    4.  **Step 1.4: Implement Core CRUD:** Create CRUD functions for creating `Project` and `BomItem` records, and retrieving a `Project` by ID.
    5.  **Step 1.5: Refactor `POST /project`:** Modify the project creation endpoint to use the new CRUD functions to save data to the database instead of CSV. Inject the DB session.
*   **Phase 2: Reading Queued & Basic Info**
    6.  **Step 2.1: Implement Queued Read CRUD:** Add CRUD functions to retrieve `BomItem`s for a given project and to get project status and queue information (count, position).
    7.  **Step 2.2: Refactor `GET /project/{project_id}` (Queued):** Modify the project retrieval endpoint to handle the 'queued' status by fetching data from the DB using CRUD functions. Inject the DB session.
    8.  **Step 2.3: Refactor `GET /project/queue/length`:** Modify the queue length endpoint to use a CRUD function querying the database. Inject the DB session.
*   **Phase 3: Handling Finished State & Deletion**
    9.  **Step 3.1: Define Matching Models:** Create SQLAlchemy models for `Component` and `BomItemMatch`.
    10. **Step 3.2: Implement Matching CRUD:** Create CRUD functions for finding/creating `Component`s and creating `BomItemMatch` records. Add CRUD function(s) to retrieve all data needed for a 'finished' project (joins likely needed). Add CRUD function to update project status (e.g., to 'cancelled' or 'deleted').
    11. **Step 3.3: Refactor `GET /project/{project_id}` (Finished):** Enhance the project retrieval endpoint to handle the 'finished' status, fetching enriched BOM data from the database using CRUD functions and reconstructing the `MatchedBOM`.
    12. **Step 3.4: Refactor `DELETE /project/{project_id}`:** Modify the project deletion endpoint to update the project status in the database (e.g., to 'cancelled') instead of removing files. Inject the DB session.
*   **Phase 4: Worker Integration & Cleanup**
    13. **Step 4.1: Worker Prerequisite CRUD:** Ensure necessary CRUD functions exist for the (separate) background worker: finding the next 'queued' project, updating status to 'processing', 'finished', or 'error', setting start/end times. (Note: Actual worker refactor is outside these prompts but relies on this).
    14. **Step 4.2: Final Code Cleanup:** Remove all unused filesystem/CSV-related code, imports (`pandas`, `Path`, `shutil`), helper functions (`bom_to_dataframe`, `dataframe_to_bom`, `read_project_details`), and constants (`PROJECTS_DIR`, etc.) from the API codebase.
    15. **Step 4.3: Configuration Cleanup:** Remove the `projects` volume mount from the `api` service in `docker-compose.yml`.

This breakdown provides small, logical steps, building database interaction incrementally into the existing API structure.

---

**LLM Prompts for Implementation:**

Below are the prompts designed to guide a code-generation LLM through the refactoring process, step-by-step.

**Prompt 1: Add Dependencies**
```text
Objective: Update the dependencies for the API service to include SQLAlchemy and the PostgreSQL driver.

Instructions:
1.  Modify the appropriate requirements file (e.g., `requirements.txt` or within a `pyproject.toml` if using Poetry) for the API service.
2.  Add `SQLAlchemy` (version 2.x recommended).
3.  Add `psycopg2-binary` (or `psycopg[binary]`) as the PostgreSQL database adapter.
4.  Optionally, add `alembic` for database migrations, although we won't implement migrations in these steps.
5.  Optionally, add `asyncpg` if planning for async database operations (we will assume synchronous operations for simplicity unless specified otherwise).

Context: This is the first step in migrating the FastAPI backend from CSV files to a PostgreSQL database. We need the necessary libraries to interact with the database using an ORM.
```

---

**Prompt 2: Database Configuration & Session Management**
```text
Objective: Set up SQLAlchemy database engine, session management, and a FastAPI dependency provider.

Instructions:
1.  Create a new directory `pcb_part_finder/db`.
2.  Create a new file `pcb_part_finder/db/session.py`.
3.  In `session.py`:
    *   Import necessary components from `sqlalchemy` (e.g., `create_engine`) and `sqlalchemy.orm` (e.g., `sessionmaker`, `Session`).
    *   Import `os` to read environment variables.
    *   Retrieve the `DATABASE_URL` from environment variables (provide a default or raise an error if not set, matching the `docker-compose.yml` setup: `postgresql://part_finder:part_finder@db:5432/part_finder`).
    *   Create the SQLAlchemy engine using `create_engine` with the `DATABASE_URL`.
    *   Create a `SessionLocal` factory using `sessionmaker`, bound to the engine, with `autocommit=False` and `autoflush=False`.
    *   Define a FastAPI dependency function `get_db()`:
        *   It should create a database session using `SessionLocal()`.
        *   It should `yield` the session.
        *   It must ensure the session is closed afterwards using a `finally` block (`db.close()`).

Context: This sets up the core connection to the database and provides a standard way (`get_db` dependency) to inject database sessions into our FastAPI path operation functions, ensuring proper session lifecycle management.
```

---

**Prompt 3: Define Core SQLAlchemy Models**
```text
Objective: Define SQLAlchemy ORM models for the `projects` and `bom_items` tables based on `init.sql`.

Instructions:
1.  Create a new file `pcb_part_finder/db/models.py`.
2.  In `models.py`:
    *   Import necessary components from `sqlalchemy` (e.g., `Column`, `Integer`, `String`, `Text`, `TIMESTAMP`, `ForeignKey`) and `sqlalchemy.orm` (e.g., `relationship`, `declarative_base`).
    *   Import `datetime`.
    *   Create a `Base = declarative_base()`.
    *   Define the `Project` class inheriting from `Base`:
        *   Set `__tablename__ = 'projects'`.
        *   Define columns matching `init.sql`: `project_id` (String, primary_key=True), `name` (String, nullable=True), `description` (Text, nullable=True), `email` (String, nullable=True), `created_at` (TIMESTAMP, default=datetime.datetime.utcnow), `status` (String), `start_time` (TIMESTAMP, nullable=True), `end_time` (TIMESTAMP, nullable=True).
        *   Add a relationship to `BomItem`: `bom_items = relationship("BomItem", back_populates="project", cascade="all, delete-orphan")`.
    *   Define the `BomItem` class inheriting from `Base`:
        *   Set `__tablename__ = 'bom_items'`.
        *   Define columns matching `init.sql`: `bom_item_id` (Integer, primary_key=True), `project_id` (String, ForeignKey('projects.project_id')), `quantity` (Integer), `description` (Text), `package` (String), `notes` (Text, nullable=True), `created_at` (TIMESTAMP, default=datetime.datetime.utcnow).
        *   Add a relationship back to `Project`: `project = relationship("Project", back_populates="bom_items")`.

Context: These models provide the Python object mapping to our database tables, allowing SQLAlchemy to translate between Python objects and database rows. The relationships define how projects and their BOM items are linked.
```

---

**Prompt 4: Implement Core CRUD Functions**
```text
Objective: Create basic Create and Read functions for the `Project` and `BomItem` models.

Instructions:
1.  Create a new file `pcb_part_finder/db/crud.py`.
2.  In `crud.py`:
    *   Import `Session` from `sqlalchemy.orm`.
    *   Import the `Project`, `BomItem` models from `.models`.
    *   Import the Pydantic `InputBOM`, `BOMComponent` schemas from `..schemas`. (We'll need `InputBOM` in the next step's refactor, but import related schemas here).
    *   Define `create_project(db: Session, project_id: str, description: str | None, status: str) -> Project`:
        *   Creates a `Project` model instance.
        *   Adds it to the session (`db.add()`).
        *   Commits the session (`db.commit()`).
        *   Refreshes the instance to get DB-generated values (`db.refresh()`).
        *   Returns the created `Project` instance.
    *   Define `create_bom_item(db: Session, item: BOMComponent, project_id: str) -> BomItem`:
        *   Creates a `BomItem` model instance from the Pydantic `item` data and `project_id`.
        *   Adds it to the session.
        *   Returns the created `BomItem` instance (Note: commit is usually done after adding all items for a project).
    *   Define `get_project_by_id(db: Session, project_id: str) -> Project | None`:
        *   Queries the database for a `Project` with the matching `project_id`.
        *   Returns the first result or `None`.

Context: This file will house all database interaction logic, keeping it separate from the API endpoint handlers. These initial functions cover creating new projects and their associated BOM items, and retrieving a specific project.
```

---

**Prompt 5: Refactor `POST /project` Endpoint**
```text
Objective: Modify the `create_project` endpoint in `api/projects.py` to use the database CRUD functions instead of CSV writing.

Instructions:
1.  Open `pcb_part_finder/api/projects.py`.
2.  Import `Session` from `sqlalchemy.orm` and `Depends` from `fastapi`.
3.  Import the `get_db` dependency from `..db.session`.
4.  Import the CRUD functions `create_project`, `create_bom_item` from `..db.crud`.
5.  Import the `Project` model from `..db.models` (optional, maybe not needed directly in endpoint).
6.  Modify the `create_project` async function:
    *   Add `db: Session = Depends(get_db)` as a parameter.
    *   Remove the `generate_project_id` function call and associated imports (`string`, `random`, `datetime` if only used there). Instead, generate a unique ID (e.g., using `uuid.uuid4()`). Import `uuid`.
    *   Remove the file/directory creation logic (`QUEUE_DIR`, `project_dir.mkdir`, `Path`).
    *   Remove the `bom_to_dataframe` function call and the function definition itself, along with the `pandas` import if no longer needed.
    *   Remove the `df.to_csv(...)` call.
    *   Remove the `project_details.txt` writing logic.
    *   **Instead:**
        *   Generate a `project_id` (e.g., `str(uuid.uuid4())`).
        *   Call `crud.create_project(db=db, project_id=project_id, description=bom.project_description, status='queued')`.
        *   Iterate through `bom.components`:
            *   For each `comp`, call `crud.create_bom_item(db=db, item=comp, project_id=project_id)`.
        *   After the loop, commit the transaction: `db.commit()`. You might need to catch potential exceptions during item creation and handle rollbacks (`db.rollback()`).
        *   Refresh the created project object if needed (e.g., `db.refresh(db_project)`) - though not strictly necessary if just returning the ID.
    *   Keep the truncation logic as is.
    *   Return the `project_id` and `truncation_info`.
    *   Remove unused imports like `Path`, `shutil`, `pd`, `string`, `random`.

Context: This is the first major refactor step, switching the creation path from filesystem operations to database persistence using the newly created DB layer. It introduces the `get_db` dependency injection pattern.
```

---

**Prompt 6: Implement Queued Read CRUD Functions**
```text
Objective: Add CRUD functions to retrieve BOM items for a project, get project status, and get queue information.

Instructions:
1.  Open `pcb_part_finder/db/crud.py`.
2.  Import `List` from `typing` and potentially `func` from `sqlalchemy` for count operations.
3.  Define `get_bom_items_for_project(db: Session, project_id: str) -> List[BomItem]`:
    *   Queries the `BomItem` table, filtering by `project_id`.
    *   Returns all matching `BomItem` instances.
4.  Define `get_project_status(db: Session, project_id: str) -> str | None`:
    *   Queries the `Project` table for the specific `project_id`.
    *   Returns the `status` column value if the project exists, otherwise `None`.
5.  Define `get_queue_info(db: Session, project_id: str) -> tuple[int, int]`:
    *   Query 1: Count all projects where `status == 'queued'`. This is the `total_in_queue`.
    *   Query 2: Count all projects where `status == 'queued'` AND `created_at <= (SELECT created_at FROM projects WHERE project_id = :project_id)`. This gives the `position`. Use subqueries or fetch the project's `created_at` first.
    *   Return `(position, total_in_queue)`. Handle the case where the project itself isn't found or isn't queued.
6.  Define `count_queued_projects(db: Session) -> int`:
    *   Queries the `Project` table and counts rows where `status == 'queued'`.
    *   Returns the count.

Context: These functions provide the necessary database operations to retrieve data for projects that are still in the 'queued' state and to get overall queue statistics.
```

---

**Prompt 7: Refactor `GET /project/{project_id}` (Queued Status)**
```text
Objective: Modify the `get_project` endpoint to handle 'queued' projects by fetching data from the database.

Instructions:
1.  Open `pcb_part_finder/api/projects.py`.
2.  Import `Depends` from `fastapi`, `Session` from `sqlalchemy.orm`, and the new CRUD functions (`get_project_by_id`, `get_bom_items_for_project`, `get_queue_info`) from `..db.crud`. Also import `InputBOM`, `BOMComponent` from `..schemas`.
3.  Import `get_db` from `..db.session`.
4.  Modify the `get_project` async function:
    *   Add `db: Session = Depends(get_db)` as a parameter.
    *   Remove the filesystem path checking (`QUEUE_DIR`, `FINISHED_DIR`, `queue_path.exists()`, `finished_path.exists()`).
    *   Remove the queue position calculation based on directory listing.
    *   Remove the `pd.read_csv` call for `initial_bom.csv`.
    *   Remove the `read_project_details` call and the function definition.
    *   Remove the `dataframe_to_bom` call and the function definition.
    *   **Instead:**
        *   Call `db_project = crud.get_project_by_id(db=db, project_id=project_id)`.
        *   If `db_project` is None, raise `HTTPException(status_code=404, detail="Project not found")`.
        *   Check `db_project.status`:
            *   **If `'queued'`:**
                *   Call `db_items = crud.get_bom_items_for_project(db=db, project_id=project_id)`.
                *   Call `position, total_in_queue = crud.get_queue_info(db=db, project_id=project_id)`.
                *   Reconstruct the `InputBOM` Pydantic model:
                    *   Create a list of `BOMComponent` objects by iterating through `db_items` and mapping the database model fields (qty, description, possible_mpn, package, notes) back to the Pydantic model fields. Remember `possible_mpn` and `notes` might be None in the DB, matching the Optional Pydantic fields. Package might need `str()` conversion if stored differently.
                    *   Instantiate `InputBOM(components=..., project_description=db_project.description)`.
                *   Return the dictionary structure for the 'queued' response, using the fetched data: `{"status": "queued", "position": position, "total_in_queue": total_in_queue, "bom": bom.model_dump()}`.
            *   **Else (handle 'finished' later):** For now, if status is not 'queued', continue to the original 'finished' block logic (which still uses CSVs) or raise a 501 Not Implemented error temporarily. We will replace this in a later step.
    *   Ensure the 404 HTTPException is raised at the end if neither 'queued' nor 'finished' logic handles the project (this might change based on how the 'finished' part is integrated).

Context: This step refactors the read path for *queued* projects, replacing filesystem lookups and CSV parsing with database queries via the CRUD layer. It keeps the Pydantic schemas for the response consistent.
```

---

**Prompt 8: Refactor `GET /project/queue/length` Endpoint**
```text
Objective: Modify the `get_queue_length` endpoint to use the database CRUD function.

Instructions:
1.  Open `pcb_part_finder/api/projects.py`.
2.  Import `Depends` from `fastapi`, `Session` from `sqlalchemy.orm`, the CRUD function `count_queued_projects` from `..db.crud`, and `get_db` from `..db.session`.
3.  Modify the `get_queue_length` async function:
    *   Add `db: Session = Depends(get_db)` as a parameter.
    *   Remove the directory listing logic (`QUEUE_DIR`, `iterdir`, list comprehension).
    *   **Instead:**
        *   Call `count = crud.count_queued_projects(db=db)`.
        *   Return `{"queue_length": count}`.
    *   Remove unused imports like `Path`.

Context: This replaces the filesystem-based queue length calculation with a much more efficient database query.
```

---

**Prompt 9: Define Matching SQLAlchemy Models**
```text
Objective: Define SQLAlchemy ORM models for the `components` and `bom_item_matches` tables based on `init.sql`.

Instructions:
1.  Open `pcb_part_finder/db/models.py`.
2.  Import `DECIMAL`, `ForeignKeyConstraint`, `Index` if needed (though relationships handle FKs usually).
3.  Define the `Component` class inheriting from `Base`:
    *   Set `__tablename__ = 'components'`.
    *   Define columns matching `init.sql`: `component_id` (Integer, primary_key=True), `mouser_part_number` (String, unique=True, index=True), `manufacturer_part_number` (String, index=True, nullable=True), `manufacturer_name` (String, nullable=True), `description` (Text, nullable=True), `datasheet_url` (Text, nullable=True), `package` (String, nullable=True), `price` (DECIMAL(10, 2), nullable=True), `availability` (String, nullable=True), `last_updated` (TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow).
    *   Add relationship: `matches = relationship("BomItemMatch", back_populates="component")`.
4.  Define the `BomItemMatch` class inheriting from `Base`:
    *   Set `__tablename__ = 'bom_item_matches'`.
    *   Define columns matching `init.sql`: `match_id` (Integer, primary_key=True), `bom_item_id` (Integer, ForeignKey('bom_items.bom_item_id'), index=True), `component_id` (Integer, ForeignKey('components.component_id'), index=True, nullable=True), `match_status` (String), `matched_at` (TIMESTAMP, default=datetime.datetime.utcnow).
    *   Add relationships:
        *   `bom_item = relationship("BomItem")` (Might need `back_populates` on `BomItem` if a direct link is desired there).
        *   `component = relationship("Component", back_populates="matches")`.

Context: These models represent the results of the part matching process: the details of the identified components (`Component`) and the link between an original BOM item and a matched component (`BomItemMatch`).
```

---

**Prompt 10: Implement Matching CRUD Functions**
```text
Objective: Create CRUD functions for handling `Component` and `BomItemMatch` data, retrieving finished project data, and updating project status.

Instructions:
1.  Open `pcb_part_finder/db/crud.py`.
2.  Import the new models `Component`, `BomItemMatch` from `.models`.
3.  Import `select`, `update` statements from `sqlalchemy` if needed for more complex queries/updates.
4.  Define `get_or_create_component(db: Session, component_data: dict) -> Component`:
    *   Tries to find a `Component` based on `mouser_part_number` from `component_data`.
    *   If found, update its fields (price, availability, description, etc., and `last_updated`) from `component_data`.
    *   If not found, create a new `Component` instance with `component_data`.
    *   Add/commit/refresh as needed. Return the found or created `Component`. (This logic is crucial for the background worker).
5.  Define `create_bom_item_match(db: Session, bom_item_id: int, component_id: int | None, match_status: str) -> BomItemMatch`:
    *   Creates a `BomItemMatch` instance.
    *   Adds it to the session. Returns the instance. (Commit often handled later).
6.  Define `get_finished_project_data(db: Session, project_id: str) -> List[tuple[BomItem, BomItemMatch | None, Component | None]]`:
    *   Perform a query that joins `BomItem` LEFT OUTER JOIN `BomItemMatch` ON `BomItem.bom_item_id == BomItemMatch.bom_item_id` LEFT OUTER JOIN `Component` ON `BomItemMatch.component_id == Component.component_id`.
    *   Filter the query where `BomItem.project_id == project_id`.
    *   Return the list of resulting tuples `(BomItem, BomItemMatch, Component)`. Handle potential `None` values from the outer joins.
7.  Define `update_project_status(db: Session, project_id: str, new_status: str, start_time: datetime | None = None, end_time: datetime | None = None) -> bool`:
    *   Find the `Project` by `project_id`.
    *   If found, update its `status` field to `new_status`. Update `start_time` and `end_time` if provided.
    *   Commit the change. Return `True`.
    *   If not found, return `False`.

Context: These functions support the background worker's process of storing matched component data and associating it with BOM items. They also provide the query needed to retrieve the complete data for a finished project and allow status updates (including marking for deletion/cancellation).
```

---

**Prompt 11: Refactor `GET /project/{project_id}` (Finished Status)**
```text
Objective: Enhance the `get_project` endpoint to handle 'finished' projects by fetching enriched data from the database.

Instructions:
1.  Open `pcb_part_finder/api/projects.py`.
2.  Import the new CRUD function `get_finished_project_data` from `..db.crud`.
3.  Import the Pydantic schemas `MatchedBOM`, `MatchedComponent` from `..schemas`.
4.  Import `datetime` from `datetime`.
5.  Modify the `get_project` async function inside the `else` block (or add an `elif db_project.status == 'finished':`) following the 'queued' check:
    *   Remove the `finished_path.exists()` check and related `Path` logic.
    *   Remove the `pd.read_csv('bom_matched.csv')` call.
    *   Remove the manual iteration over DataFrame rows (`df.iterrows()`).
    *   Remove the `read_project_details` call for reading `results.json`.
    *   **Instead:**
        *   Call `results_data = crud.get_finished_project_data(db=db, project_id=project_id)`.
        *   Create an empty list `matched_components = []`.
        *   Iterate through `results_data` (which contains tuples like `(db_bom_item, db_match, db_component)`):
            *   Map data from `db_bom_item` (qty, description, possible_mpn, package, notes) to a dictionary.
            *   If `db_match` and `db_component` exist (successful match):
                *   Add fields from `db_component` (mouser_part_number, manufacturer_part_number, manufacturer_name, mouser_description, datasheet_url, price, availability) to the dictionary. Handle potential `None` values and type conversions (e.g., `Decimal` to `float`).
                *   Add `match_status` from `db_match` to the dictionary.
            *   Else (no match found):
                *   Set the corresponding fields (mouser_part_number, etc.) to `None`.
                *   Set `match_status` (e.g., from `db_match.match_status` if it exists even without a component, or deduce as 'no_match').
            *   Instantiate `MatchedComponent(**component_dict)` and append to `matched_components`.
        *   Reconstruct the `MatchedBOM` Pydantic model:
            *   `match_date = db_project.end_time.isoformat() if db_project.end_time else datetime.now().isoformat()` (use end time from project record).
            *   `match_status = db_project.status` (or a specific status field if you add one).
            *   Instantiate `MatchedBOM(components=matched_components, project_description=db_project.description, match_date=match_date, match_status=match_status)`.
        *   Prepare the `results` dictionary (e.g., `{"start_time": db_project.start_time.isoformat(), "end_time": match_date, "status": match_status}`) using data from `db_project`.
        *   Return the dictionary structure for the 'finished' response: `{"status": "finished", "bom": matched_bom.model_dump(), "results": results}`.
    *   Modify the final `raise HTTPException(status_code=404, ...)` to only trigger if the status is neither 'queued' nor 'finished' (or handle other statuses like 'processing', 'error' explicitly if desired).

Context: This completes the refactoring of the main project retrieval endpoint, enabling it to serve both queued and finished projects entirely from the database, maintaining the original response structure.
```

---

**Prompt 12: Refactor `DELETE /project/{project_id}` Endpoint**
```text
Objective: Modify the project deletion endpoint to update the project status in the database instead of removing filesystem artifacts.

Instructions:
1.  Open `pcb_part_finder/api/projects.py`.
2.  Import the CRUD function `update_project_status` from `..db.crud`. (Ensure `get_project_by_id` is also imported if not already).
3.  Modify the `delete_project` async function:
    *   Add `db: Session = Depends(get_db)` as a parameter.
    *   Remove the `queue_path` check (`QUEUE_DIR`, `Path`, `queue_path.exists()`).
    *   Remove the `shutil.rmtree(queue_path)` call.
    *   **Instead:**
        *   Call `db_project = crud.get_project_by_id(db=db, project_id=project_id)`.
        *   If `db_project` is None or `db_project.status != 'queued'`, raise `HTTPException(status_code=404, detail="Project not found in queue or cannot be deleted")`. (Adjust status check logic as needed - maybe allow deletion of 'error' states too?).
        *   Call `updated = crud.update_project_status(db=db, project_id=project_id, new_status='cancelled')`. You could use 'deleted' but 'cancelled' might be clearer.
        *   If `updated` is `False` (shouldn't happen if project was found), raise an internal server error.
        *   Commit the transaction `db.commit()`.
        *   Return `{"status": "cancelled"}` (or "deleted" matching the new status).
    *   Remove unused imports like `Path`, `shutil`.

Context: This changes the delete operation from a physical file deletion to a logical status update in the database, preserving project history while achieving the user's intent.
```

---

**Prompt 13: Prerequisite CRUD for Background Worker**
```text
Objective: Ensure CRUD functions exist that the (separate) background worker process will need to interact with the database state.

Instructions:
1.  Review `pcb_part_finder/db/crud.py`.
2.  Ensure the following functions (or equivalents) exist and are robust:
    *   `find_next_queued_project(db: Session) -> Project | None`: Queries for one project where `status == 'queued'`, ordered by `created_at`, and returns it. (Could use `LIMIT 1`).
    *   `update_project_status(db: Session, project_id: str, new_status: str, start_time: datetime | None = None, end_time: datetime | None = None) -> bool`: Already created, ensure it can handle setting status to 'processing', 'finished', 'error', and updating timestamps.
    *   `get_bom_items_for_project(db: Session, project_id: str) -> List[BomItem]`: Already created.
    *   `get_or_create_component(db: Session, component_data: dict) -> Component`: Already created. Needs careful implementation regarding updates vs. creates.
    *   `create_bom_item_match(db: Session, bom_item_id: int, component_id: int | None, match_status: str) -> BomItemMatch`: Already created. Ensure the worker commits transactions appropriately after processing a project.

Context: While we are not refactoring the worker itself with these prompts, the API's database layer must provide the necessary interface for the worker to function correctly in the new DB-centric architecture. This step verifies those prerequisites. No code changes are likely needed if previous steps were done correctly, but it's a crucial verification point.
```

---

**Prompt 14: Final Code Cleanup (API Service)**
```text
Objective: Remove all obsolete filesystem and CSV-related code from the API service.

Instructions:
1.  Thoroughly review all files within `pcb_part_finder/api/` and `pcb_part_finder/db/`.
2.  Delete any remaining helper functions related to CSVs or DataFrames (`bom_to_dataframe`, `dataframe_to_bom`, `read_project_details`).
3.  Remove unused constants like `PROJECTS_DIR`, `QUEUE_DIR`, `FINISHED_DIR`.
4.  Remove any remaining unused imports, especially `pandas`, `pathlib`, `shutil`, `csv`, `os` (if only used for paths), `string`, `random` (if `generate_project_id` was fully replaced).
5.  Ensure Pydantic schemas in `pcb_part_finder/api/schemas.py` are still accurate for the API contract, but do not contain database-specific details (like foreign key IDs) unless intended to be part of the API response.

Context: This step cleans up the codebase, removing dead code related to the old persistence method, making the project cleaner and easier to maintain.
```

---

**Prompt 15: Configuration Cleanup (Docker)**
```text
Objective: Remove the unnecessary project volume mount from the API service definition in `docker-compose.yml`.

Instructions:
1.  Open `docker-compose.yml`.
2.  Locate the `api` service definition.
3.  In the `volumes` section for the `api` service, remove the line mounting the local `./projects` directory (e.g., `- ./projects:/app/projects`).
4.  Leave the `./cache:/app/cache` volume if it's being used for other purposes.
5.  The `web` service might also have a `./projects` mount – remove it if it's also no longer needed there.

Context: Since project data is now stored exclusively in the database (`db` service volume `postgres_data`), the API and Web services no longer need direct access to the host's `./projects` directory for reading/writing BOM data. This simplifies the configuration.
```

---

This sequence of prompts provides a granular, step-by-step guide for an LLM to perform the refactoring, ensuring each change builds upon the last and maintains a working state logically and integrates with the previous steps.
