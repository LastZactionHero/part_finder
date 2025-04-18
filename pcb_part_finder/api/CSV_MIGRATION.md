
Okay, let's create a detailed, iterative plan to implement the real data processing logic in `pcb_part_finder/core/processor.py`, replacing the mock data generation.

**Overall Goal:** Modify `process_project_from_db` in `pcb_part_finder/core/processor.py` to use `llm_handler.py` and `mouser_api.py` functions to enrich `BomItem` data loaded from the database with real component information from Mouser, guided by LLM analysis, and then save these results back to the database via `output_writer.py`.

**High-Level Plan:**

1.  **Setup:** Import necessary modules and initialize variables.
2.  **Load Data:** Load project details and BOM items from the database (already implemented).
3.  **Iterate & Process BOM Items:** Loop through each `BomItem`.
    *   Generate search terms using the LLM based on item description, MPN, package, etc.
    *   Search Mouser using the generated terms.
    *   Evaluate Mouser results with the LLM to select the best Manufacturer Part Number (MPN).
    *   Fetch detailed information for the selected MPN from Mouser.
    *   Format the results, handling successes and failures gracefully.
    *   Keep track of selected parts for context in subsequent LLM evaluations.
4.  **Save Results:** Save the processed data (enriched BOM items) back to the database (already implemented, needs correct input structure).

**Iterative Breakdown (Chunking):**

*   **Chunk 1: Basic Structure & Imports:** Modify `processor.py` to import required modules (`llm_handler`, `mouser_api`) and set up the main loop structure, replacing the mock data generation block with a placeholder loop.
*   **Chunk 2: Search Term Generation:** Implement the logic within the loop to format the prompt, call the LLM to get search terms, and parse the response for a single `BomItem`. Add basic error handling.
*   **Chunk 3: Mouser Keyword Search:** Add the logic to iterate through the generated search terms, call the Mouser keyword search API, and aggregate unique results. Add error handling for API calls.
*   **Chunk 4: LLM Evaluation:** Implement the LLM call to evaluate the aggregated Mouser results and select the best MPN. Requires formatting the evaluation prompt with item details, project notes, *previously selected parts* (need to track this), and search results. Handle LLM errors and cases where no MPN is chosen.
*   **Chunk 5: Fetch Final Part Details:** Add the call to the Mouser MPN search API using the MPN selected by the LLM. Handle API errors and cases where the MPN isn't found.
*   **Chunk 6: Result Formatting & Accumulation:** Structure the final `match_data` based on the success or failure of the previous steps (search term generation, keyword search, evaluation, final fetch). Set an appropriate `status` field. Store this result and update the list of previously selected parts. Ensure the data format matches what `save_bom_results_to_db` expects.
*   **Chunk 7: Integration & Finalization:** Ensure the loop handles errors for individual items gracefully and continues processing others. Verify the final `bom_items_with_matches` list is correctly passed to `save_bom_results_to_db`. Add overall try/except blocks and logging.

**Second Iteration (Smaller Steps for Implementation):**

1.  **Step 1: Imports and Setup:**
    *   Add imports: `llm_handler`, `mouser_api`, `LlmApiError`, `MouserApiError`, `List`.
    *   Initialize `bom_items_with_matches = []` before the loop.
    *   Initialize `selected_part_details = []` before the loop (to store `{ 'Description': ..., 'Manufacturer Part Number': ... }` for context).
    *   Remove the existing mock data generation block inside the `for bom_item in bom_items:` loop.
2.  **Step 2: Generate Search Terms (Inside Loop):**
    *   Create `part_info` dict from `bom_item` attributes (`description`, `possible_mpn`, `package`, `notes`).
    *   Wrap LLM calls in a `try...except LlmApiError`.
    *   Call `llm_handler.format_search_term_prompt(part_info)`.
    *   Call `llm_handler.get_llm_response()`.
    *   Call `llm_handler.parse_search_terms()`.
    *   Store terms or handle failure (log error, set a flag/status for this item).
