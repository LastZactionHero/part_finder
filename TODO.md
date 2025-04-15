# TODO Checklist: PCB Part Selection Streamlining Tool

## Iteration 1: Core Setup & Input/Output (Prompt 1-3)

### Step 1.1: Project & CLI Setup (Prompt 1)
- [x] Create project directory structure (`pcb_part_finder/`, `tests/`, `data/`).
- [x] Initialize Python virtual environment (`venv`).
- [x] Install base libraries: `python-dotenv`, `argparse`.
- [x] Create `requirements.txt` and add initial libraries.
- [x] Create `.env` file and add placeholders for `MOUSER_API_KEY` and `ANTHROPIC_API_KEY`.
- [x] Implement `pcb_part_finder/main.py` with `argparse` for `--input` and `--notes`.
- [x] Add file existence validation for input arguments in `main.py`.
- [x] Implement `.env` loading in `main.py`.
- [x] Install `pytest`. Update `requirements.txt`.
- [x] Create `tests/test_main.py`.
- [x] Write unit tests for CLI argument parsing (valid, missing, invalid paths).

### Step 1.2: Input Loading (Prompt 2)
- [x] Create `pcb_part_finder/data_loader.py`.
- [x] Define `DataLoaderError` exception in `data_loader.py`.
- [x] Implement `load_notes(filepath)` function in `data_loader.py` with error handling.
- [x] Implement `load_input_csv(filepath)` function using `csv.DictReader` in `data_loader.py` with error handling.
- [x] Integrate calls to `load_notes` and `load_input_csv` into `main.py` with `try...except DataLoaderError`.
- [x] Add temporary print statements in `main.py` to verify loading.
- [x] Create `tests/test_data_loader.py`.
- [x] Write unit tests for `load_notes` (success, file not found).
- [x] Write unit tests for `load_input_csv` (success, file not found, bad format).
- [x] Update `tests/test_main.py` to mock data loading functions and test integration/error handling in `main`.

### Step 1.3: Output CSV Setup & Writing (Prompt 3)
- [X] Create `pcb_part_finder/output_writer.py`.
- [X] Define `OutputWriterError` exception in `output_writer.py`.
- [X] Define `OUTPUT_HEADER` list constant in `output_writer.py`.
- [X] Implement `initialize_output_csv(filepath, header)` function in `output_writer.py`.
- [X] Implement `append_row_to_csv(filepath, data_dict, header)` function using `csv.DictWriter` in `output_writer.py`.
- [X] Define `output_filename` in `main.py`.
- [X] Call `initialize_output_csv` in `main.py` (handle errors).
- [X] Add temporary loop in `main.py` to call `append_row_to_csv` with dummy data (handle errors).
- [X] Create `tests/test_output_writer.py`.
- [X] Write unit tests for `initialize_output_csv` (check header, error handling).
- [x] Write unit tests for `append_row_to_csv` (check append, multi-append, error handling).

## Iteration 2: Mouser API Interaction (Prompt 4-5)

### Step 2.1: Mouser API Wrapper (Keyword Search) (Prompt 4)
- [ ] Install `requests`. Update `requirements.txt`.
- [ ] Create `pcb_part_finder/mouser_api.py`.
- [ ] Define `MOUSER_API_BASE_URL` constant in `mouser_api.py`.
- [ ] Implement `get_api_key()` helper in `mouser_api.py`.
- [ ] Define `MouserApiError` exception in `mouser_api.py`.
- [ ] Implement `search_mouser_by_keyword(keyword, records)` function in `mouser_api.py`.
- [ ] Add API key handling, request construction (POST), `requests.post` call with timeout/error handling.
- [ ] Add status code checking (200, 429, other) and JSON parsing/error handling.
- [ ] Implement logic to extract `['SearchResults']['Parts']` list or return `[]`.
- [ ] Add temporary call in `main.py` to test `search_mouser_by_keyword` (within `try...except`).
- [ ] Install `pytest-mock`. Update `requirements.txt`.
- [ ] Create `tests/test_mouser_api.py`.
- [ ] Write unit tests for `search_mouser_by_keyword` mocking `requests.post` (success, no results, invalid JSON, 429, other errors, network error, API key missing).

