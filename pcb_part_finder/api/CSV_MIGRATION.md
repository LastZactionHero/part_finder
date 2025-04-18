
Okay, let's architect the addition of Project Name and Description fields.

**Blueprint: Adding Project Name and Description**

1.  **Goal:** Allow users to provide a name and description for their project via the web UI, store this information in the database, and use it as context during the LLM part evaluation phase.
2.  **Current State:** The UI only accepts a component list CSV. The API accepts a hardcoded description ("Web UI Project") and stores it, but there's no concept of a project name being passed or stored. The LLM only receives the project description (currently hardcoded) as context.
3.  **High-Level Strategy:**
    *   Modify the frontend HTML to add input fields for Name and Description.
    *   Update the frontend JavaScript to capture these inputs and send them to the API.
    *   Adjust the API schema (`InputBOM`) to accept `project_name` and use the user-provided `project_description`.
    *   Update the API endpoint (`create_project`) to receive the new schema and pass the data to the database layer.
    *   Modify the database CRUD function (`crud_create_project`) to accept and store the project name alongside the description. (The DB schema itself is already correct).
    *   Ensure the core processing logic (`load_project_data_from_db`, `process_project_from_db`, `_process_single_bom_item`) correctly loads and passes both name and description.
    *   Update the LLM prompt formatting function (`format_evaluation_prompt`) to include the project name in the context provided to the LLM.

**Iterative Steps (Chunked and Refined):**

*   **Phase 1: Frontend UI Modification**
    *   **Step 1.1:** Edit `pcb_part_finder/web/templates/index.html`. Add labeled input fields for "Project Name" and "Project Description" above the existing component list textarea. Assign appropriate IDs (`projectNameInput`, `projectDescriptionInput`).

*   **Phase 2: Frontend Logic Integration**
    *   **Step 2.1:** Edit `pcb_part_finder/web/static/script.js`. Add `getElementById` calls to get references to the new input elements (`projectNameInput`, `projectDescriptionInput`).
    *   **Step 2.2:** Edit `pcb_part_finder/web/static/script.js`. Modify the `createProject` function signature to accept `projectName` and `projectDescription` arguments.
    *   **Step 2.3:** Edit `pcb_part_finder/web/static/script.js`. Inside the `submitButton` event listener, read the `.value` from the new name and description input elements and pass them when calling `createProject`.
    *   **Step 2.4:** Edit `pcb_part_finder/web/static/script.js`. Update the `fetch` call body within the `createProject` function. Add a `project_name: projectName` field and ensure the `project_description` field uses the `projectDescription` argument passed to the function (replacing the hardcoded value).

*   **Phase 3: Backend Schema Update**
    *   **Step 3.1:** Edit `pcb_part_finder/schemas.py`. Modify the `InputBOM` Pydantic model to include an optional `project_name: Optional[str] = None` field. Update the default value for `project_description` if desired, or remove it if it should always be provided by the frontend now.

*   **Phase 4: Backend API and Database Integration**
    *   **Step 4.1:** Edit `pcb_part_finder/db/crud.py`. Modify the `create_project` function signature to accept `name: Optional[str]` as a parameter. Update the creation of the `Project` model instance within the function to set the `name` attribute using this new parameter.
    *   **Step 4.2:** Edit `pcb_part_finder/api/projects.py`. Update the `create_project` API endpoint function:
        *   It should now use the modified `InputBOM` schema implicitly due to the type hint.
        *   Extract `bom.project_name` from the input `bom`.
        *   When calling `crud_create_project`, pass `name=bom.project_name` along with the existing `description=bom.project_description`.

*   **Phase 5: Core Processing Data Flow**
    *   **Step 5.1:** Edit `pcb_part_finder/core/data_loader.py` (or wherever `load_project_data_from_db` is defined). Ensure this function fetches and returns the `project.name` attribute along with the `project` object and `bom_items`. *(Self-correction: `processor.py` currently calls `load_project_data_from_db` which returns the `Project` object directly. So, the name is implicitly loaded if the ORM model is correct. No code change needed here, just verification that `Project.name` is accessible)*.
    *   **Step 5.2:** Edit `pcb_part_finder/core/processor.py`. In the `process_project_from_db` function, after loading the `project` object, retrieve `project.name`.
    *   **Step 5.3:** Edit `pcb_part_finder/core/processor.py`. Modify the call to `executor.submit(_process_single_bom_item, ...)` within `process_project_from_db` to pass the retrieved `project.name` as an argument.
    *   **Step 5.4:** Edit `pcb_part_finder/core/processor.py`. Modify the `_process_single_bom_item` function signature to accept `project_name: str` as a parameter.

