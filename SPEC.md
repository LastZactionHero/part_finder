## PCB Part Selection Streamlining Tool Specification

**1. Goal:**

To automate and streamline the part selection process for PCB design by matching approximate parts listed in a CSV file to real Mouser parts using the Mouser API, with the aid of an LLM for evaluating relevance.

**2. Input:**

* **Input CSV File (CLI Argument: `--input <filepath>`):**
    * Format: Comma-Separated Values (CSV).
    * Header Row: Expected to be present with columns: `Qty`, `Description`, `Possible MPN`, `Package`, `Notes/Source`. The order of columns is not strictly defined but these headers are expected.
    * Encoding: UTF-8.
    * Content: Each row represents a part to be matched, with approximate descriptions and any relevant notes.
* **Project Notes File (CLI Argument: `--notes <filepath>`):**
    * Format: Plain text file.
    * Content: Contains high-level project requirements, constraints, or preferences provided by the user. This context will be used by the LLM during part evaluation.
* **Previously Selected Parts (Internal List):**
    * Format: A Python list of dictionaries, where each dictionary contains at least the `Description` (from the input CSV) and the `ManufacturerPartNumber` of a successfully selected Mouser part during the current run.
    * Purpose: To provide context to the LLM for subsequent part selections, potentially influencing it to favor similar manufacturers or component types.

**3. Output:**

* **Output CSV File:**
    * Filename: `bom_matched.csv` (overwritten on each run).
    * Format: Comma-Separated Values (CSV).
    * Header Row:
        * `Qty` (from input CSV)
        * `Description` (from input CSV)
        * `Possible MPN` (from input CSV)
        * `Package` (from input CSV)
        * `Notes/Source` (from input CSV)
        * `Mouser Part Number`
        * `Manufacturer Part Number`
        * `Manufacturer Name`
        * `Mouser Description`
        * `Datasheet URL`
        * `Price` (for quantity of 1, or first available price break)
        * `Availability` (In Stock or Lead Time)
        * `Match Status` (e.g., "Success", "No Mouser Matches", "LLM Selection Failed")
    * Content: Each row corresponds to a part from the input CSV, with the original information and the details of the best matched Mouser part (if found). Rows are appended as each part is processed.

**4. Architecture and Workflow:**

1.  **Initialization:**
    * Parse command-line arguments to get file paths for the input CSV and project notes.
    * Initialize an empty list to store previously selected parts (`selected_parts`).
    * Open the output CSV file (`bom_matched.csv`) in write mode and write the header row.

2.  **Process Input CSV:**
    * Read the input CSV file row by row (skipping the header).
    * For each row:
        a.  **Generate Search Terms (LLM - Pass 1):**
            * Construct a prompt for the LLM (Anthropic Claude 3 Sonnet) that includes the "Description", "Possible MPN", and "Package" from the current CSV row.
            * Instruct the LLM to generate approximately 3 diverse search terms, prioritizing exact MPN matches, concise keyword searches, and combinations with package information. Use a low temperature (e.g., 0.2).
            * Make an API call to the Anthropic Claude API to get the search terms.
        b.  **Query Mouser API:**
            * For each generated search term, call the Mouser API `/search/keyword` endpoint.
            * Set the `keyword` parameter to the generated search term and the `records` parameter to 5.
            * Store the responses from the Mouser API.
        c.  **Evaluate Search Results (LLM - Pass 2):**
            * Construct a prompt for the LLM (Anthropic Claude 3 Sonnet) that includes:
                * The current row from the input CSV (including "Notes/Source").
                * The content of the project notes file.
                * The list of `selected_parts` (formatted as "Original Description: Manufacturer Part Number").
                * The top 5 results from each Mouser API search (including Manufacturer, Part Number, Description, Price, Datasheet URL, Availability, Attributes).
            * Instruct the LLM to evaluate the parts based on prioritized criteria: availability, relevance to "Notes/Source", datasheet availability, manufacturer reputation (if indicated), price, matching specifications, and package compatibility. Use a low temperature (e.g., 0.2).
            * Instruct the LLM to return the Manufacturer Part Number of the best match in the format `[ManufacturerPartNumber:XXXXX]`.
            * Make an API call to the Anthropic Claude API for the evaluation.
        d.  **Process LLM Evaluation:**
            * Extract the Manufacturer Part Number from the LLM's response.
            * If a Manufacturer Part Number is successfully extracted:
                * Make another call to the Mouser API (e.g., `/search/partnumber`) using the extracted Manufacturer Part Number to get detailed part information (Manufacturer Name, Mouser Part Number, full Description, Datasheet URL, Price, Availability).
                * Write a new row to the output CSV (`bom_matched.csv`) with the original input data and the retrieved Mouser part details, setting the "Match Status" to "Success".
                * Append a dictionary containing the original `Description` and the selected `ManufacturerPartNumber` to the `selected_parts` list.
            * If no Manufacturer Part Number is extracted (LLM selection failed), write a row to the output CSV with the original input data and a "Match Status" of "LLM Selection Failed".
        e.  **Handle No Mouser Matches:** If all generated search terms return no results from the Mouser API, write a row to the output CSV with the original input data and a "Match Status" of "No Mouser Matches".

**5. Data Handling:**

* **CSV Parsing:** Use Python's `csv` module for reading and writing CSV files, ensuring proper handling of delimiters and encoding.
* **JSON Parsing:** Use Python's `json` module to parse the JSON responses from the Mouser API and the LLM.
* **Text Handling:** Read the project notes file as plain text.
* **Data Extraction:** Implement robust logic (e.g., regular expressions) to extract the Manufacturer Part Number from the LLM's response.

