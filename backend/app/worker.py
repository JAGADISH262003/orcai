"""Standalone job worker process: `python -m app.worker`.

Runs the same worker loop as the in-process background task, useful for
horizontal scaling (run N workers against the Postgres-backed queue).
"""

import asyncio
import logging

from app.core.logging import setup_logging

setup_logging()


async def main() -> None:
    from app.services import job_handlers  # noqa: F401  (register handlers)
    from app.services.jobs import worker_loop

    logging.getLogger("orcai.worker").info("job worker starting")
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
