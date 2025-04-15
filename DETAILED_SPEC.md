Okay, let's break down the PCB Part Selection Streamlining Tool project.

## Detailed Blueprint

Here's a more granular step-by-step plan derived from the specification:

1.  **Project Setup:**
    * Create project directory structure (e.g., `pcb_part_finder/`, `tests/`, `data/`).
    * Initialize a virtual environment (`python -m venv venv`).
    * Install necessary base libraries (`pip install requests python-dotenv anthropic`). We'll add testing libraries later.
    * Set up configuration management for API keys (e.g., using `.env` file and `python-dotenv`). Store `MOUSER_API_KEY` and `ANTHROPIC_API_KEY`.

2.  **Command-Line Interface (CLI):**
    * Implement argument parsing using `argparse`.
    * Define arguments: `--input` (required, path to input CSV), `--notes` (required, path to notes file).
    * Validate that the provided file paths exist upon startup.

3.  **Input Data Loading:**
    * Implement a function to read the project notes file into a string.
    * Implement a function to read the input CSV file using the `csv` module (`csv.DictReader`). Handle potential `FileNotFoundError` and basic CSV format errors (e.g., missing header). Store data as a list of dictionaries.

4.  **Output CSV Setup:**
    * Define the exact output CSV header row as specified.
    * Implement a function to initialize the output file (`bom_matched.csv`), opening it in write mode and writing *only* the header row. Handle potential `IOError`.

5.  **Mouser API Interaction (Wrapper):**
    * Create a dedicated module/class for Mouser API interactions.
    * Implement a function `search_mouser_by_keyword(keyword, records=5)`:
        * Takes a search keyword and number of records.
        * Constructs the API request URL for `/search/keyword`.
        * Includes the `apiKey` in the request payload/headers as required by Mouser.
        * Uses the `requests` library to make the POST request.
        * Handles potential `requests` exceptions (timeout, connection error).
        * Checks the HTTP status code of the response. Raises an exception for non-200 codes (log the error detail). Specifically check for rate limiting errors (e.g., 429 Too Many Requests) and potentially terminate.
        * Parses the JSON response. Handles potential `JSONDecodeError`.
        * Extracts relevant data (Parts list) from the response structure.
        * Returns the list of parts found or an empty list if none.
    * Implement a function `search_mouser_by_mpn(mpn)`:
        * Takes a Manufacturer Part Number (MPN).
        * Constructs the API request URL for `/search/partnumber` (or `/search/keyword` if more appropriate for getting single-part details based on MPN).
        * Includes the `apiKey`.
        * Makes the POST request using `requests`.
        * Handles errors and parses JSON as above.
        * Extracts detailed information for the *single* matching part (Mouser Part Number, Manufacturer Name, Full Description, Datasheet URL, Price, Availability). Note: Need to carefully parse the price and availability structures from the Mouser response.
        * Returns a dictionary containing the detailed part information or `None` if not found or an error occurs.

6.  **Anthropic API Interaction (Wrapper):**
    * Create a dedicated module/class for Anthropic API interactions.
    * Load the `ANTHROPIC_API_KEY` securely.
    * Implement a function `get_llm_response(prompt, model="claude-3-sonnet-20240229", temperature=0.2)`:
        * Takes the prompt string, model name, and temperature.
        * Initializes the Anthropic client.
        * Constructs the API request payload according to Anthropic's message API format.
        * Uses the `anthropic` library to make the API call.
        * Handles potential API exceptions (authentication, rate limiting, server errors). Log errors.
        * Extracts the text content from the response.
        * Returns the text content or `None` if an error occurred.

7.  **LLM Prompt Formatting:**
    * Implement a function `format_search_term_prompt(part_info)` that takes a dictionary representing a row from the input CSV and returns the formatted prompt string for LLM Pass 1 (Search Term Generation).
    * Implement a function `format_evaluation_prompt(part_info, project_notes, selected_parts, mouser_results)` that takes the input CSV row data, project notes string, list of previously selected parts dictionaries, and the aggregated list of Mouser search result dictionaries, and returns the formatted prompt string for LLM Pass 2 (Evaluation). Ensure Mouser results are formatted clearly within the prompt.

8.  **Core Processing Logic:**
    * Initialize the `selected_parts` list (empty).
    * Initialize the output CSV (call function from step 4).
    * Loop through each `part_row` dictionary read from the input CSV (from step 3).
        * **LLM Pass 1 (Search Terms):**
            * Format the prompt using `format_search_term_prompt(part_row)`.
            * Call `get_llm_response()` to get search term suggestions.
            * Parse the comma-separated search terms from the response. Handle cases where the LLM response is invalid or empty. Default to using `part_row['Possible MPN']` or `part_row['Description']` if generation fails.
        * **Mouser Search:**
            * Initialize an empty list `all_mouser_results`.
            * Loop through the generated `search_terms`:
                * Call `search_mouser_by_keyword(term)`.
                * If results are returned, append them to `all_mouser_results`. Handle potential API errors gracefully (log, continue to next term).
            * If `all_mouser_results` is empty after trying all terms:
                * Prepare output row data with original input + `Match Status` = "No Mouser Matches".
                * Write the row to the output CSV.
                * `continue` to the next `part_row`.
        * **LLM Pass 2 (Evaluation):**
            * Format the prompt using `format_evaluation_prompt(part_row, project_notes, selected_parts, all_mouser_results)`. Ensure `selected_parts` is formatted correctly.
            * Call `get_llm_response()` to get the evaluation.
            * Implement robust extraction logic (e.g., regex `r'\[ManufacturerPartNumber:(.*?)\]'`) to get the MPN from the LLM response.
            * If extraction fails or the LLM response is invalid:
                * Prepare output row data with original input + `Match Status` = "LLM Selection Failed".
                * Write the row to the output CSV.
                * `continue` to the next `part_row`.
        * **Mouser Detail Fetch:**
            * Call `search_mouser_by_mpn(extracted_mpn)`. Handle potential API errors.
            * If `part_details` are successfully retrieved:
                * Prepare output row data combining `part_row` data and `part_details`, setting `Match Status` = "Success".
                * Write the row to the output CSV.
                * Append `{'Description': part_row['Description'], 'ManufacturerPartNumber': extracted_mpn}` to the `selected_parts` list.
            * If `part_details` retrieval fails (e.g., MPN not found despite LLM suggesting it, or API error):
                * Prepare output row data with original input + `Match Status` = "Mouser Detail Fetch Failed". (Or potentially retry LLM eval? For now, report failure).
                * Write the row to the output CSV.
        * Add logging for each major step within the loop (e.g., "Processing row X", "Generated search terms", "Found Y Mouser results", "LLM selected MPN Z").