3.  **Step 3: Perform Mouser Keyword Search (Inside Loop):**
    *   Check if search terms were successfully generated.
    *   Initialize `mouser_results = []` and `unique_mpns = set()`.
    *   Loop through search terms.
    *   Wrap Mouser call in `try...except MouserApiError`.
    *   Call `mouser_api.search_mouser_by_keyword()`.
    *   Iterate through results, add unique ones (based on `MouserPartNumber`) to `mouser_results`.
    *   Handle failure (log error, set flag/status).
4.  **Step 4: Evaluate Search Results (Inside Loop):**
    *   Check if `mouser_results` were found.
    *   Wrap LLM calls in `try...except LlmApiError`.
    *   Call `llm_handler.format_evaluation_prompt(part_info, project.project_notes, selected_part_details, mouser_results)`.
    *   Call `llm_handler.get_llm_response()`.
    *   Call `llm_handler.extract_mpn_from_eval()`.
    *   Store the chosen MPN or handle failure (log error, set flag/status).
5.  **Step 5: Get Final Part Details (Inside Loop):**
    *   Check if an MPN was successfully extracted.
    *   Wrap Mouser call in `try...except MouserApiError`.
    *   Call `mouser_api.search_mouser_by_mpn(chosen_mpn)`.
    *   Store the detailed part dictionary or handle failure (log error, set flag/status).
6.  **Step 6: Format and Store Result (Inside Loop):**
    *   Initialize `match_data = {}` and `status = 'error'`.
    *   Based on the flags/status set in previous steps:
        *   If final part details fetched: Populate `match_data` with details from `search_mouser_by_mpn` result (Mouser Part Number, MPN, Manufacturer, Description, Datasheet, Price, Availability), set `status = 'matched'`. Add part details to `selected_part_details`.
        *   If MPN lookup failed: Set `status = 'mpn_lookup_failed'`. Populate `match_data` with minimal info and the failed MPN if available.
        *   If evaluation failed: Set `status = 'evaluation_failed'`.
        *   If no keyword results: Set `status = 'no_keyword_results'`.
        *   If search term generation failed: Set `status = 'search_term_failed'`.
    *   Add the `status` key to `match_data`.
    *   Create `item_data` dict: `{ 'bom_item_id': bom_item.bom_item_id, 'quantity': bom_item.quantity, 'description': bom_item.description, 'matches': [match_data] }`. Note: `output_writer` expects a list for `matches`. We are generating one primary match/status per item here.
    *   Append `item_data` to `bom_items_with_matches`.
7.  **Step 7: Final Integration:**
    *   Ensure the loop continues to the next `bom_item` even if errors occur for the current one.
    *   The call `save_bom_results_to_db(project_id, bom_items_with_matches, db)` should remain after the loop.
    *   Review overall logging for clarity.

This step-by-step breakdown seems appropriately sized for implementation. Each step introduces a manageable piece of functionality.

---

**Implementation Prompts:**

Here are the prompts for a code-generation LLM, designed to implement the plan step-by-step:

**Prompt 1: Setup and Imports**

```text
Okay, let's start modifying `pcb_part_finder/core/processor.py`.

1.  Add the following imports at the top:
    *   `from typing import List, Dict, Any` (Update existing import if necessary)
    *   `from . import llm_handler`
    *   `from . import mouser_api`
    *   `from .llm_handler import LlmApiError`
    *   `from .mouser_api import MouserApiError`
2.  Inside the `process_project_from_db` function, right before the `for bom_item in bom_items:` loop, initialize two empty lists:
    *   `bom_items_with_matches = []`
    *   `selected_part_details = []`
3.  Remove the entire block of code *inside* the `for bom_item in bom_items:` loop that currently generates mock `matches` and `item_data`. The loop structure (`for bom_item in bom_items:`) should remain, but its body should be empty for now.
```

**Prompt 2: Generate Search Terms**