### Step 2.2: Mouser API Wrapper (MPN Search/Detail Fetch) (Prompt 5)
- [ ] Implement `search_mouser_by_mpn(mpn)` function in `mouser_api.py`.
- [ ] Determine correct Mouser endpoint and method (e.g., Part Search POST).
- [ ] Add API key handling, request construction, `requests` call with timeout/error handling.
- [ ] Add status code checking, JSON parsing/error handling.
- [ ] Implement logic to extract details from the *first* part in `['SearchResults']['Parts']`.
- [ ] Extract specific fields: Mouser#, MPN, Manufacturer, Description, Datasheet URL.
- [ ] Implement robust Price extraction logic (find qty 1 or lowest break).
- [ ] Implement robust Availability extraction logic (In Stock vs Lead Time).
- [ ] Return structured dictionary on success, `None` on failure/not found.
- [ ] Remove temporary keyword search call from `main.py`.
- [ ] Write unit tests in `tests/test_mouser_api.py` for `search_mouser_by_mpn` mocking `requests` (success, multiple results->first, price/avail parsing variations, not found, API errors, network error, invalid JSON, API key missing).

## Iteration 3: LLM Integration (Search Term Generation) (Prompt 6)

### Step 3.1: Anthropic API Wrapper (Prompt 6)
- [ ] Install `anthropic`. Update `requirements.txt`.
- [ ] Create `pcb_part_finder/llm_handler.py`.
- [ ] Define `LlmApiError` exception in `llm_handler.py`.
- [ ] Implement `get_anthropic_client()` helper in `llm_handler.py`.
- [ ] Implement `get_llm_response(prompt, model, temperature)` function in `llm_handler.py`.
- [ ] Add API key handling, Anthropic client initialization.
- [ ] Construct message payload for Anthropic API.
- [ ] Call `client.messages.create` with error handling (`anthropic.APIError`).
- [ ] Extract text content from response.
- [ ] Create `tests/test_llm_handler.py`.
- [ ] Write unit tests for `get_llm_response` mocking `anthropic.Anthropic().messages.create` (success, API error, API key missing).

### Step 3.2: Search Term Prompt Formatting & Generation (Prompt 6)
- [ ] Implement `format_search_term_prompt(part_info)` function in `llm_handler.py`.
- [ ] Implement `parse_search_terms(llm_response)` helper function in `llm_handler.py`.
- [ ] Write unit tests in `tests/test_llm_handler.py` for `format_search_term_prompt` (check output string).
- [ ] Write unit tests in `tests/test_llm_handler.py` for `parse_search_terms` (valid, edge cases, None).

## Iteration 4: LLM Integration (Evaluation) & Core Logic (Prompt 7-8)

### Step 4.1: Evaluation Prompt Formatting & MPN Extraction (Prompt 7)
- [ ] Implement `format_evaluation_prompt(part_info, project_notes, selected_parts, mouser_results)` function in `llm_handler.py`.
- [ ] Ensure correct formatting of `selected_parts` list within the prompt.
- [ ] Ensure clear formatting of `mouser_results` list within the prompt.
- [ ] Implement `extract_mpn_from_eval(llm_response)` function using regex in `llm_handler.py`.
- [ ] Write unit tests in `tests/test_llm_handler.py` for `format_evaluation_prompt` (check output string with sample data).
- [ ] Write unit tests in `tests/test_llm_handler.py` for `extract_mpn_from_eval` (valid pattern, no pattern, empty content, None input).

