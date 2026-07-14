"""Background worker for long-running Software Factory jobs."""

from __future__ import annotations

import time
from typing import Callable, Optional

from agentic_rag_template.applications import FileApplicationRegistry
from agentic_rag_template.config import Settings
from agentic_rag_template.llm import create_llm_provider
from agentic_rag_template.llm.models import LLMProvider
from agentic_rag_template.software_factory.architecture_sheet import generate_architecture_sheet
from agentic_rag_template.software_factory.job_store import PostgresArchitectureGenerationJobStore
from agentic_rag_template.software_factory.jobs import (
    ArchitectureGenerationEvent,
    ArchitectureGenerationJob,
    apply_architecture_generation_event,
)


SOFTWARE_FACTORY_APP_ID = "software-factory"


class ArchitectureGenerationWorker:
    """Poll queued architecture jobs and execute them outside the web process."""

    def __init__(
        self,
        settings: Settings,
        job_store: Optional[PostgresArchitectureGenerationJobStore] = None,
        llm_provider_factory: Optional[Callable[[Settings], LLMProvider]] = None,
        poll_seconds: float = 2.0,
    ) -> None:
        self.settings = settings
        self.job_store = job_store or PostgresArchitectureGenerationJobStore(settings.database_url)
        self.llm_provider_factory = llm_provider_factory or create_llm_provider
        self.poll_seconds = poll_seconds

    def run_forever(self) -> None:
        """Continuously claim and process queued jobs."""
        self.job_store.initialize()
        while True:
            processed = self.process_next()
            if not processed:
                time.sleep(self.poll_seconds)

    def process_next(self) -> bool:
        """Process one queued job if available."""
        job = self.job_store.claim_next(app_id=SOFTWARE_FACTORY_APP_ID)
        if job is None:
            return False

        self.process_job(job)
        return True

    def process_job(self, job: ArchitectureGenerationJob) -> ArchitectureGenerationJob:
        """Run one claimed architecture generation job to a terminal state."""
        try:
            application = FileApplicationRegistry(self.settings).get(job.app_id)
            llm_provider = self.llm_provider_factory(self.settings)
            job.llm_provider = getattr(llm_provider, "name", "none")
            job.llm_model = getattr(llm_provider, "model", "none")
            self.job_store.save(job)

            def persist_event(event: ArchitectureGenerationEvent) -> None:
                apply_architecture_generation_event(job, event)
                self.job_store.save(job)

            result = generate_architecture_sheet(
                job.description,
                application,
                llm_provider=llm_provider,
                generation_mode=job.generation_mode,
                event_handler=persist_event,
            )
            job.complete(result.to_dict())
            self.job_store.save(job)
        except Exception as error:
            job.fail(str(error))
            self.job_store.save(job)

        return job


def main() -> None:
    settings = Settings.from_env()
    worker = ArchitectureGenerationWorker(settings=settings, poll_seconds=settings.worker_poll_seconds)
    worker.run_forever()


if __name__ == "__main__":
    main()