```text
Continuing in `pcb_part_finder/core/processor.py` inside the `for bom_item in bom_items:` loop:

1.  Create a dictionary `part_info` from the current `bom_item` object. Include keys 'Description', 'Possible MPN', 'Package', and 'Notes/Source', mapping them to the corresponding attributes of `bom_item` (e.g., `bom_item.description`, `bom_item.possible_mpn`, `bom_item.package`, `bom_item.notes`). Handle potential `None` values gracefully, perhaps by defaulting to empty strings.
2.  Initialize `search_terms = []` and `status = 'pending'`.
3.  Add a `try...except LlmApiError as e:` block.
    *   Inside the `try` block:
        *   Generate the prompt string: `search_prompt = llm_handler.format_search_term_prompt(part_info)`
        *   Get the LLM response: `llm_response_terms = llm_handler.get_llm_response(search_prompt)`
        *   Parse the terms: `search_terms = llm_handler.parse_search_terms(llm_response_terms)`
        *   Check if `search_terms` is empty. If it is, log a warning (`logger.warning(...)`) indicating no search terms were generated for this item and set `status = 'search_term_failed'`.
    *   Inside the `except` block:
        *   Log the error: `logger.error(f"LLM error generating search terms for item {bom_item.bom_item_id}: {e}")`
        *   Set `status = 'search_term_failed'`
```

**Prompt 3: Perform Mouser Keyword Search**

```text
Continuing in `pcb_part_finder/core/processor.py` inside the `for bom_item in bom_items:` loop, *after* the search term generation block:

1.  Initialize `mouser_results = []` and `unique_mouser_part_numbers = set()`.
2.  Add a conditional check: `if status == 'pending' and search_terms:`. All the following logic in this step should be inside this `if` block.
3.  Loop through each `term` in `search_terms`.
4.  Inside this term loop, add a `try...except MouserApiError as e:` block.
    *   Inside the `try` block:
        *   Call the Mouser API: `results = mouser_api.search_mouser_by_keyword(term)`
        *   Iterate through the `results` list (each item is a potential part dictionary).
        *   For each `part` in `results`:
            *   Get the `MouserPartNumber`.
            *   If the `MouserPartNumber` is not `None` and not already in `unique_mouser_part_numbers`:
                *   Add the `MouserPartNumber` to `unique_mouser_part_numbers`.
                *   Append the `part` dictionary to the `mouser_results` list.
    *   Inside the `except` block:
        *   Log the error: `logger.error(f"Mouser API keyword search error for item {bom_item.bom_item_id}, term '{term}': {e}")`
        *   (Optionally, you could `continue` to the next term, or break; for now, just logging is fine).
5.  After the term loop (still inside the main `if status == 'pending' and search_terms:` block), check if `mouser_results` is empty. If it is, log a warning (`logger.warning(...)`) indicating no results were found for any search term for this item and set `status = 'no_keyword_results'`.
```

**Prompt 4: Evaluate Search Results**

```text
Continuing in `pcb_part_finder/core/processor.py` inside the `for bom_item in bom_items:` loop, *after* the Mouser keyword search block:

1.  Initialize `chosen_mpn = None`.
2.  Add a conditional check: `if status == 'pending' and mouser_results:`. All the following logic in this step should be inside this `if` block.
3.  Add a `try...except LlmApiError as e:` block.
    *   Inside the `try` block:
        *   Format the evaluation prompt: `eval_prompt = llm_handler.format_evaluation_prompt(part_info, project.project_notes, selected_part_details, mouser_results)` (Make sure `project` is available; it's returned by `load_project_data_from_db`).
        *   Get the LLM response: `llm_response_eval = llm_handler.get_llm_response(eval_prompt)`
        *   Extract the MPN: `chosen_mpn = llm_handler.extract_mpn_from_eval(llm_response_eval)`
        *   Check if `chosen_mpn` is `None`. If it is, log a warning (`logger.warning(...)`) indicating the LLM failed to select an MPN for this item and set `status = 'evaluation_failed'`.
    *   Inside the `except` block:
        *   Log the error: `logger.error(f"LLM error evaluating search results for item {bom_item.bom_item_id}: {e}")`
        *   Set `status = 'evaluation_failed'`
```

**Prompt 5: Get Final Part Details**