### Step 4.2: Integrate Core Loop Logic (Part 1) (Prompt 8)
- [ ] Modify `pcb_part_finder/main.py`.
- [ ] Import necessary functions and modules.
- [ ] Configure basic `logging`.
- [ ] Initialize `selected_parts = []` before loop.
- [ ] Implement main processing loop `for input_row in ...`.
- [ ] Inside loop: Log start of row processing.
- [ ] Inside loop: Implement LLM Pass 1 block (`format_search_term_prompt`, `get_llm_response`, `parse_search_terms`).
- [ ] Inside loop: Add `try...except LlmApiError` around LLM Pass 1. Handle error (log, write status="LLM Search Term Failed", continue).
- [ ] Inside loop: Add fallback logic if `parse_search_terms` returns empty.
- [ ] Inside loop: Implement Mouser Search block (init `all_mouser_results`, loop `search_terms`, call `search_mouser_by_keyword`).
- [ ] Inside loop: Add `try...except MouserApiError` around `search_mouser_by_keyword`. Handle error (log, continue/break). Add `time.sleep`.
- [ ] Inside loop: Check if `all_mouser_results` is empty after loop. Handle (log, write status="No Mouser Matches", continue).
- [ ] Inside loop: Implement LLM Pass 2 block (`format_evaluation_prompt`, `get_llm_response`).
- [ ] Inside loop: Add `try...except LlmApiError` around LLM Pass 2. Handle error (log, write status="LLM Evaluation API Failed", continue).
- [ ] Inside loop: Call `extract_mpn_from_eval`.
- [ ] Inside loop: Check if `extracted_mpn` is `None`. Handle (log, write status="LLM Selection Failed", continue).
- [ ] Inside loop: Add placeholder log for successful MPN extraction.
- [ ] Update `tests/test_main.py` with integration tests (using mocks) for the new logic branches (No Mouser Matches, LLM Selection Failed, API errors). Verify logging with `caplog`.

## Iteration 5: Tying it Together & Final Output (Prompt 9)

### Step 5.1: Integrate Mouser Detail Fetch & Success Path (Prompt 9)
- [ ] Modify `pcb_part_finder/main.py` loop after successful MPN extraction.
- [ ] Implement Mouser Detail Fetch block (call `search_mouser_by_mpn(extracted_mpn)`).
- [ ] Add `try...except MouserApiError`. Handle error (log, write status="Mouser Detail Fetch Failed", continue). Add `time.sleep`.
- [ ] Check if `part_details` is `None`. Handle (log, write status="Mouser Detail Not Found", continue).
- [ ] Implement Success Path:
    - [ ] Log success.
    - [ ] Set `match_status = "Success"`.
    - [ ] Prepare `output_data` dict combining `input_row` and `part_details`.
    - [ ] Call `append_row_to_csv`. Handle `OutputWriterError`.
    - [ ] Append `{ 'Description': ..., 'ManufacturerPartNumber': ... }` to `selected_parts` list.
- [ ] Ensure `selected_parts` list is correctly used in subsequent loop iterations.
- [ ] Add final "Processing complete" log message after the loop.
- [ ] Update `tests/test_main.py` with integration tests (using mocks) for the success path, detail fetch failure path, and detail not found path. Verify CSV output and `selected_parts` update/usage.

## Iteration 6: Error Handling, Logging & Final Touches (Prompt 10)

### Step 6.1: Robust Error Handling & Logging Review (Prompt 10)
- [ ] Review all `try...except` blocks in `main.py` for completeness.
- [ ] Review handling of file operation errors.
- [ ] Verify logging covers key steps, decisions, and errors adequately.
- [ ] Review Mouser rate limit handling (is current logging/continuation sufficient?).
- [ ] Consider adding a `logging.FileHandler` to `main.py` for persistent logs.

### Step 6.2: Final Polish (Prompt 10)
- [ ] Add comprehensive docstrings to all functions in all `.py` files.
- [ ] Add type hints to all function signatures in all `.py` files.
- [ ] Run static analysis tools (e.g., `flake8`, `mypy`) and address issues.
- [ ] Create `README.md` file in project root.
- [ ] Add content to `README.md`: Title, Description, Setup, Configuration (`.env`), Usage, Input Format, Output Format.
- [ ] Run `pip freeze > requirements.txt` to finalize dependencies.
- [ ] Perform a final manual test run with sample input CSV and notes file. Verify `bom_matched.csv` output.