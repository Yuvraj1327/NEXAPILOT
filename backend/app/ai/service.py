"""
The AI service: turns a natural-language message into a validated
structured action.

Flow: user message -> Claude (with read-only data tools) -> Claude calls
read-only tools zero or more times -> Claude calls `submit_nexapilot_action`
-> backend validates that input against app.schemas.ai.NexaPilotAIAction ->
on failure, the validation error is handed back to Claude to self-correct
(bounded retries) -> on success, the validated action is returned to the
caller (app/api/v1/endpoints/ai.py), which decides what to persist.

Nothing in this file, or anything it calls, can sign or send a
transaction. It can only read (via app.ai.tools's read-only dispatch) and
return a validated Pydantic object.
"""

import json
import logging
from typing import List, Tuple

from anthropic.types import ToolUseBlock
from pydantic import ValidationError

from app.ai.client import get_anthropic_client
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.tools import (
    READ_ONLY_TOOL_DEFINITIONS,
    SUBMIT_ACTION_TOOL_DEFINITION,
    ToolContext,
    dispatch_read_only_tool,
)
from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.ai import NexaPilotAIAction

logger = logging.getLogger("nexapilot.ai")

SUBMIT_TOOL_NAME = "submit_nexapilot_action"
_ALL_TOOLS = READ_ONLY_TOOL_DEFINITIONS + [SUBMIT_ACTION_TOOL_DEFINITION]


class AIServiceError(AppError):
    status_code = 502
    code = "AI_SERVICE_ERROR"


class AIOutputValidationError(AppError):
    status_code = 502
    code = "AI_OUTPUT_INVALID"


def run_ai_query(*, ctx: ToolContext, message: str) -> Tuple[NexaPilotAIAction, List[str]]:
    """Run the full tool-use loop for one user message.

    Returns (validated_action, tools_used). Raises AIServiceError /
    AIOutputValidationError / AIConfigurationError (all AppError
    subclasses) on failure — never returns anything unvalidated.
    """
    client = get_anthropic_client()
    messages: list = [{"role": "user", "content": message}]
    tools_used: List[str] = []
    output_retries = 0

    for _ in range(settings.ai_max_tool_iterations):
        try:
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.ai_max_tokens,
                system=SYSTEM_PROMPT,
                tools=_ALL_TOOLS,
                tool_choice={"type": "any"},
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001 — any SDK/network failure
            logger.error("Anthropic API call failed: %s", exc)
            raise AIServiceError(f"Claude API call failed: {exc}") from exc

        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks: List[ToolUseBlock] = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            raise AIServiceError("Claude responded without calling a tool.")

        submit_block = next((b for b in tool_use_blocks if b.name == SUBMIT_TOOL_NAME), None)
        final_action = None
        validation_error: ValidationError | None = None

        if submit_block is not None:
            try:
                final_action = NexaPilotAIAction.model_validate(submit_block.input)
            except ValidationError as exc:
                validation_error = exc
                logger.info("Claude's structured action failed validation (attempt %d): %s", output_retries + 1, exc)

        tool_results = []
        for block in tool_use_blocks:
            if block is submit_block:
                if final_action is not None:
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": "Accepted."}
                    )
                else:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Your submission was invalid: {validation_error}. Correct it and call {SUBMIT_TOOL_NAME} again.",
                            "is_error": True,
                        }
                    )
                continue

            tools_used.append(block.name)
            try:
                result = dispatch_read_only_tool(block.name, block.input, ctx)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                )
            except AppError as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Tool error: {exc.message}",
                        "is_error": True,
                    }
                )

        if final_action is not None:
            return final_action, tools_used

        if validation_error is not None:
            output_retries += 1
            if output_retries > settings.ai_max_output_retries:
                raise AIOutputValidationError(
                    f"Claude's structured output kept failing validation after {output_retries} attempts: "
                    f"{validation_error}"
                )

        messages.append({"role": "user", "content": tool_results})

    raise AIServiceError(
        f"Claude did not produce a final structured action within {settings.ai_max_tool_iterations} tool-use turns."
    )