```text
Continuing in `pcb_part_finder/core/processor.py` inside the `for bom_item in bom_items:` loop, *after* the LLM evaluation block:

1.  Initialize `final_part_details = None`.
2.  Add a conditional check: `if status == 'pending' and chosen_mpn:`. All the following logic in this step should be inside this `if` block.
3.  Add a `try...except MouserApiError as e:` block.
    *   Inside the `try` block:
        *   Call the Mouser API: `final_part_details = mouser_api.search_mouser_by_mpn(chosen_mpn)`
        *   Check if `final_part_details` is `None`. If it is, log a warning (`logger.warning(...)`) indicating the chosen MPN was not found via the MPN search API for this item and set `status = 'mpn_lookup_failed'`.
        *   If `final_part_details` is not `None`, set `status = 'matched'`.
    *   Inside the `except` block:
        *   Log the error: `logger.error(f"Mouser API MPN search error for item {bom_item.bom_item_id}, MPN '{chosen_mpn}': {e}")`
        *   Set `status = 'mpn_lookup_failed'`
```

**Prompt 6: Format and Store Result**

```text
Continuing in `pcb_part_finder/core/processor.py` inside the `for bom_item in bom_items:` loop, *after* fetching final part details:

1.  Initialize `match_data = {}`.
2.  Use `if/elif/else` based on the `status` variable to populate `match_data`:
    *   `if status == 'matched' and final_part_details:`
        *   Populate `match_data` using the keys from `final_part_details` returned by `search_mouser_by_mpn`. The keys expected by `save_bom_results_to_db` (based on its Component model creation) are: `'mouser_part_number'`, `'manufacturer_name'`, `'description'`, `'datasheet_url'`, `'price'`, `'availability'`. Map the values from `final_part_details` accordingly. Ensure the key names match what `save_bom_results_to_db` uses when creating/querying the `Component` (e.g., use 'manufacturer_name' not 'manufacturer').
        *   Add `'match_status': status` to `match_data`.
        *   Append a dictionary `{'Description': bom_item.description, 'Manufacturer Part Number': final_part_details.get('Manufacturer Part Number')}` to the `selected_part_details` list.
    *   `elif status == 'mpn_lookup_failed':`
        *   Set `match_data = {'match_status': status, 'possible_mpn': chosen_mpn or part_info.get('Possible MPN', '')}` (Include other fields as empty/None if needed by the saving function).
    *   `elif status == 'evaluation_failed':`
        *   Set `match_data = {'match_status': status}`
    *   `elif status == 'no_keyword_results':`
        *   Set `match_data = {'match_status': status}`
    *   `elif status == 'search_term_failed':`
        *   Set `match_data = {'match_status': status}`
    *   `else:` (Handle any unexpected status or default to 'error')
        *   Set `match_data = {'match_status': 'error'}`
3.  Create the `item_data` dictionary:
    ```python
    item_data = {
        'bom_item_id': bom_item.bom_item_id,
        'quantity': bom_item.quantity,
        'description': bom_item.description,
        'matches': [match_data] # Wrap match_data in a list
    }
    ```
4.  Append `item_data` to the `bom_items_with_matches` list.
```

**Prompt 7: Final Integration and Review**

```text
Final checks for `pcb_part_finder/core/processor.py`:

1.  Ensure the `for bom_item in bom_items:` loop correctly iterates through all items, and the logic from steps 2-6 is contained within this loop.
2.  Verify that the `save_bom_results_to_db(project_id, bom_items_with_matches, db)` call happens *after* the loop finishes.
3.  Make sure the `project` variable (containing `project_notes`) is correctly accessed within the loop (it's returned alongside `bom_items` from `load_project_data_from_db`).
4.  Review all logging messages (`logger.error`, `logger.warning`, `logger.info`) for clarity and appropriateness. Ensure necessary details like `bom_item_id` are included in logs.
5.  Confirm that the `status` variable correctly tracks the outcome for each item throughout the steps and determines the final `match_data` structure.
6. Add necessary default values (like empty strings or None) to `match_data` for failure statuses if `save_bom_results_to_db` requires certain keys to always be present, even if empty. Check the `output_writer.py` `save_bom_results_to_db` function's handling of `match_data` keys when creating `Component` and `BomItemMatch` to ensure compatibility.
```

These prompts break the task into manageable chunks, building the desired functionality incrementally within `processor.py`. Each prompt builds on the previous one, leading to the final integrated solution.
