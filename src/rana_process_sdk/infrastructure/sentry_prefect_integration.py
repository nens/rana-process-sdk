import json

from prefect import Flow
from prefect.blocks.core import Block
from prefect.client.schemas import FlowRun
from prefect.states import State
from sentry_sdk import capture_message, init, new_scope, set_context, set_tag
from sentry_sdk.types import Event, Hint

from rana_process_sdk.domain import FormattedException, ProcessUserError

__all__ = ["SentryBlock", "SENTRY_BLOCK_NAME"]

SENTRY_BLOCK_NAME = "sentry-block"
FAILED_STATE_MESSAGE = "Finished in state Failed"


def prefect_log_filter(event: Event, hint: Hint) -> Event | None:
    message = str((event.get("logentry") or {}).get("message"))
    if message.startswith("{"):
        try:
            # Exception with formatted messages have already been logged by sentry
            FormattedException(**json.loads(message))
        except Exception:
            return event
        else:
            return None
    if message.startswith(FAILED_STATE_MESSAGE) or ProcessUserError.__name__ in message:
        # Filter out exception from ending in failed state or user errors
        return None
    return event


class SentryBlock(Block):
    """Block that bootstraps Sentry with metadata related to Prefect flow runs."""

    dsn: str
    environment: str

    def init(self, default_integrations: bool = True) -> None:
        """Initialize the sentry block."""
        init(
            self.dsn,
            environment=self.environment,
            default_integrations=default_integrations,
            enable_tracing=False,
            auto_session_tracking=False,
            before_send=prefect_log_filter,
        )

    @staticmethod
    def set_tags_and_context(flow_run: FlowRun) -> None:
        """Set tags and context for the current scope."""
        set_tag("rana_process_id", str(flow_run.deployment_id))
        set_tag("rana_job_id", str(flow_run.id))
        set_tag(
            "rana_tenant",
            next(
                (tag[10:] for tag in flow_run.tags if tag.startswith("tenant_id_")),
                None,
            ),
        )
        set_tag(
            "rana_project_id",
            next(
                (tag[11:] for tag in flow_run.tags if tag.startswith("project_id_")),
                None,
            ),
        )
        set_context("rana_job_parameters", flow_run.parameters)

    @staticmethod
    def crash_handler(flow: Flow, flow_run: FlowRun, state: State) -> None:
        with new_scope():
            SentryBlock.set_tags_and_context(flow_run)
            capture_message(f"Process {flow_run.deployment_id} crashed", level="error")
