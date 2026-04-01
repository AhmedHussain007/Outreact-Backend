import asyncio
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/backend")

logging.basicConfig(level=logging.INFO)

from app.services.worker import dispatch_due_emails

async def main():
    await dispatch_due_emails()

asyncio.run(main())
