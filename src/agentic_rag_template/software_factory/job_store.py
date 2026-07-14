"""Persistent storage for Software Factory jobs."""

from typing import Any, Callable, Dict, List, Optional

from agentic_rag_template.software_factory.jobs import (
    JOB_STATUS_QUEUED,
    ArchitectureGenerationJob,
)


class ArchitectureGenerationJobStoreError(RuntimeError):
    """Raised when the architecture job store cannot read or write jobs."""


class PostgresArchitectureGenerationJobStore:
    """Postgres-backed store for Architecture Sheet generation jobs."""

    def __init__(
        self,
        database_url: str,
        connection_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        if not database_url:
            raise ValueError("database_url is required")

        self.database_url = database_url
        self.connection_factory = connection_factory or self._load_psycopg_connect()
        self.json_wrapper = (lambda value: value) if connection_factory else self._load_jsonb_wrapper()

    def initialize(self) -> None:
        """Create the jobs table when it does not exist yet."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS architecture_generation_jobs (
                        id TEXT PRIMARY KEY,
                        app_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        current_step TEXT NOT NULL DEFAULT '',
                        description TEXT NOT NULL,
                        generation_mode TEXT NOT NULL,
                        llm_provider TEXT NOT NULL DEFAULT 'none',
                        llm_model TEXT NOT NULL DEFAULT 'none',
                        error TEXT NOT NULL DEFAULT '',
                        payload JSONB NOT NULL,
                        result JSONB,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        started_at TIMESTAMPTZ,
                        finished_at TIMESTAMPTZ
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_architecture_generation_jobs_status
                    ON architecture_generation_jobs (status)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_architecture_generation_jobs_created_at
                    ON architecture_generation_jobs (created_at DESC)
                    """
                )

    def save(self, job: ArchitectureGenerationJob) -> None:
        """Insert or update a job snapshot."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._save_with_cursor(cursor, job)

    def claim_next(self, app_id: Optional[str] = None) -> Optional[ArchitectureGenerationJob]:
        """Atomically reserve the oldest queued job for one worker."""
        where_clause = "status = %(status)s"
        params = {"status": JOB_STATUS_QUEUED}

        if app_id:
            where_clause += " AND app_id = %(app_id)s"
            params["app_id"] = app_id

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT payload
                    FROM architecture_generation_jobs
                    WHERE {where_clause}
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """,
                    params,
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                payload = row[0] if not isinstance(row, dict) else row["payload"]
                job = ArchitectureGenerationJob.from_dict(payload)
                job.mark_running("Worker hat den Job uebernommen.")
                self._save_with_cursor(cursor, job)

        return job

    def get(self, job_id: str) -> Optional[ArchitectureGenerationJob]:
        """Load one job by id."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM architecture_generation_jobs WHERE id = %(id)s",
                    {"id": job_id},
                )
                row = cursor.fetchone()

        if row is None:
            return None

        payload = row[0] if not isinstance(row, dict) else row["payload"]
        return ArchitectureGenerationJob.from_dict(payload)

    def list(self, limit: int = 50) -> List[ArchitectureGenerationJob]:
        """List recent jobs newest first."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM architecture_generation_jobs
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                    """,
                    {"limit": limit},
                )
                rows = cursor.fetchall()

        return [
            ArchitectureGenerationJob.from_dict(row[0] if not isinstance(row, dict) else row["payload"])
            for row in rows
        ]

    def _connect(self) -> Any:
        return self.connection_factory(self.database_url)

    @staticmethod
    def _load_psycopg_connect() -> Callable[..., Any]:
        try:
            from psycopg import connect
        except ImportError as error:
            raise ArchitectureGenerationJobStoreError(
                "Postgres job storage requires the 'psycopg[binary]' dependency."
            ) from error
        return connect

    @staticmethod
    def _load_jsonb_wrapper() -> Callable[[Any], Any]:
        try:
            from psycopg.types.json import Jsonb
        except ImportError as error:
            raise ArchitectureGenerationJobStoreError(
                "Postgres job storage requires the 'psycopg[binary]' dependency."
            ) from error
        return Jsonb

    def _job_params(self, job: ArchitectureGenerationJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": job.id,
            "app_id": job.app_id,
            "status": job.status,
            "current_step": job.current_step,
            "description": job.description,
            "generation_mode": job.generation_mode,
            "llm_provider": job.llm_provider,
            "llm_model": job.llm_model,
            "error": job.error,
            "payload": self.json_wrapper(payload),
            "result": self.json_wrapper(job.result) if job.result is not None else None,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }

    def _save_with_cursor(self, cursor: Any, job: ArchitectureGenerationJob) -> None:
        payload = job.to_dict()
        cursor.execute(
            """
            INSERT INTO architecture_generation_jobs (
                id,
                app_id,
                status,
                current_step,
                description,
                generation_mode,
                llm_provider,
                llm_model,
                error,
                payload,
                result,
                created_at,
                updated_at,
                started_at,
                finished_at
            )
            VALUES (
                %(id)s,
                %(app_id)s,
                %(status)s,
                %(current_step)s,
                %(description)s,
                %(generation_mode)s,
                %(llm_provider)s,
                %(llm_model)s,
                %(error)s,
                %(payload)s,
                %(result)s,
                %(created_at)s,
                %(updated_at)s,
                %(started_at)s,
                %(finished_at)s
            )
            ON CONFLICT (id) DO UPDATE SET
                app_id = EXCLUDED.app_id,
                status = EXCLUDED.status,
                current_step = EXCLUDED.current_step,
                description = EXCLUDED.description,
                generation_mode = EXCLUDED.generation_mode,
                llm_provider = EXCLUDED.llm_provider,
                llm_model = EXCLUDED.llm_model,
                error = EXCLUDED.error,
                payload = EXCLUDED.payload,
                result = EXCLUDED.result,
                updated_at = EXCLUDED.updated_at,
                started_at = EXCLUDED.started_at,
                finished_at = EXCLUDED.finished_at
            """,
            self._job_params(job, payload),
        )
