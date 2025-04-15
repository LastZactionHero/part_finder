Right now, this is a script that identifies good parts for a PCB project with Mouse and Claude. It runs a single turn, taking an input project and outputting a single CSV.

I'd like to create a very bare bones MVP for this. In a full system, we'd probably set up queues for all of this, but I'm just trying to go fast to get insight if it's useful for users.

I'd like you to modify the main script to sequentially process a queue:

- Polls /projects/queue
- Picks the earliest, sorted alphabetically
- Processes the files (intial_bom.csv and project_details.txt)
- Moves to /projects/finished when done
- Adds a results.json file, that includes "status:" "complete" or "failed", and start/finish timestamp