*   **Phase 6: LLM Context Integration**
    *   **Step 6.1:** Edit `pcb_part_finder/core/llm_handler.py`. Modify the `format_evaluation_prompt` function signature to accept `project_name: str` as a parameter.
    *   **Step 6.2:** Edit `pcb_part_finder/core/llm_handler.py`. Update the prompt string returned by `format_evaluation_prompt` to include a line like `Project Name: {project_name}` near the `Project Notes:` section.
    *   **Step 6.3:** Edit `pcb_part_finder/core/processor.py`. Update the call to `llm_handler.format_evaluation_prompt` within `_process_single_bom_item` to pass the `project_name` received by the worker function.

This breakdown provides small, manageable steps focusing on specific files and functionalities, ensuring a logical progression from UI to LLM context.

---

**LLM Generation Prompts:**

Here are the prompts derived from the steps above, designed for a code-generation LLM.

**Prompt 1: Add Frontend HTML Inputs**

```text
Modify the file `pcb_part_finder/web/templates/index.html`. Inside the `<div class="upload-section">`, immediately before the `<textarea id="componentInput">`, add two new input fields:
1.  A text input for "Project Name". Include a `<label>`. Give the input an `id="projectNameInput"`.
2.  A textarea for "Project Description". Include a `<label>`. Give the textarea an `id="projectDescriptionInput"`. Make its appearance consistent with the existing textarea but perhaps shorter initially.
```

**Prompt 2: Get References to New Inputs in JS**

```text
Modify the file `pcb_part_finder/web/static/script.js`. Near the top where other DOM elements are referenced (like `componentInput`, `submitButton`), add two new constants:
1.  `projectNameInput` referencing the element with ID `projectNameInput`.
2.  `projectDescriptionInput` referencing the element with ID `projectDescriptionInput`.
```

**Prompt 3: Modify JS `createProject` Signature**

```text
Modify the file `pcb_part_finder/web/static/script.js`. Update the `createProject` asynchronous function signature. It currently accepts `components`. Modify it to also accept `projectName` and `projectDescription` as the first two arguments: `async function createProject(projectName, projectDescription, components)`.
```

**Prompt 4: Read and Pass Values in JS Event Listener**

```text
Modify the file `pcb_part_finder/web/static/script.js`. Locate the `submitButton.addEventListener('click', async () => { ... });` block. Inside the `try` block, *before* calling `createProject`, add lines to:
1. Read the `.value.trim()` from `projectNameInput` into a variable (e.g., `const projectName`).
2. Read the `.value.trim()` from `projectDescriptionInput` into a variable (e.g., `const projectDescription`).
3. Add basic validation: if either `projectName` or `projectDescription` is empty, throw an error like `throw new Error('Please enter both Project Name and Description');`.
4. Update the line that calls `createProject(components)` to pass the new values: `const projectId = await createProject(projectName, projectDescription, components);`.
```

**Prompt 5: Update JS `fetch` Call Body**

