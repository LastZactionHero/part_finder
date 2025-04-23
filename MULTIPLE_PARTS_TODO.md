Okay, here is a todo list based on the steps we outlined. You can use this to track your progress:

**Phase 1: Database Setup**

* [x] **SQL:** Modify `init.sql` to include the new tables and fields. Don't worry about migrations
* [x] **Define Model:** Create the `PotentialBomMatch` SQLAlchemy model in `pcb_part_finder/db/models.py`.
* [x] **Define Relationships:** Add the necessary `relationship` attributes to both `PotentialBomMatch` and `BomItem` in `pcb_part_finder/db/models.py`.
* [ ] **DB Migration:** Generate and apply the database migration (e.g., using Alembic) to create the `potential_bom_matches` table.
* [x] **Create CRUD Functions:** Implement `create_potential_bom_match` and `get_potential_matches_for_bom_item` in `pcb_part_finder/db/crud.py`.

**Phase 2: LLM Interaction Update**

* [x] **Modify LLM Prompt:** Update `format_evaluation_prompt` in `pcb_part_finder/core/llm_handler.py` to request 5 diverse candidates in JSON format.
* [x] **Create LLM Parser:** Implement `parse_potential_matches_json` in `pcb_part_finder/core/llm_handler.py` to handle the new JSON response.
* [x] **Remove Old Parser:** Comment out or remove the old `extract_mpn_from_eval` function.

**Phase 3: Core Processing Logic Adaptation**

* [x] **Update Worker (LLM Call):** Modify `_process_single_bom_item` in `pcb_part_finder/core/processor.py` to use the new `parse_potential_matches_json` parser.
* [x] **Update Worker (Process Matches):** Modify `_process_single_bom_item` to loop through the parsed potential matches, call `create_potential_bom_match` for each valid one, and commit the session.
* [x] **Update Worker (Status Logic):** Review and adjust all status assignment logic within `_process_single_bom_item` to reflect the new workflow outcomes (e.g., `potential_matches_saved`, `db_save_error`).
* [x] **Remove Old Logic:** Remove the old code related to handling a single `chosen_mpn` and creating a single `BomItemMatch`.

**Phase 4: API Layer Integration**

* [x] **Define API Schema:** Create the `PotentialMatch` Pydantic schema in `pcb_part_finder/api/schemas.py`.
* [x] **Update API Schema:** Add the `potential_matches: Optional[List[PotentialMatch]]` field to the `MatchedComponent` schema in `pcb_part_finder/api/schemas.py`. Adjust other fields as needed (Optional, descriptions).
* [x] **Modify API Endpoint (Fetch):** Update the `get_project` endpoint in `pcb_part_finder/api/projects.py` to call `get_potential_matches_for_bom_item`.
* [x] **Modify API Endpoint (Populate):** Add logic within the `get_project` endpoint to loop through fetched potential matches, look up corresponding component details using `get_component_by_mpn`, and populate the `PotentialMatch` schema instances for the API response. Adjust how the overall `match_status` for the `MatchedComponent` is determined.

**Phase 5: Frontend Display**

* [ ] **Modify JS (Handle List):** Update `updateResultsTable` in `pcb_part_finder/web/static/script.js` to create the primary row for the original BOM item and check for the `potential_matches` list.
* [ ] **Modify JS (Generate Rows):** Add the nested loop in `updateResultsTable` to generate the secondary rows for each potential match, populating cells with data from the `potentialMatch` object.
* [ ] **Update HTML Headers:** Adjust the `<thead>` in `pcb_part_finder/web/templates/index.html` to match the new data presentation.
* [ ] **Define CSS Styles:** Add CSS rules in `pcb_part_finder/web/static/style.css` for `.potential-match-row` and selection state classes (`.status-proposed`, etc.).

**Phase 6: Testing**

* [ ] **Manual Testing:** Perform thorough manual testing of the end-to-end flow as outlined in the testing plan guidance.

**Current Status:**
- Completed Phases 1-4
- Ready to begin Phase 5 (Frontend Display)
- Next step: Update the JavaScript code to handle and display potential matches in the results table