9.  **Output CSV Writing:**
    * Implement a function `append_to_output_csv(filepath, data_dict, header)` that takes the output CSV path, a dictionary containing the data for one row, and the expected header list.
    * Opens the file in append mode (`'a'`).
    * Uses `csv.DictWriter` to write the row, ensuring columns align with the header. Handle potential `IOError`.

10. **Testing:**
    * Install testing framework (`pip install pytest pytest-mock`).
    * Write unit tests for:
        * CLI argument parsing (using mocks for file existence).
        * Input data loading (CSV and notes).
        * Output CSV initialization and appending (check file content).
        * Mouser API wrappers (using `pytest-mock` to mock `requests.post` and simulate various responses: success, no results, errors, rate limits).
        * Anthropic API wrapper (using `pytest-mock` to mock `anthropic.Anthropic().messages.create` and simulate various responses).
        * LLM prompt formatting functions (verify output string structure).
        * MPN extraction logic from LLM response.
        * Core processing logic (mocking API calls and file I/O, testing different branches like "No Mouser Matches", "LLM Selection Failed", "Success").
    * Write integration tests (optional, requires real API keys and careful management): Test the flow with 1-2 rows, mocking only where necessary (e.g., limiting Mouser results) or using dedicated test keys if available.

11. **Refinement:**
    * Add logging throughout the application using the `logging` module.
    * Refine error messages and handling based on testing.
    * Ensure proper resource cleanup (e.g., file handles, though `with open(...)` handles this).
    * Add docstrings and type hints to functions.
    * Create a `requirements.txt` file (`pip freeze > requirements.txt`).
    * Create a README explaining setup and usage.

## Iterative Chunks and Steps Breakdown

Let's break the blueprint into smaller, testable steps suitable for generating prompts.

**Iteration 1: Core Setup & Input/Output**

* **Step 1.1: Project & CLI Setup:**
    * Goal: Basic project structure, virtual env, install `argparse`, `python-dotenv`. Implement CLI parsing for `--input` and `--notes`. Validate file existence.
    * Testing: Unit tests for `argparse` (valid args, missing args, invalid paths).
* **Step 1.2: Input Loading:**
    * Goal: Function to read notes file. Function to read input CSV using `csv.DictReader` into a list of dictionaries. Basic error handling for file not found/bad format.
    * Testing: Unit tests with sample valid/invalid CSVs and notes files. Test error handling.
* **Step 1.3: Output CSV Setup & Writing:**
    * Goal: Define output header. Function to initialize output CSV (write header). Function to append a dictionary row using `csv.DictWriter`.
    * Testing: Unit tests to check header writing and row appending produces correct CSV content.

**Iteration 2: Mouser API Interaction**

* **Step 2.1: Mouser API Wrapper (Keyword Search):**
    * Goal: Install `requests`. Create Mouser API module. Implement `search_mouser_by_keyword`. Handle API key via environment variable (`dotenv`). Basic request/response handling, JSON parsing, error checking (status code, request exceptions). Extract 'Parts' list.
    * Testing: Unit tests mocking `requests.post`. Test success (parsing parts), API errors (4xx, 5xx), request exceptions, rate limit (429), no results found.
