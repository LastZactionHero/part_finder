Right now, we run three searches to Mouser for every part in the BOM. We only have 1000 queries per day, so this will run out quick.

I'd like to build a parts cache for near exact matches:

- All updates to the API docker container
- Update mouser_api.py to save the result of every request
- Save to Pinecone DB

mouserparts
https://mouserparts-10e253q.svc.aped-4627-b74a.pinecone.io
llama-text-embed-v2

So in this case, the user's keyword search gets converted to an embedding vector and is used for the search.

- When calling `search_mouser_by_keyword`, first search the PineconeDB.
- If there's a hit higher than some threshold, use this instead and skip the Mouser search

PINECONE_DB_API_KEY was added to .env
