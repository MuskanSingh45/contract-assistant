"""Errors raised by the ai/ package. The backend maps them to API error codes."""


class AIError(Exception):
    code = "ANALYSIS_FAILED"


class AIUnavailable(AIError):
    """Ollama unreachable or model not pulled."""

    code = "AI_UNAVAILABLE"


class AITimeout(AIError):
    code = "AI_TIMEOUT"


class InvalidAIOutput(AIError):
    """Model output failed JSON/schema validation after the retry."""

    code = "INVALID_AI_OUTPUT"
