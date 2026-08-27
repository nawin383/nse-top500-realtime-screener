"""Helper to record live ticks to file for replay mode."""
import json
from datetime import datetime

# Usage: customize to connect KiteProvider and dump ticks to file
# with open("replay.jsonl","a") as f:
#   for batch in ticks:
#     for t in batch:
#       f.write(t.model_dump_json() + "\n")
print("Configure provider and run to generate replay.jsonl")
