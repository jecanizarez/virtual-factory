import json
import os

import litellm

from prompts import build_system_prompt
from tools import TOOL_SCHEMAS, dispatch

litellm.suppress_debug_info = True


def _max_turns():
    try:
        return max(1, int(os.environ.get("ORACULO_MAX_TOOL_TURNS", "6")))
    except ValueError:
        return 6


def _assistant_with_tool_calls(message):
    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ],
    }


def _format_args(arguments):
    try:
        params = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return arguments or ""
    if not isinstance(params, dict) or not params:
        return ""
    parts = []
    for key, value in params.items():
        value = str(value)
        if len(value) > 40:
            value = value[:37] + "..."
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def ask(question, history=None):
    messages = [{"role": "system", "content": build_system_prompt()}]
    for item in history or []:
        messages.append(item)
    messages.append({"role": "user", "content": question})

    for _ in range(_max_turns()):
        try:
            response = litellm.completion(
                model=os.environ.get("ORACULO_MODEL", "openai/deepseek-v4-flash"),
                messages=messages,
                tools=TOOL_SCHEMAS,
            )
        except Exception as e:
            yield f"[error calling the LLM: {e}]"
            yield "[check oraculo/.env — copy env.example and fill in your API key]"
            return

        message = response.choices[0].message
        if not message.tool_calls:
            yield message.content or ""
            return

        messages.append(_assistant_with_tool_calls(message))
        for call in message.tool_calls:
            print(f"  \033[2m🔧 {call.function.name}({_format_args(call.function.arguments)})\033[0m", flush=True)
            result = dispatch(call.function.name, _parse_args(call.function.arguments))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.function.name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    yield "[stopped after reaching ORACULO_MAX_TOOL_TURNS without a final answer]"


def _parse_args(arguments):
    try:
        params = json.loads(arguments or "{}")
        return params if isinstance(params, dict) else {}
    except json.JSONDecodeError:
        return {}
