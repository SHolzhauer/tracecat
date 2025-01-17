from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from tracecat.db.schemas import ActionRun, Resource, Schedule, WorkflowRun
from tracecat.dsl.common import DSLInput
from tracecat.types.generics import ListModel
from tracecat.types.secrets import SecretKeyValue

# TODO: Consistent API design
# Action and Workflow create / update params
# should be the same as the metadata responses

RunStatus = Literal["pending", "running", "failure", "success", "canceled"]


class ActionResponse(BaseModel):
    id: str
    type: str
    title: str
    description: str
    status: str
    inputs: dict[str, Any]
    key: str  # Computed field


class WorkflowResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    actions: dict[str, ActionResponse]
    object: dict[str, Any] | None  # React Flow object
    owner_id: str
    version: int | None = None
    webhook: WebhookResponse
    schedules: list[Schedule]
    entrypoint: str | None


class ActionMetadataResponse(BaseModel):
    id: str
    workflow_id: str
    type: str
    title: str
    description: str
    status: str
    key: str


class WorkflowMetadataResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    icon_url: str | None
    created_at: datetime
    updated_at: datetime
    version: int | None


class WorkflowRunResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    action_runs: list[ActionRun] = []

    @classmethod
    def from_orm(cls, run: WorkflowRun) -> WorkflowRunResponse:
        return cls(**run.model_dump(), action_runs=run.action_runs)


class ActionRunResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    action_id: str
    workflow_run_id: str
    status: str
    error_msg: str | None = None
    result: dict[str, Any] | None = None

    @classmethod
    def from_orm(cls, run: ActionRun) -> ActionRunResponse:
        dict_result = None if run.result is None else json.loads(run.result)
        return cls(**run.model_dump(exclude={"result"}), result=dict_result)


class ActionRunEventParams(BaseModel):
    id: str  # This is deterministically defined in the runner
    owner_id: str
    created_at: datetime
    updated_at: datetime
    status: RunStatus
    workflow_run_id: str
    error_msg: str | None = None
    result: str | None = None  # JSON-serialized String


class WorkflowRunEventParams(BaseModel):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    status: RunStatus


class CreateWorkflowParams(BaseModel):
    title: str | None = None
    description: str | None = None


class UpdateWorkflowParams(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)
    title: str | None = None
    description: str | None = None
    status: Literal["online", "offline"] | None = None
    object: dict[str, Any] | None = None
    version: int | None = None
    entrypoint: str | None = None
    icon_url: str | None = None


class CreateActionParams(BaseModel):
    workflow_id: str
    type: str
    title: str


class UpdateActionParams(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    inputs: dict[str, Any] | None = None


class UpsertWebhookParams(BaseModel):
    status: Literal["online", "offline"] | None = None
    entrypoint_ref: str | None = None
    method: Literal["GET", "POST"] | None = None


class WebhookResponse(Resource):
    id: str
    secret: str
    status: Literal["online", "offline"]
    entrypoint_ref: str | None = None
    filters: dict[str, Any]
    method: Literal["GET", "POST"]
    workflow_id: str
    url: str


class GetWebhookParams(BaseModel):
    webhook_id: str | None = None
    path: str | None = None


class Event(BaseModel):
    published_at: datetime
    action_id: str
    action_run_id: str
    action_title: str
    action_type: str
    workflow_id: str
    workflow_title: str
    workflow_run_id: str
    data: dict[str, Any]


class EventSearchParams(BaseModel):
    workflow_id: str
    limit: int = 1000
    order_by: str = "pubished_at"
    workflow_run_id: str | None = None
    query: str | None = None
    group_by: list[str] | None = None
    agg: str | None = None


class CreateUserParams(BaseModel):
    tier: Literal["free", "pro", "enterprise"] = "free"  # "free" or "premium"
    settings: str | None = None  # JSON-serialized String of settings


UpdateUserParams = CreateUserParams


class CreateSecretParams(BaseModel):
    """Create a new secret.

    Secret types
    ------------
    - `custom`: Arbitrary user-defined types
    - `token`: A token, e.g. API Key, JWT Token (TBC)
    - `oauth2`: OAuth2 Client Credentials (TBC)"""

    type: Literal["custom"] = "custom"  # Support other types later
    name: str
    description: str | None = None
    keys: list[SecretKeyValue]
    tags: dict[str, str] | None = None

    @staticmethod
    def from_strings(name: str, keyvalues: list[str]) -> CreateSecretParams:
        keys = [SecretKeyValue.from_str(kv) for kv in keyvalues]
        return CreateSecretParams(name=name, keys=keys)

    def reveal_keys(self) -> dict[str, str]:
        return [kv.reveal() for kv in self.keys]

    @field_validator("keys")
    def validate_keys(cls, v, values):
        if not v:
            raise ValueError("Keys cannot be empty")
        # Ensure keys are unique
        if len({kv.key for kv in v}) != len(v):
            raise ValueError("Keys must be unique")
        return v


UpdateSecretParams = CreateSecretParams


class SearchSecretsParams(BaseModel):
    names: list[str]


class Tag(BaseModel):
    tag: str
    value: str
    is_ai_generated: bool = False


class Suppression(BaseModel):
    condition: str
    result: str  # Should evaluate to 'true' or 'false'


class CaseContext(BaseModel):
    key: str
    value: str


class CaseParams(BaseModel):
    # SQLModel defaults
    id: str
    owner_id: str
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    # Case related fields
    workflow_id: str
    case_title: str
    payload: dict[str, Any]
    malice: Literal["malicious", "benign"]
    status: Literal["open", "closed", "in_progress", "reported", "escalated"]
    priority: Literal["low", "medium", "high", "critical"]
    context: ListModel[CaseContext]
    action: Literal[
        "ignore", "quarantine", "informational", "sinkhole", "active_compromise"
    ]
    suppression: ListModel[Suppression]
    tags: ListModel[Tag]


class CaseActionParams(BaseModel):
    tag: str
    value: str
    user_id: str | None = None


class CaseContextParams(BaseModel):
    tag: str
    value: str
    user_id: str | None = None


class SearchWebhooksParams(BaseModel):
    action_id: str | None = None
    workflow_id: str | None = None
    limit: int = 100
    order_by: str = "created_at"
    query: str | None = None
    group_by: list[str] | None = None
    agg: str | None = None


class TriggerWorkflowRunParams(BaseModel):
    action_key: str
    payload: dict[str, Any]


class StartWorkflowParams(BaseModel):
    entrypoint_key: str
    entrypoint_payload: dict[str, Any]


class StartWorkflowResponse(BaseModel):
    status: str
    message: str
    id: str


class CopyWorkflowParams(BaseModel):
    owner_id: str


class SecretResponse(BaseModel):
    id: str
    type: Literal["custom"]  # Support other types later
    name: str
    description: str | None = None
    keys: list[SecretKeyValue]


class CaseEventParams(BaseModel):
    type: str
    data: dict[str, str | None] | None


class UpsertWorkflowDefinitionParams(BaseModel):
    content: DSLInput


class UDFArgsValidationResponse(BaseModel):
    ok: bool
    message: str
    detail: Any | None = None


class CreateScheduleParams(BaseModel):
    entrypoint_ref: str
    entrypoint_payload: dict[str, Any] | None = None
    cron: str
