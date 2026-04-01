import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/backend")

from app.db.database import supabase
from pprint import pprint

def main():
    res = supabase.table("leads").select("*, campaigns(status, templates, delays)").execute()
    pprint(res.data)

main()
