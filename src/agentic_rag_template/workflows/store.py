"""Postgres-backed persistence for configurable workflows."""

import json
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from agentic_rag_template.workflows.models import (
    AgentVersion,
    VERSION_STATUS_PUBLISHED,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowVersion,
)


class WorkflowStoreError(RuntimeError):
    """Raised when workflow persistence cannot read or write data."""


@runtime_checkable
class WorkflowStore(Protocol):
    """Persistence contract for workflow configuration, runs and artifacts."""

    def initialize(self) -> None:
        """Prepare persistence structures."""

    def save_workflow_version(self, workflow_version: WorkflowVersion) -> None:
        """Persist one workflow version snapshot."""

    def get_workflow_version(self, workflow_slug: str, version_number: int) -> Optional[WorkflowVersion]:
        """Load one workflow version by slug and version number."""

    def list_workflow_versions(self, workflow_slug: str) -> List[WorkflowVersion]:
        """List workflow versions for one workflow."""

    def save_agent_version(self, agent_version: AgentVersion) -> None:
        """Persist one agent version snapshot."""

    def get_agent_version(self, agent_slug: str, version_number: int) -> Optional[AgentVersion]:
        """Load one agent version by slug and version number."""

    def save_run(self, workflow_run: WorkflowRun) -> None:
        """Persist one workflow run snapshot and its artifacts."""

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Load one workflow run."""

    def list_runs(self, workflow_slug: Optional[str] = None, limit: int = 50) -> List[WorkflowRun]:
        """List workflow runs, optionally scoped to one workflow."""

    def list_validated_artifacts(self, run_id: str) -> List[WorkflowArtifact]:
        """List validated artifacts for a workflow run."""


class PostgresWorkflowStore:
    """Lightweight Postgres store for workflow configuration and runs.

    The store keeps indexed columns for lookup and complete immutable snapshots
    in JSONB payloads. This matches the current non-Django project shape while
    leaving room for a later Django model migration.
    """

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
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_definitions (
                        slug TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_versions (
                        workflow_slug TEXT NOT NULL,
                        version_number INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        published_at TIMESTAMPTZ,
                        PRIMARY KEY (workflow_slug, version_number)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_definitions (
                        slug TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_versions (
                        agent_slug TEXT NOT NULL,
                        version_number INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        published_at TIMESTAMPTZ,
                        PRIMARY KEY (agent_slug, version_number)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_runs (
                        id TEXT PRIMARY KEY,
                        workflow_slug TEXT NOT NULL,
                        workflow_version_number INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        started_at TIMESTAMPTZ,
                        finished_at TIMESTAMPTZ
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_artifacts (
                        workflow_run_id TEXT NOT NULL,
                        artifact_key TEXT NOT NULL,
                        is_validated BOOLEAN NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        PRIMARY KEY (workflow_run_id, artifact_key)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_workflow_versions_status
                    ON workflow_versions (status)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_workflow_runs_status
                    ON workflow_runs (status)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_workflow_artifacts_validated
                    ON workflow_artifacts (workflow_run_id, is_validated)
                    """
                )

    def save_workflow_version(self, workflow_version: WorkflowVersion) -> None:
        payload = workflow_version.to_dict()
        existing_version = self.get_workflow_version(
            workflow_version.workflow.slug,
            workflow_version.version_number,
        )
        _assert_published_snapshot_is_unchanged(
            existing_version.to_dict() if existing_version else None,
            payload,
            f"workflow version {workflow_version.workflow.slug} v{workflow_version.version_number}",
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_definitions (
                        slug,
                        name,
                        status,
                        payload,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %(slug)s,
                        %(name)s,
                        %(status)s,
                        %(payload)s,
                        %(created_at)s,
                        %(updated_at)s
                    )
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        updated_at = EXCLUDED.updated_at
                    """,
                    {
                        "slug": workflow_version.workflow.slug,
                        "name": workflow_version.workflow.name,
                        "status": workflow_version.workflow.status,
                        "payload": self.json_wrapper(workflow_version.workflow.to_dict()),
                        "created_at": workflow_version.workflow.created_at,
                        "updated_at": workflow_version.workflow.updated_at,
                    },
                )
                cursor.execute(
                    """
                    INSERT INTO workflow_versions (
                        workflow_slug,
                        version_number,
                        status,
                        payload,
                        created_at,
                        published_at
                    )
                    VALUES (
                        %(workflow_slug)s,
                        %(version_number)s,
                        %(status)s,
                        %(payload)s,
                        %(created_at)s,
                        %(published_at)s
                    )
                    ON CONFLICT (workflow_slug, version_number) DO UPDATE SET
                        status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        published_at = EXCLUDED.published_at
                    WHERE workflow_versions.status <> 'published'
                    OR workflow_versions.payload = EXCLUDED.payload
                    """,
                    {
                        "workflow_slug": workflow_version.workflow.slug,
                        "version_number": workflow_version.version_number,
                        "status": workflow_version.status,
                        "payload": self.json_wrapper(payload),
                        "created_at": workflow_version.created_at,
                        "published_at": workflow_version.published_at,
                    },
                )

    def get_workflow_version(self, workflow_slug: str, version_number: int) -> Optional[WorkflowVersion]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM workflow_versions
                    WHERE workflow_slug = %(workflow_slug)s
                    AND version_number = %(version_number)s
                    """,
                    {"workflow_slug": workflow_slug, "version_number": version_number},
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return WorkflowVersion.from_dict(_row_payload(row))

    def list_workflow_versions(self, workflow_slug: str) -> List[WorkflowVersion]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM workflow_versions
                    WHERE workflow_slug = %(workflow_slug)s
                    ORDER BY version_number DESC
                    """,
                    {"workflow_slug": workflow_slug},
                )
                rows = cursor.fetchall()
        return [WorkflowVersion.from_dict(_row_payload(row)) for row in rows]

    def save_agent_version(self, agent_version: AgentVersion) -> None:
        payload = agent_version.to_dict()
        existing_version = self.get_agent_version(
            agent_version.agent.slug,
            agent_version.version_number,
        )
        _assert_published_snapshot_is_unchanged(
            existing_version.to_dict() if existing_version else None,
            payload,
            f"agent version {agent_version.agent.slug} v{agent_version.version_number}",
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_definitions (
                        slug,
                        name,
                        status,
                        payload,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %(slug)s,
                        %(name)s,
                        %(status)s,
                        %(payload)s,
                        %(created_at)s,
                        %(updated_at)s
                    )
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        updated_at = EXCLUDED.updated_at
                    """,
                    {
                        "slug": agent_version.agent.slug,
                        "name": agent_version.agent.name,
                        "status": agent_version.agent.status,
                        "payload": self.json_wrapper(agent_version.agent.to_dict()),
                        "created_at": agent_version.agent.created_at,
                        "updated_at": agent_version.agent.updated_at,
                    },
                )
                cursor.execute(
                    """
                    INSERT INTO agent_versions (
                        agent_slug,
                        version_number,
                        status,
                        payload,
                        created_at,
                        published_at
                    )
                    VALUES (
                        %(agent_slug)s,
                        %(version_number)s,
                        %(status)s,
                        %(payload)s,
                        %(created_at)s,
                        %(published_at)s
                    )
                    ON CONFLICT (agent_slug, version_number) DO UPDATE SET
                        status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        published_at = EXCLUDED.published_at
                    WHERE agent_versions.status <> 'published'
                    OR agent_versions.payload = EXCLUDED.payload
                    """,
                    {
                        "agent_slug": agent_version.agent.slug,
                        "version_number": agent_version.version_number,
                        "status": agent_version.status,
                        "payload": self.json_wrapper(payload),
                        "created_at": agent_version.created_at,
                        "published_at": agent_version.published_at,
                    },
                )

    def get_agent_version(self, agent_slug: str, version_number: int) -> Optional[AgentVersion]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM agent_versions
                    WHERE agent_slug = %(agent_slug)s
                    AND version_number = %(version_number)s
                    """,
                    {"agent_slug": agent_slug, "version_number": version_number},
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return AgentVersion.from_dict(_row_payload(row))

    def save_run(self, workflow_run: WorkflowRun) -> None:
        payload = workflow_run.to_dict()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_runs (
                        id,
                        workflow_slug,
                        workflow_version_number,
                        status,
                        payload,
                        started_at,
                        finished_at
                    )
                    VALUES (
                        %(id)s,
                        %(workflow_slug)s,
                        %(workflow_version_number)s,
                        %(status)s,
                        %(payload)s,
                        %(started_at)s,
                        %(finished_at)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        finished_at = EXCLUDED.finished_at
                    """,
                    {
                        "id": workflow_run.id,
                        "workflow_slug": workflow_run.workflow_version.workflow.slug,
                        "workflow_version_number": workflow_run.workflow_version.version_number,
                        "status": workflow_run.status,
                        "payload": self.json_wrapper(payload),
                        "started_at": workflow_run.started_at,
                        "finished_at": workflow_run.finished_at,
                    },
                )
                for artifact in workflow_run.artifacts:
                    self._save_artifact_with_cursor(cursor, artifact)

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM workflow_runs WHERE id = %(id)s",
                    {"id": run_id},
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return WorkflowRun.from_dict(_row_payload(row))

    def list_runs(self, workflow_slug: Optional[str] = None, limit: int = 50) -> List[WorkflowRun]:
        params: Dict[str, Any] = {"limit": limit}
        where_clause = ""
        if workflow_slug:
            where_clause = "WHERE workflow_slug = %(workflow_slug)s"
            params["workflow_slug"] = workflow_slug
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT payload
                    FROM workflow_runs
                    {where_clause}
                    ORDER BY started_at DESC NULLS LAST
                    LIMIT %(limit)s
                    """,
                    params,
                )
                rows = cursor.fetchall()
        return [WorkflowRun.from_dict(_row_payload(row)) for row in rows]

    def list_validated_artifacts(self, run_id: str) -> List[WorkflowArtifact]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM workflow_artifacts
                    WHERE workflow_run_id = %(run_id)s
                    AND is_validated = TRUE
                    ORDER BY created_at ASC
                    """,
                    {"run_id": run_id},
                )
                rows = cursor.fetchall()
        return [WorkflowArtifact.from_dict(_row_payload(row)) for row in rows]

    def _save_artifact_with_cursor(self, cursor: Any, artifact: WorkflowArtifact) -> None:
        payload = artifact.to_dict()
        cursor.execute(
            """
            INSERT INTO workflow_artifacts (
                workflow_run_id,
                artifact_key,
                is_validated,
                payload,
                created_at
            )
            VALUES (
                %(workflow_run_id)s,
                %(artifact_key)s,
                %(is_validated)s,
                %(payload)s,
                %(created_at)s
            )
            ON CONFLICT (workflow_run_id, artifact_key) DO UPDATE SET
                is_validated = EXCLUDED.is_validated,
                payload = EXCLUDED.payload,
                created_at = EXCLUDED.created_at
            """,
            {
                "workflow_run_id": artifact.workflow_run_id,
                "artifact_key": artifact.artifact_key,
                "is_validated": artifact.is_validated,
                "payload": self.json_wrapper(payload),
                "created_at": artifact.created_at,
            },
        )

    def _connect(self) -> Any:
        return self.connection_factory(self.database_url)

    @staticmethod
    def _load_psycopg_connect() -> Callable[..., Any]:
        try:
            from psycopg import connect
        except ImportError as error:
            raise WorkflowStoreError(
                "Postgres workflow storage requires the 'psycopg[binary]' dependency."
            ) from error
        return connect

    @staticmethod
    def _load_jsonb_wrapper() -> Callable[[Any], Any]:
        try:
            from psycopg.types.json import Jsonb
        except ImportError as error:
            raise WorkflowStoreError(
                "Postgres workflow storage requires the 'psycopg[binary]' dependency."
            ) from error
        return Jsonb


def _row_payload(row: Any) -> Dict[str, Any]:
    payload = row[0] if not isinstance(row, dict) else row["payload"]
    return dict(payload)


def _assert_published_snapshot_is_unchanged(
    existing_payload: Optional[Dict[str, Any]],
    incoming_payload: Dict[str, Any],
    label: str,
) -> None:
    if not existing_payload or existing_payload.get("status") != VERSION_STATUS_PUBLISHED:
        return
    if _canonical_payload(existing_payload) == _canonical_payload(incoming_payload):
        return
    raise WorkflowStoreError(f"published {label} is immutable")


def _canonical_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
