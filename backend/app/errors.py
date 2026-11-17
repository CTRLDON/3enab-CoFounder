"""Domain errors, mapped to HTTP responses in app/main.py."""

from __future__ import annotations


class MateError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, **detail: object) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFound(MateError):
    status_code = 404
    code = "not_found"


class Unauthorized(MateError):
    status_code = 401
    code = "unauthorized"


class Forbidden(MateError):
    status_code = 403
    code = "forbidden"


class ApprovalRequired(MateError):
    """A gated action was attempted without an explicit founder approval."""

    status_code = 403
    code = "approval_required"


class PolicyViolation(MateError):
    """A hard safety/policy rule. Founder approval cannot override it."""

    status_code = 403
    code = "policy_violation"


class InvalidTransition(MateError):
    status_code = 409
    code = "invalid_transition"


class VersionConflict(MateError):
    status_code = 409
    code = "version_conflict"


class AgentFailure(MateError):
    """The model was unavailable or produced unusable output. Never replaced by invented content."""

    status_code = 503
    code = "agent_failure"