**6. Error Handling:**

* **Mouser API Errors:** Log any errors returned by the Mouser API. For rate limiting errors, the script should terminate with a clear error message.
* **LLM API Errors:** Log any errors returned by the Anthropic Claude API.
* **Data Parsing Errors:** If there are issues parsing JSON responses from either API, the script should terminate with an error message including the raw response that failed to parse.
* **File Handling Errors:** Implement error handling for cases where the input CSV or project notes file cannot be opened or read, or if the output CSV cannot be written.
* **No Matches/LLM Selection Failures:** These should be recorded in the "Match Status" column of the output CSV, allowing the user to review these cases.

**7. Testing Plan:**

* **Unit Tests:**
    * Test the search term generation logic (mocking the LLM API) with various input CSV rows to ensure diverse and relevant search terms are produced.
    * Test the Mouser API interaction (mocking the API) with different keywords and responses to ensure correct data extraction.
    * Test the LLM evaluation logic (mocking the LLM API) with sample Mouser parts and project notes to verify the selection process and the format of the returned Manufacturer Part Number.
    * Test the CSV reading and writing functionality, including header creation and data appending.
    * Test the extraction of the Manufacturer Part Number from the LLM's response.
* **Integration Tests:**
    * Run the entire workflow with a small sample input CSV and real Mouser and LLM API keys (using a limited number of requests to avoid excessive costs or rate limits).
    * Verify that the output CSV is generated correctly with the expected data.
    * Test the handling of cases with no Mouser matches and LLM selection failures.
    * Test the inclusion of project notes and previously selected parts in the LLM evaluation.
* **End-to-End Tests:**
    * Run the tool with a realistic input CSV and project notes.
    * Manually verify the accuracy and relevance of the selected Mouser parts.
    * Monitor API usage and potential rate limiting.
* **Error Handling Tests:**
    * Test the script's behavior when provided with invalid file paths for input CSV or project notes.
    * Simulate API errors (e.g., by using incorrect API keys or triggering rate limits if possible in a controlled manner).
    * Test the script's robustness against unexpected data formats in API responses (though "hard fail" is the current strategy).

**8. Further Considerations (Out of Scope for Initial Implementation):**

* More sophisticated error handling and retry mechanisms for API calls.
* Handling different price breaks based on the quantity in the input CSV.
* More advanced logic for package compatibility.
* User interface (e.g., a web interface or GUI).
* Configuration options for LLM temperature and the number of Mouser search results to consider.
* Logging of the entire process for debugging and auditing.

=====


**Example Prompt for Search Term Generation (LLM - Pass 1):**

```
Your task is to generate a small number of diverse search terms (approximately 3) for finding electronic components on Mouser.com based on the following input fields: 'Description', 'Possible MPN', and 'Package'. The goal is to create search terms that are likely to yield relevant results. Consider the following strategies when generating these terms:

1. Prioritize the 'Possible MPN': If a 'Possible MPN' is provided, use it as one of the search terms, ideally as an exact match.
2. Create concise keyword-based searches from the 'Description', focusing on the most important features and component type.
3. Combine keywords from the 'Description' with the 'Package' information to narrow or broaden the search effectively. For example, if the description mentions a type of IC and the package is 'SMD', include 'SMD' in one of the search terms.
4. Vary the level of detail in the generated search terms. Some should be more specific, while others should be broader to capture a wider range of potential matches.
5. Consider common abbreviations or alternative names for components or packages if they are likely to be used in Mouser's search.

Here is the input for the current part:
Description: {Description from CSV}
Possible MPN: {Possible MPN from CSV}
Package: {Package from CSV}

Generate the search terms as a comma-separated list.
```

**Example Prompt for Part Evaluation (LLM - Pass 2):**

```
Here is a list of potential parts from Mouser for the original part described below. Your task is to evaluate this list and select the single best part that matches the requirements and context provided.

Original Part Details:
Quantity: {Qty from CSV}
Description: {Description from CSV}
Possible MPN: {Possible MPN from CSV}
Package: {Package from CSV}
Notes/Source: {Notes/Source from CSV}

Project Notes:
{Content of the project notes file}

Previously Selected Parts:
{List of previously selected parts, formatted as "Original Description: Manufacturer Part Number"}

Mouser Search Results:
{Formatted list of the top 5 results from each Mouser API search, including Manufacturer, Manufacturer Part Number, Mouser Part Number, Description, Price, Datasheet URL, Availability, and key Product Attributes}

When evaluating the Mouser parts, prioritize parts that are currently in stock or have a short lead time. The most important factor is that the selected part closely matches the requirements and specifications mentioned in the 'Notes/Source' field provided for the original part. Favor parts with readily available datasheets. Consider the manufacturer if project preferences are indicated in the 'Project Notes' or 'Previously Selected Parts'. While important, price should be a secondary consideration after availability and functional suitability are established. Ensure the specifications and package of the selected part are compatible with the original requirement.

Return your answer in the following format so it can be easily parsed. Use EXACTLY the Manufacturer Part Number as shown in the list above, do not add manufacturer name or any other text:
[ManufacturerPartNumber:XXXXX]
```

**Notes for the Developer:**

* Remember to replace the bracketed placeholders in these prompts with the actual data at runtime.
* The formatting of the Mouser search results within the second prompt should be clear and easy for the LLM to understand. Consider including relevant attributes in a structured way (e.g., as a list of key-value pairs).
* The "Previously Selected Parts" section in the second prompt will be dynamically populated based on the successful matches made for previous parts in the input CSV during the current run. If no parts have been selected yet, this section will be empty.

These example prompts should give the developer a clear starting point for implementing the LLM interactions.