* **Step 2.2: Mouser API Wrapper (MPN Search):**
    * Goal: Implement `search_mouser_by_mpn`. Similar request/response/error handling. Focus on extracting *detailed* info for a *single* part (Mouser#, Manufacturer, Desc, Datasheet, Price, Availability). Return a structured dictionary or `None`.
    * Testing: Unit tests mocking `requests.post`. Test success (parsing details), MPN not found, API errors.

**Iteration 3: LLM Integration (Search Term Generation)**

* **Step 3.1: Anthropic API Wrapper:**
    * Goal: Install `anthropic`. Create LLM API module. Implement `get_llm_response`. Handle API key via environment variable. Basic API call using `anthropic` client, error handling (API exceptions), extract text content.
    * Testing: Unit tests mocking `anthropic.Anthropic().messages.create`. Test success, API errors.
* **Step 3.2: Search Term Prompt Formatting & Generation:**
    * Goal: Implement `format_search_term_prompt`. Integrate with `get_llm_response` in the main script loop (placeholder for now). Parse comma-separated terms from LLM response. Add basic fallback if LLM fails (e.g., use 'Possible MPN').
    * Testing: Unit test for `format_search_term_prompt`. Unit test for parsing LLM response string. Integration test piece (in main loop context) mocking `get_llm_response`.

**Iteration 4: LLM Integration (Evaluation) & Core Logic**

* **Step 4.1: Evaluation Prompt Formatting & MPN Extraction:**
    * Goal: Implement `format_evaluation_prompt`. Implement regex/logic to extract `[ManufacturerPartNumber:XXXXX]` from LLM response string.
    * Testing: Unit test for `format_evaluation_prompt`. Unit test for MPN extraction from various sample strings (valid, invalid, missing).
* **Step 4.2: Integrate Core Loop Logic (No Mouser -> LLM Eval -> MPN Extract):**
    * Goal: In the main script loop: call LLM 1 (Step 3.2), loop through terms calling `search_mouser_by_keyword` (Step 2.1), aggregate results. Handle "No Mouser Matches" case (write output, continue). Format eval prompt (Step 4.1), call LLM 2 (`get_llm_response`, Step 3.1), extract MPN (Step 4.1). Handle "LLM Selection Failed" case (write output, continue).
    * Testing: Integration tests (mocking API calls heavily) for the flow: No results -> correct output; Results -> LLM Eval -> Failed extraction -> correct output.

**Iteration 5: Tying it Together & Final Output**

* **Step 5.1: Integrate Mouser Detail Fetch & Success Path:**
    * Goal: After successful MPN extraction (Step 4.2), call `search_mouser_by_mpn` (Step 2.2). If details are fetched, format the full "Success" output row. Append selected part info to `selected_parts` list. Write row to output CSV. Handle "Mouser Detail Fetch Failed" case. Ensure `selected_parts` list is passed correctly to subsequent `format_evaluation_prompt` calls.
    * Testing: Integration tests (mocking APIs) for the success path and detail fetch failure path. Verify `selected_parts` list updates and is used in subsequent loop iterations. Check final output CSV row format for "Success".

**Iteration 6: Error Handling, Logging & Final Touches**

* **Step 6.1: Robust Error Handling & Logging:**
    * Goal: Add `try...except` blocks around all API calls and critical parsing steps within the main loop. Implement logging using the `logging` module (configure basic file/console logging). Log key events and errors. Ensure script terminates gracefully or continues processing rows based on error type. Specifically handle Mouser rate limiting termination.
    * Testing: Review code for comprehensive error handling. Add tests simulating specific exceptions during API calls/parsing. Check log output.
* **Step 6.2: Final Polish:**
    * Goal: Add docstrings, type hints. Create `requirements.txt`. Create README.md.
    * Testing: Code review, static analysis (e.g., `flake8`, `mypy`). Manual execution test with sample data.

This breakdown provides small, manageable steps, each building on the last, with clear testing goals for each stage.

## Prompts for Code-Generation LLM

Here are the prompts based on the iterative steps, designed for TDD where applicable.

---

**Prompt 1: Project Setup & CLI**

```text
Objective: Set up the basic Python project structure and implement command-line argument parsing for a PCB part selection tool.

Tasks:
1.  Assume a standard project layout (`pcb_part_finder/` for code, `tests/` for tests, `.env` for secrets).
2.  Create a Python script `main.py` inside `pcb_part_finder/`.
3.  Install necessary libraries: `pip install python-dotenv argparse`. Create a `requirements.txt`.
4.  In `main.py`, use the `argparse` module to:
    * Define two required command-line arguments:
        * `--input`: Path to the input CSV file.
        * `--notes`: Path to the project notes text file.
    * Parse the arguments in a `main()` function.
    * Add basic validation *after* parsing to check if the provided file paths exist using `os.path.exists`. If not, print an informative error message and exit (`sys.exit(1)`).
5.  Load environment variables from a `.env` file using `dotenv.load_dotenv()` at the beginning of the script. Assume `.env` might contain `MOUSER_API_KEY` and `ANTHROPIC_API_KEY` (we won't use them yet).
6.  Create a `tests/` directory.
7.  Install `pytest`: `pip install pytest`. Update `requirements.txt`.
8.  Write unit tests in `tests/test_main.py` using `pytest` (and potentially `unittest.mock` if needed to mock `os.path.exists` or `sys.exit`) to verify:
    * Correct parsing of valid arguments.
    * Error handling for missing arguments.
    * Error handling and exit for non-existent file paths passed via arguments.

Provide the complete `pcb_part_finder/main.py` script and the `tests/test_main.py` script. Include the updated `requirements.txt`.
```

---

**Prompt 2: Input Data Loading**

```text
Objective: Implement functions to load data from the input CSV and project notes file specified via CLI arguments. Build upon the code from Prompt 1.

Tasks:
1.  Modify `pcb_part_finder/main.py`.
2.  Create a new file `pcb_part_finder/data_loader.py`.
3.  In `data_loader.py`, implement a function `load_notes(filepath: str) -> str`:
    * Takes the notes file path as input.
    * Reads the entire content of the file.
    * Handles `FileNotFoundError` and `IOError`, raising a custom exception or returning `None` / empty string with an error logged (choose one approach, be consistent). For now, let's raise a custom exception like `DataLoaderError`. Define this simple exception class.
    * Returns the file content as a single string.
4.  In `data_loader.py`, implement a function `load_input_csv(filepath: str) -> list[dict]`:
    * Takes the input CSV file path.
    * Uses the `csv.DictReader` to read the CSV. Assumes UTF-8 encoding.
    * Assumes the header row exists (`Qty`, `Description`, `Possible MPN`, `Package`, `Notes/Source` are expected but don't hardcode validation for *these specific* headers yet, just read whatever headers are present).
    * Handles `FileNotFoundError`, `IOError`, and potential `csv.Error` during reading (e.g., poorly formatted CSV). Raise `DataLoaderError` on failure.
    * Returns the data as a list of dictionaries, where each dictionary represents a row.
5.  In `main.py`, within the `main()` function (after argument parsing and validation from Prompt 1):
    * Call `load_notes()` and `load_input_csv()` using the parsed file paths.
    * Wrap these calls in a `try...except DataLoaderError` block. Print an error and exit if loading fails.
    * For now, just print the loaded notes and the number of rows loaded from the CSV to verify.
6.  Update `tests/test_data_loader.py` (create this file):
    * Write unit tests for `load_notes` using `pytest`. Test successful reading, file not found, and potentially permission errors (if mockable). Use temporary files (`tmp_path` fixture in pytest).
    * Write unit tests for `load_input_csv`. Test successful reading of a sample CSV, file not found, and a poorly formatted CSV. Use temporary files. Check the structure of the returned list of dicts.
7.  Update `tests/test_main.py` to mock `data_loader.load_notes` and `data_loader.load_input_csv` to test the integration within `main()` and the error handling there.

Provide the complete `pcb_part_finder/data_loader.py`, the updated `pcb_part_finder/main.py`, and the new `tests/test_data_loader.py`.
```

---

**Prompt 3: Output CSV Setup & Writing**

```text
Objective: Implement functions to set up the output CSV file and append data rows to it. Build upon the code from Prompt 2.

Tasks:
1.  Modify `pcb_part_finder/main.py`.
2.  Create a new file `pcb_part_finder/output_writer.py`.
3.  In `output_writer.py`, define the expected output header list: `OUTPUT_HEADER = ['Qty', 'Description', 'Possible MPN', 'Package', 'Notes/Source', 'Mouser Part Number', 'Manufacturer Part Number', 'Manufacturer Name', 'Mouser Description', 'Datasheet URL', 'Price', 'Availability', 'Match Status']`.
4.  In `output_writer.py`, implement a function `initialize_output_csv(filepath: str, header: list[str])`:
    * Takes the output file path (e.g., `bom_matched.csv`) and the header list.
    * Opens the file in write mode (`'w'`), overwriting existing content. Ensure `newline=''` is used.
    * Uses `csv.writer` to write the header row.
    * Handles `IOError` during file opening/writing, raising a custom `OutputWriterError`. Define this simple exception class.
5.  In `output_writer.py`, implement a function `append_row_to_csv(filepath: str, data_dict: dict, header: list[str])`:
    * Takes the output file path, a dictionary representing the row data, and the expected header list.
    * Opens the file in append mode (`'a'`), `newline=''`.
    * Uses `csv.DictWriter` with the provided `header` to write the `data_dict`. Ensure `DictWriter` is created with the correct `fieldnames=header`.
    * Handles `IOError` and potential `ValueError` (if `data_dict` is missing keys from the header), raising `OutputWriterError`.
6.  In `main.py`, within the `main()` function:
    * Define the output filename: `output_filename = "bom_matched.csv"`.
    * Call `initialize_output_csv()` once before processing any input rows. Handle potential `OutputWriterError`.
    * For demonstration purposes, after loading the input CSV, loop through the first 1-2 `input_rows`, create a dummy `output_data` dictionary for each (copying input fields and adding placeholder values for Mouser fields + a 'Match Status'), and call `append_row_to_csv()`. Handle potential `OutputWriterError`.
7.  Update `requirements.txt` if any new standard libraries were implicitly added (like `csv`, which is built-in).
8.  Create `tests/test_output_writer.py`:
    * Write unit tests for `initialize_output_csv`. Use `tmp_path` to create a temp file and verify its header content. Test error handling (e.g., mock `open` to raise `IOError`).
    * Write unit tests for `append_row_to_csv`. Use `tmp_path`. Test appending a valid row, check content. Test appending multiple rows. Test error handling (IOError, missing keys in data_dict).

Provide the complete `pcb_part_finder/output_writer.py`, the updated `pcb_part_finder/main.py`, and the new `tests/test_output_writer.py`.
```

---

**Prompt 4: Mouser API Wrapper (Keyword Search)**

```text
Objective: Implement a wrapper function to interact with the Mouser API's keyword search endpoint. Build upon Prompt 3.

Tasks:
1.  Install `requests`: `pip install requests`. Update `requirements.txt`.
2.  Create a new file `pcb_part_finder/mouser_api.py`.
3.  In `mouser_api.py`:
    * Import `os`, `requests`, `json`.
    * Define a constant `MOUSER_API_BASE_URL = "https://api.mouser.com/api/v1.0"`.
    * Implement a function `get_api_key() -> str | None` to retrieve the Mouser API key from the environment variable `MOUSER_API_KEY`. Return `None` if not found.
    * Define a custom exception `MouserApiError(Exception)`.
    * Implement the function `search_mouser_by_keyword(keyword: str, records: int = 5) -> list[dict]`:
        * Get the API key using `get_api_key()`. If `None`, raise `MouserApiError("Mouser API key not found")`.
        * Construct the URL: `f"{MOUSER_API_BASE_URL}/search/keyword"`.
        * Construct the request payload (JSON body) as specified by the Mouser API documentation for keyword search. Include the `keyword`, `records`, and any other necessary parameters (e.g., `startingRecord=0`).
        * Use `requests.post` to make the request. Include `headers={'Content-Type': 'application/json'}`. Pass the payload as `json=payload_dict`. Add a reasonable timeout (e.g., 15 seconds).
        * Wrap the `requests.post` call in a `try...except requests.exceptions.RequestException as e:` block. Raise `MouserApiError(f"Network error: {e}")` in case of connection/timeout errors.
        * Check the response status code (`response.status_code`):
            * If 200: Parse the JSON using `response.json()`. Handle potential `JSONDecodeError` (raise `MouserApiError`). Extract the list of parts from the response structure (typically under `['SearchResults']['Parts']`). Return this list. If `['SearchResults']` or `['Parts']` is missing or `None`, return an empty list `[]`.
            * If 429 (Too Many Requests): Raise `MouserApiError("Mouser API rate limit exceeded.")`.
            * For any other non-200 status code: Raise `MouserApiError(f"Mouser API error: {response.status_code} - {response.text}")`.
4.  In `main.py`, temporarily modify the loop to call `search_mouser_by_keyword` for the `Description` field of the first input row. Print the results. Wrap the call in a `try...except MouserApiError`. (This is just for basic integration check, will be replaced later). Make sure `dotenv.load_dotenv()` is called early.
5.  Install `pytest-mock`: `pip install pytest-mock`. Update `requirements.txt`.
6.  Create `tests/test_mouser_api.py`:
    * Write unit tests for `search_mouser_by_keyword` using `pytest` and `mocker` (from `pytest-mock`).
    * Mock `requests.post`.
    * Test case: Successful response (200 OK) with valid part data -> verify returned list.
    * Test case: Successful response (200 OK) but no parts found -> verify returned empty list.
    * Test case: Response with invalid JSON -> verify `MouserApiError` is raised.
    * Test case: Response with 429 status code -> verify `MouserApiError` (rate limit) is raised.
    * Test case: Response with other error status code (e.g., 500) -> verify `MouserApiError` is raised.
    * Test case: `requests.post` raises `RequestException` -> verify `MouserApiError` (network error) is raised.
    * Test case: `MOUSER_API_KEY` environment variable not set -> verify `MouserApiError` (API key not found) is raised (use `mocker.patch.dict` on `os.environ`).

Provide the complete `pcb_part_finder/mouser_api.py`, the updated `pcb_part_finder/main.py`, `tests/test_mouser_api.py`, and `requirements.txt`.
```

---

**Prompt 5: Mouser API Wrapper (MPN Search/Detail Fetch)**

```text
Objective: Implement a Mouser API wrapper function to fetch detailed information for a specific Manufacturer Part Number (MPN). Build upon Prompt 4.

Tasks:
1.  Modify `pcb_part_finder/mouser_api.py`.
2.  Implement the function `search_mouser_by_mpn(mpn: str) -> dict | None`:
    * Get the API key. Raise `MouserApiError` if not found.
    * Construct the URL: `f"{MOUSER_API_BASE_URL}/search/partnumber?apiKey={{api_key}}"`. (Check Mouser docs - Part Search might be better than Keyword Search here, let's try Part Search first. It might be a GET request with URL parameters or a POST with a body - adapt accordingly. Let's assume POST for consistency with keyword search, check docs).
    * Construct the payload: Include the `mpn` in the format required by the specific Mouser endpoint (e.g., `{"SearchByPartRequest": {"mouserPartNumber": null, "manufacturerPartNumber": mpn}}`).
    * Use `requests.post` (or `get`) as determined above, with headers, JSON payload, and timeout.
    * Implement the same error handling as `search_mouser_by_keyword`: `RequestException`, status code checks (200, 429, other errors), `JSONDecodeError`, raising `MouserApiError` appropriately.
    * If successful (200 OK) and parts are found:
        * Assume the response contains a list of parts under `['SearchResults']['Parts']`.
        * **Crucially:** Since searching by MPN might still return multiple results (e.g., different packaging), try to find the *most likely* match or the first one. For simplicity now, just take the **first part** from the list `parts[0]`.
        * Extract the required detailed fields: `MouserPartNumber`, `ManufacturerPartNumber`, `Manufacturer`, `Description`, `DataSheetUrl`.
        * Extract Price: Look for pricing information (e.g., `PriceBreaks`). Find the price for quantity 1 or the lowest quantity break available. Format as a string (e.g., "$1.23"). Handle cases where price is missing.
        * Extract Availability: Look for availability information (e.g., `Availability`, `AvailabilityInStock`). Determine if it's "In Stock" or provide the lead time information if available. Format as a string. Handle cases where availability is missing.
        * Return a dictionary containing these extracted fields: `{'Mouser Part Number': ..., 'Manufacturer Part Number': ..., 'Manufacturer Name': ..., 'Mouser Description': ..., 'Datasheet URL': ..., 'Price': ..., 'Availability': ...}`.
    * If no parts are found in the response (empty list or key missing), return `None`.
    * If any error occurs during processing, raise `MouserApiError` or return `None` after logging the error (let's return `None` for this function on error/not found).
3.  In `main.py`, remove the temporary call to `search_mouser_by_keyword`. We will integrate this new function later.
4.  Update `tests/test_mouser_api.py`:
    * Write unit tests for `search_mouser_by_mpn` using `pytest` and `mocker`.
    * Mock the appropriate `requests` call (`post` or `get`).
    * Test case: Successful response with one part -> verify returned dictionary structure and sample values.
    * Test case: Successful response with multiple parts -> verify it extracts details from the *first* part.
    * Test case: Price/Availability parsing -> Test different structures in the mocked response (price breaks, simple price, in stock, lead time, missing data).
    * Test case: Successful response but no parts found -> verify returns `None`.
    * Test case: API errors (429, 500, etc.) -> verify returns `None`.
    * Test case: Network error (`RequestException`) -> verify returns `None`.
    * Test case: Invalid JSON response -> verify returns `None`.
    * Test case: API key missing -> verify `MouserApiError` is raised (consistency check - maybe this one should also return None for simplicity? Let's stick to raising for API key missing).

Provide the updated `pcb_part_finder/mouser_api.py` and `tests/test_mouser_api.py`.
```

---

**Prompt 6: Anthropic API Wrapper & Search Term Prompt**

```text
Objective: Implement a wrapper for the Anthropic Claude API and the function to format the prompt for generating search terms. Build upon Prompt 5.

Tasks:
1.  Install `anthropic`: `pip install anthropic`. Update `requirements.txt`.
2.  Create a new file `pcb_part_finder/llm_handler.py`.
3.  In `llm_handler.py`:
    * Import `os`, `anthropic`.
    * Define a custom exception `LlmApiError(Exception)`.
    * Implement a function `get_anthropic_client() -> anthropic.Anthropic | None`: Retrieves the `ANTHROPIC_API_KEY` from env vars and returns an initialized `anthropic.Anthropic(api_key=...)` client, or `None` if the key is missing.
    * Implement the function `get_llm_response(prompt: str, model: str = "claude-3-sonnet-20240229", temperature: float = 0.2) -> str | None`:
        * Get the Anthropic client using `get_anthropic_client()`. If `None`, raise `LlmApiError("Anthropic API key not found.")`.
        * Construct the message payload for the Anthropic Messages API: `model`, `max_tokens` (set a reasonable limit, e.g., 500), `temperature`, `messages=[{"role": "user", "content": prompt}]`.
        * Wrap the `client.messages.create(...)` call in a `try...except anthropic.APIError as e:` block. Handle potential errors (authentication, rate limiting, server errors). Raise `LlmApiError(f"Anthropic API error: {e}")`.
        * If the call is successful, extract the text content from the response (e.g., `response.content[0].text`).
        * Return the extracted text content.
    * Implement the function `format_search_term_prompt(part_info: dict) -> str`:
        * Takes a dictionary `part_info` representing one row from the input CSV (e.g., `{'Description': '...', 'Possible MPN': '...', 'Package': '...'}`).
        * Constructs the exact prompt string as specified in the "Example Prompt for Search Term Generation (LLM - Pass 1)" from the project specification. Use f-strings to insert the values from `part_info`.
    * Implement a helper function `parse_search_terms(llm_response: str | None) -> list[str]`:
        * Takes the raw string response from the LLM.
        * If the response is `None` or empty, return an empty list.
        * Otherwise, split the string by commas and strip whitespace from each term.
        * Return the list of search terms.
4.  In `main.py`: No integration changes yet.
5.  Create `tests/test_llm_handler.py`:
    * Write unit tests for `get_llm_response` using `pytest` and `mocker`.
    * Mock `anthropic.Anthropic` and its `messages.create` method.
    * Test case: Successful API call -> verify returns correct text content.
    * Test case: API call raises `anthropic.APIError` -> verify `LlmApiError` is raised.
    * Test case: API key missing -> verify `LlmApiError` is raised.
    * Write unit tests for `format_search_term_prompt`. Provide sample `part_info` dicts and assert the generated prompt string matches the expected format and content.
    * Write unit tests for `parse_search_terms`. Test with valid comma-separated strings, strings with extra whitespace, empty string, and `None` input.

Provide the complete `pcb_part_finder/llm_handler.py`, `tests/test_llm_handler.py`, and updated `requirements.txt`.
```

---

**Prompt 7: Evaluation Prompt Formatting & MPN Extraction**

```text
Objective: Implement the LLM prompt formatting for part evaluation and the logic to extract the chosen MPN from the LLM's response. Build upon Prompt 6.

Tasks:
1.  Modify `pcb_part_finder/llm_handler.py`.
2.  Implement the function `format_evaluation_prompt(part_info: dict, project_notes: str, selected_parts: list[dict], mouser_results: list[dict]) -> str`:
    * Takes the input CSV row (`part_info`), project notes string, list of previously selected parts (`selected_parts` format: `[{'Description': '...', 'ManufacturerPartNumber': '...'}, ...]`), and the aggregated list of Mouser search results (`mouser_results` format: list of dicts from `search_mouser_by_keyword`).
    * Format the `selected_parts` list into a readable string for the prompt (e.g., "Original Description: MPN\n..."). Handle the case where the list is empty.
    * Format the `mouser_results` list into a readable string. For each part, include key details like Manufacturer, Manufacturer Part Number, Mouser Part Number, Description, Price, Datasheet URL, Availability, and maybe a few key attributes if available in the keyword search results (keep it concise). Handle the case where `mouser_results` might be empty (though the main logic should prevent calling this if empty).
    * Construct the exact prompt string as specified in the "Example Prompt for Part Evaluation (LLM - Pass 2)" from the project specification. Use f-strings to insert all the formatted data.
3.  Implement the function `extract_mpn_from_eval(llm_response: str | None) -> str | None`:
    * Takes the raw string response from the LLM evaluation call.
    * If the response is `None` or empty, return `None`.
    * Use regular expression (`re.search`) to find the pattern `r'\[ManufacturerPartNumber:(.*?)\]'`.
    * If a match is found, extract the captured group (the MPN) and strip any leading/trailing whitespace.
    * Return the extracted MPN string.
    * If no match is found, return `None`.
4.  In `main.py`: No integration changes yet.
5.  Update `tests/test_llm_handler.py`:
    * Write unit tests for `format_evaluation_prompt`. Create sample inputs for `part_info`, `project_notes`, `selected_parts` (including empty list), and `mouser_results` (including complex structures if possible based on expected Mouser API output). Assert the generated prompt string matches the expected format.
    * Write unit tests for `extract_mpn_from_eval`. Test with sample LLM response strings containing the target pattern, strings without the pattern, strings with the pattern but empty content, and `None`/empty input.

Provide the updated `pcb_part_finder/llm_handler.py` and `tests/test_llm_handler.py`.
```

---

**Prompt 8: Integrate Core Loop Logic (Part 1 - Up to MPN Extraction)**

```text
Objective: Integrate the components developed so far into the main processing loop in `main.py`, handling the flow up to extracting the MPN from the LLM evaluation. Build upon Prompt 7.

Tasks:
1.  Modify `pcb_part_finder/main.py`.
2.  Import necessary functions from `data_loader`, `output_writer`, `mouser_api`, `llm_handler`. Import `logging` and `time`.
3.  Configure basic logging (e.g., `logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')`).
4.  Inside the `main()` function, after loading inputs and initializing the output CSV:
    * Initialize an empty list: `selected_parts = []`.
    * Get the `project_notes` string.
    * Get the `output_header` from `output_writer`.
    * Start the main loop: `for input_row in loaded_input_data:` (or whatever the list of dicts is called).
    * Inside the loop:
        * Log the start of processing for the row (e.g., `logging.info(f"Processing row {input_row.get('Description', 'N/A')}")`).
        * **LLM Pass 1 (Search Terms):**
            * Wrap in `try...except LlmApiError as e`:
                * `search_prompt = format_search_term_prompt(input_row)`
                * `llm_search_response = get_llm_response(search_prompt)`
                * `search_terms = parse_search_terms(llm_search_response)`
                * If `search_terms` is empty, log a warning and add a fallback (e.g., `search_terms = [input_row.get('Possible MPN'), input_row.get('Description')]` ensuring they are non-empty).
            * If `LlmApiError` occurs, log the error, set `match_status = "LLM Search Term Failed"`, prepare an output row dictionary combining `input_row` and this status, call `append_row_to_csv`, and `continue` to the next input row.
        * **Mouser Search:**
            * `all_mouser_results = []`
            * Loop through `search_terms`:
                * Wrap in `try...except MouserApiError as e`:
                    * `mouser_response_parts = search_mouser_by_keyword(term)`
                    * Append `mouser_response_parts` to `all_mouser_results` (use `extend` if it returns a list).
                    * Add a small delay `time.sleep(0.5)` to avoid hitting rate limits aggressively (optional but recommended).
                * If `MouserApiError` occurs, log the error (include the term searched) but *continue* to the next search term (don't abort the whole row yet). If it's a rate limit error, maybe log it and `break` the inner loop.
            * Check if `all_mouser_results` is empty *after* trying all terms. If yes:
                * Log "No Mouser matches found".
                * Set `match_status = "No Mouser Matches"`.
                * Prepare output row, call `append_row_to_csv`, `continue` to next input row.
        * **LLM Pass 2 (Evaluation):**
            * Wrap in `try...except LlmApiError as e`:
                * `eval_prompt = format_evaluation_prompt(input_row, project_notes, selected_parts, all_mouser_results)`
                * `llm_eval_response = get_llm_response(eval_prompt)` # Use default temp
                * `extracted_mpn = extract_mpn_from_eval(llm_eval_response)`
            * If `LlmApiError` occurs, log error, set `match_status = "LLM Evaluation API Failed"`, prepare output row, call `append_row_to_csv`, `continue`.
        * **Check MPN Extraction:**
            * If `extracted_mpn` is `None`:
                * Log "LLM did not return a valid MPN".
                * Set `match_status = "LLM Selection Failed"`.
                * Prepare output row, call `append_row_to_csv`, `continue`.
        * **Placeholder for next step:** If `extracted_mpn` is valid, `logging.info(f"LLM selected MPN: {extracted_mpn}")`. (We will add the detail fetch next).
5.  Update `tests/test_main.py`: This becomes harder to unit test directly. Focus on integration testing with mocks.
    * Create helper functions to mock API responses (`mocker.patch`).
    * Test the main loop flow for the "No Mouser Matches" path.
    * Test the flow for the "LLM Selection Failed" path (mock `extract_mpn_from_eval` to return `None`).
    * Test the flow for API errors during LLM calls or Mouser calls and verify the correct status is written and the loop continues.
    * Verify logging messages are emitted (using `caplog` fixture in pytest).

Provide the updated `pcb_part_finder/main.py` and `tests/test_main.py`. Ensure all necessary imports are included in `main.py`.
```

---

**Prompt 9: Integrate Final Steps (Mouser Detail Fetch & Success Output)**

```text
Objective: Integrate the final steps into the main loop: fetching detailed part info from Mouser based on the LLM's selected MPN and writing the final "Success" row to the output CSV. Build upon Prompt 8.

Tasks:
1.  Modify `pcb_part_finder/main.py`.
2.  Locate the section in the main loop where `extracted_mpn` has been successfully obtained (after the `if extracted_mpn is None:` check).
3.  **Mouser Detail Fetch:**
    * Wrap in `try...except MouserApiError as e`:
        * `part_details = search_mouser_by_mpn(extracted_mpn)`
        * Add a small delay `time.sleep(0.5)`.
    * If `MouserApiError` occurs:
        * Log the error (e.g., `f"Mouser API error fetching details for {extracted_mpn}: {e}"`).
        * Set `match_status = "Mouser Detail Fetch Failed"`.
        * Prepare output row (original input + status), call `append_row_to_csv`, `continue`.
4.  **Process Detail Fetch Results:**
    * If `part_details` is `None` (meaning MPN wasn't found by the detail search API, even if LLM suggested it):
        * Log `f"Could not find Mouser details for selected MPN: {extracted_mpn}"`.
        * Set `match_status = "Mouser Detail Not Found"`.
        * Prepare output row, call `append_row_to_csv`, `continue`.
    * **Success Path:** If `part_details` is a valid dictionary:
        * Log `f"Successfully fetched details for {extracted_mpn}"`.
        * Set `match_status = "Success"`.
        * Prepare the final `output_data` dictionary:
            * Start with `input_row.copy()`.
            * Update/add keys from the `part_details` dictionary (`Mouser Part Number`, `Manufacturer Part Number`, `Manufacturer Name`, `Mouser Description`, `Datasheet URL`, `Price`, `Availability`). Make sure the keys match the `OUTPUT_HEADER`.
            * Add/update `'Match Status': match_status`.
        * Call `append_row_to_csv(output_filename, output_data, output_header)`. Handle `OutputWriterError`.
        * **Crucially:** Append the selected part information to the `selected_parts` list for context in subsequent LLM evaluations:
            `selected_parts.append({'Description': input_row.get('Description'), 'ManufacturerPartNumber': extracted_mpn})`
5.  Ensure the `selected_parts` list passed to `format_evaluation_prompt` in the *next* iteration of the loop contains the newly added part.
6.  Add a final log message at the end of the `main()` function, e.g., "Processing complete. Output saved to bom_matched.csv".
7.  Update `tests/test_main.py`:
    * Add integration tests (using mocks) for the success path: mock LLM eval to return a valid MPN, mock `search_mouser_by_mpn` to return valid details, verify the correct "Success" row is written to the CSV, and verify the `selected_parts` list is updated.
    * Test the path where `search_mouser_by_mpn` returns `None`. Verify the correct status is written.
    * Test the path where `search_mouser_by_mpn` raises `MouserApiError`. Verify the correct status is written.
    * Test that the `selected_parts` list accumulates correctly across mocked loop iterations and is passed to the evaluation prompt formatter.

Provide the final version of `pcb_part_finder/main.py` and the updated `tests/test_main.py`.
```

---

**Prompt 10: Final Polish (Error Handling Review, Logging, Docs)**

```text
Objective: Review the entire codebase for robustness, add final touches like comprehensive logging, docstrings, type hints, and basic documentation. Build upon Prompt 9.

Tasks:
1.  **Review `main.py`:**
    * Ensure all API calls (`get_llm_response`, `search_mouser_by_keyword`, `search_mouser_by_mpn`) are within appropriate `try...except` blocks catching `LlmApiError` or `MouserApiError`.
    * Ensure file operations (`load_notes`, `load_input_csv`, `initialize_output_csv`, `append_row_to_csv`) are handled for their specific exceptions (`DataLoaderError`, `OutputWriterError`) or standard `IOError`.
    * Verify that logging provides useful information for tracing execution and debugging errors (e.g., log input row being processed, search terms generated, number of mouser results, selected MPN, errors encountered).
    * Ensure the Mouser rate limit error (429) is handled gracefully (e.g., logs error and potentially exits or stops processing further rows if desired - current implementation continues per-term, maybe add an option or flag to terminate on rate limit?). For now, just ensure it's logged distinctively.
2.  **Add Docstrings and Type Hints:**
    * Go through all Python files (`main.py`, `data_loader.py`, `output_writer.py`, `mouser_api.py`, `llm_handler.py`).
    * Add clear docstrings to all functions explaining their purpose, arguments, return values, and any exceptions raised.
    * Add type hints to function signatures (arguments and return types). Use `from typing import ...`.
3.  **Refine Logging:**
    * Ensure log levels are appropriate (e.g., `INFO` for major steps, `WARNING` for recoverable issues like LLM fallback, `ERROR` for failures that stop processing a row).
    * Consider adding a FileHandler to the logger in `main.py` to write logs to a file in addition to the console.
4.  **Create `README.md`:**
    * Create a basic `README.md` file in the project root.
    * Include:
        * Project title and brief description.
        * Setup instructions (Python version, virtual env, `pip install -r requirements.txt`).
        * Configuration (mention `.env` file and the required `MOUSER_API_KEY`, `ANTHROPIC_API_KEY` variables).
        * Usage instructions (how to run `main.py` with `--input` and `--notes` arguments).
        * Description of input files (CSV format, notes format).
        * Description of the output file (`bom_matched.csv` format).
5.  **Final `requirements.txt`:**
    * Ensure `requirements.txt` is up-to-date with all necessary libraries (`python-dotenv`, `argparse` - built-in, `requests`, `anthropic`, `pytest`, `pytest-mock`). Run `pip freeze > requirements.txt`.

Provide the final, polished versions of all `.py` files (`main.py`, `data_loader.py`, `output_writer.py`, `mouser_api.py`, `llm_handler.py`) and the content for `README.md`. There are no new tests required for this step, but ensure existing tests still pass after adding type hints/docstrings.
```