```text
Modify the file `pcb_part_finder/web/static/script.js`. Inside the `createProject` function, locate the `fetch(\`${API_BASE_URL}/project\`, { ... })` call. Modify the `body: JSON.stringify({ ... })` part:
1. Add a new field `project_name: projectName,`.
2. Change the existing `project_description: "Web UI Project"` field to use the function argument: `project_description: projectDescription,`.
```

**Prompt 6: Update API Input Schema**

```text
Modify the file `pcb_part_finder/schemas.py`. In the `InputBOM` Pydantic model:
1. Add a new field: `project_name: Optional[str] = None`.
2. Review the existing `project_description: Optional[str] = "Default Project Description"`. Since the frontend will now always send a description, change this to `project_description: Optional[str] = None` to reflect that it's expected from the input, though still optional in the model definition.
```

**Prompt 7: Update Database CRUD Function**

```text
Modify the file `pcb_part_finder/db/crud.py`.
1. Update the signature of the `create_project` function. It currently accepts `db: Session, project_id: str, description: Optional[str], status: str`. Modify it to also accept `name: Optional[str]` like this: `create_project(db: Session, project_id: str, name: Optional[str], description: Optional[str], status: str)`.
2. Inside the function, when creating the `db_project = Project(...)` instance, add the `name=name,` argument alongside the existing `description=description` and `status=status`.
```

**Prompt 8: Update API Endpoint Logic**

```text
Modify the file `pcb_part_finder/api/projects.py`. In the `create_project` endpoint function:
1. The function signature `async def create_project(bom: InputBOM, ...)` already uses the correct schema type hint, so it will implicitly expect the updated `InputBOM` from step 6.
2. Inside the function, before calling `crud_create_project`, extract the project name: `project_name = bom.project_name`.
3. Modify the call to `db_project = crud_create_project(...)`. It currently passes `db=db, project_id=project_id, description=bom.project_description, status='queued'`. Update it to also pass the extracted name: `db=db, project_id=project_id, name=project_name, description=bom.project_description, status='queued'`.
```

**Prompt 9: Pass Project Name in Core Processor**

```text
Modify the file `pcb_part_finder/core/processor.py`. In the `process_project_from_db` function:
1. After the line `project, bom_items = load_project_data_from_db(project_id, db)`, add a line to get the project name: `project_name = project.name`. Also, ensure the description is retrieved if it wasn't already: `project_description = project.description`. (It seems description was already being passed, but let's be explicit).
2. Find the loop where tasks are submitted: `future = executor.submit(...)`.
3. Modify the arguments passed to `_process_single_bom_item`. It currently likely passes `bom_item, project.description, ...`. Update it to pass the retrieved name and description: `bom_item, project_name, project_description, mouser_cache_manager, bom_list_as_dicts`. Adjust the order if necessary based on the current function signature, but ensure both `project_name` and `project_description` are included.
```

**Prompt 10: Update Worker Function Signature**

```text
Modify the file `pcb_part_finder/core/processor.py`. Update the function signature for `_process_single_bom_item`. It currently accepts `bom_item: BomItem, project_description: str, ...`. Modify it to accept both name and description, ensuring the names match those passed in the previous step: `_process_single_bom_item(bom_item: BomItem, project_name: str, project_description: str, mouser_cache_manager: MouserApiCacheManager, full_bom_list: List[Dict[str, Any]]) -> str:`. Update the docstring accordingly.
```

**Prompt 11: Update LLM Prompt Function Signature**

```text
Modify the file `pcb_part_finder/core/llm_handler.py`. Update the function signature for `format_evaluation_prompt`. It currently accepts `part_info: Dict[str, str], project_notes: str, ...`. Modify it to accept `project_name: str` as well, perhaps after `part_info`: `format_evaluation_prompt(part_info: Dict[str, str], project_name: str, project_notes: str, bom_list: List[Dict[str, str]], mouser_results: List[Dict[str, Any]]) -> str:`. Update the docstring arguments list.
```

**Prompt 12: Include Project Name in LLM Prompt String**

```text
Modify the file `pcb_part_finder/core/llm_handler.py`. Inside the `format_evaluation_prompt` function, locate the prompt string (the f-string). Find the section that includes:
```
Project Notes:
{project_notes}
```
Immediately *before* the "Project Notes:" line, add a new line to display the project name:
```
Project Name: {project_name}
```
Ensure the formatting is consistent.
```

**Prompt 13: Pass Project Name to LLM Prompt Formatter**

```text
Modify the file `pcb_part_finder/core/processor.py`. Inside the `_process_single_bom_item` worker function, locate the call to `llm_handler.format_evaluation_prompt(...)`. It currently passes `part_info, project_description, ...`. Update the call to include the `project_name` that the worker function now receives as a parameter, matching the updated signature from Prompt 11: `llm_handler.format_evaluation_prompt(part_info, project_name, project_description, full_bom_list, mouser_results)`.
```
