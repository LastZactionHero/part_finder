I'd like you to create a web front-end for the project described in README.md.

This should be a simple, single-page web app to take a table of components and return a BOM with Mouser part ids. This is a rough MVP, just to test interest.

- Title and description of the page
- Displays the number of items in the queue
- A text box that lets the user input components as a CSV
- A button to submit
- Shows an error message if one occurs
- If successful, stores the project id, updates the URL bar
- Polls the current project ID
- If queued, polls every 10 seconds until finished, showing the position in the queue
- If finished, shows the full BOM.
- For each part with a valid Mouser Part ID, shows a links with URL "https://www.mouser.com/ProductDetail/<Mouser Part ID>"

