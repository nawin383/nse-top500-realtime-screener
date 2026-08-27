"""Regenerate NSE Top500 universe - run after instrument changes"""
import json, random
from pathlib import Path

# Logic duplicated from config generation; for maintenance you can fetch from NSE or Kite instruments API.
# Example: fetch Kite instruments csv, filter NSE eq, sort by market cap, take top 500, map sectors.

print("To regenerate universe, edit config/nse_top500.json or integrate Kite instruments API.")
print("Example Kite fetch:")
print("  import requests")
print("  import csv")
print("  # GET https://api.kite.trade/instruments/NSE")
