"""
Phoenix AI Observability Instrumentation for Eworks OS Agents.

This module provides decorators, context managers, and utilities for tracing
agent executions, LLM calls, tool invocations, and workflow steps with Arize Phoenix.

Usage:
    from eworks.core.phoenix_instrumentation import (
        trace_agent_execution,
        trace_llm_call,
        trace_tool_call,
        trace_workflow_step,
    )

    @trace_agent_execution("prospector")
    async def my_agent_run(self, goal: str):
        # Agent logic here
        pass

    async def llm_interaction():
        with trace_llm_call("generate_outreach_message") as span:
            response = await my_llm.generate(...)
            span.set_attributes({"prompt_length": len(prompt)})
        return response
"""

from __future__ import annotations

import functools
import logging
from contextvars import ContextVar
from typing import Any, Callable, Optional, TypeVar
from contextlib import asynccontextmanager, contextmanager

try:
    import phoenix as px
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False

logger = logging.getLogger(__name__)

# Context variables to track nested spans
_current_span: ContextVar[Optional[Any]] = ContextVar("current_span", default=None)

T = TypeVar("T")


def _get_phoenix():
    """Get Phoenix module or None if not available."""
    if PHOENIX_AVAILABLE:
        return px
    return None


def _safe_span(name: str, attributes: Optional[dict] = None) -> Any:
    """
    Safely create a Phoenix span, returning a no-op context if Phoenix is unavailable.

    Args:
        name: Name of the span.
        attributes: Optional dict of attributes to attach to the span.

    Returns:
        A context manager that yields a span object (or None if Phoenix unavailable).
    """
    px = _get_phoenix()
    if not px:
        return _noop_context()

    try:
        span = px.trace_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span
    except Exception as e:
        logger.debug(f"Failed to create Phoenix span '{name}': {e}")
        return _noop_context()


@contextmanager
def _noop_context():
    """No-op context manager for when Phoenix is unavailable."""
    yield None


def trace_agent_execution(agent_name: str) -> Callable:
    """
    Decorator to trace the execution of an agent method.

    Captures:
    - Agent name
    - Method name
    - Input parameters (goal, prompt, etc.)
    - Execution time
    - Output/result
    - Errors (if any)

    Args:
        agent_name: Name of the agent (e.g., "prospector", "publisher", "closer").

    Returns:
        Decorated function that traces execution with Phoenix.

    Example:
        @trace_agent_execution("prospector")
        async def run(self, goal: str):
            # Agent logic
            return result
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            span_name = f"agent_execution_{agent_name}_{func.__name__}"
            with _safe_span(
                span_name,
                {
                    "agent": agent_name,
                    "method": func.__name__,
                    "is_async": True,
                },
            ) as span:
                try:
                    # Capture input params
                    if span and kwargs:
                        for k, v in kwargs.items():
                            if isinstance(v, (str, int, float, bool)):
                                span.set_attribute(f"input_{k}", v)
                    
                    result = await func(*args, **kwargs)
                    
                    # Capture output summary
                    if span and result:
                        if isinstance(result, dict):
                            if "status" in result:
                                span.set_attribute("output_status", result["status"])
                            if "count" in result:
                                span.set_attribute("output_count", result["count"])
                        elif isinstance(result, str):
                            span.set_attribute("output_length", len(result))
                    
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("error", str(e))
                        span.set_attribute("error_type", type(e).__name__)
                    logger.error(f"Agent execution failed: {e}")
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            span_name = f"agent_execution_{agent_name}_{func.__name__}"
            with _safe_span(
                span_name,
                {
                    "agent": agent_name,
                    "method": func.__name__,
                    "is_async": False,
                },
            ) as span:
                try:
                    if span and kwargs:
                        for k, v in kwargs.items():
                            if isinstance(v, (str, int, float, bool)):
                                span.set_attribute(f"input_{k}", v)
                    
                    result = func(*args, **kwargs)
                    
                    if span and result:
                        if isinstance(result, dict):
                            if "status" in result:
                                span.set_attribute("output_status", result["status"])
                            if "count" in result:
                                span.set_attribute("output_count", result["count"])
                        elif isinstance(result, str):
                            span.set_attribute("output_length", len(result))
                    
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("error", str(e))
                        span.set_attribute("error_type", type(e).__name__)
                    logger.error(f"Agent execution failed: {e}")
                    raise

        # Return the appropriate wrapper based on whether func is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def trace_llm_call(
    model: str,
    operation: str = "inference",
    attributes: Optional[dict] = None,
):
    """
    Async context manager to trace LLM calls (e.g., Claude, Gemini, GROQ).

    Captures:
    - Model name
    - Operation type (inference, embedding, etc.)
    - Token counts (if available)
    - Prompt/completion lengths
    - Custom attributes

    Args:
        model: Model identifier (e.g., "claude-3-sonnet", "gemini-2.5-flash").
        operation: Type of operation (default: "inference").
        attributes: Optional dict of additional attributes.

    Yields:
        A Phoenix span object (or None if Phoenix unavailable).

    Example:
        async with trace_llm_call("claude-3-sonnet") as span:
            response = await client.messages.create(...)
            if span:
                span.set_attribute("prompt_tokens", response.usage.input_tokens)
                span.set_attribute("completion_tokens", response.usage.output_tokens)
            yield response
    """
    span_attrs = {
        "model": model,
        "operation": operation,
        "type": "llm_call",
    }
    if attributes:
        span_attrs.update(attributes)

    px = _get_phoenix()
    if not px:
        yield None
        return

    try:
        span = px.trace_span(f"llm_{model}_{operation}", attributes=span_attrs)
        yield span
    except Exception as e:
        logger.debug(f"Failed to create LLM span: {e}")
        yield None


@contextmanager
def trace_tool_call(
    tool_name: str,
    operation: str = "execute",
    attributes: Optional[dict] = None,
):
    """
    Context manager to trace external tool calls (web search, file I/O, terminal, etc.).

    Captures:
    - Tool name
    - Operation type
    - Success/failure status
    - Custom attributes (e.g., result counts, file sizes)

    Args:
        tool_name: Name of the tool (e.g., "web_search", "read_file", "terminal").
        operation: Type of operation (default: "execute").
        attributes: Optional dict of additional attributes.

    Yields:
        A Phoenix span object (or None if Phoenix unavailable).

    Example:
        with trace_tool_call("web_search", attributes={"query": "AI agents"}) as span:
            results = web_search(...)
            if span:
                span.set_attribute("result_count", len(results))
            yield results
    """
    span_attrs = {
        "tool": tool_name,
        "operation": operation,
        "type": "tool_call",
    }
    if attributes:
        span_attrs.update(attributes)

    px = _get_phoenix()
    if not px:
        yield None
        return

    try:
        span = px.trace_span(f"tool_{tool_name}_{operation}", attributes=span_attrs)
        yield span
    except Exception as e:
        logger.debug(f"Failed to create tool span: {e}")
        yield None


@contextmanager
def trace_workflow_step(
    step_name: str,
    agent: Optional[str] = None,
    attributes: Optional[dict] = None,
):
    """
    Context manager to trace a workflow step within an agent.

    Captures:
    - Step name
    - Agent name (optional)
    - Step-specific attributes
    - Execution status

    Args:
        step_name: Name of the workflow step (e.g., "generate_ideas", "create_proposal").
        agent: Optional agent name for context.
        attributes: Optional dict of additional attributes.

    Yields:
        A Phoenix span object (or None if Phoenix unavailable).

    Example:
        with trace_workflow_step("generate_outreach_message", agent="prospector") as span:
            message = generate_message(...)
            if span:
                span.set_attribute("message_length", len(message))
            yield message
    """
    span_attrs = {
        "step": step_name,
        "type": "workflow_step",
    }
    if agent:
        span_attrs["agent"] = agent
    if attributes:
        span_attrs.update(attributes)

    px = _get_phoenix()
    if not px:
        yield None
        return

    try:
        span = px.trace_span(f"workflow_{step_name}", attributes=span_attrs)
        yield span
    except Exception as e:
        logger.debug(f"Failed to create workflow step span: {e}")
        yield None


def set_span_attribute(key: str, value: Any) -> None:
    """
    Set an attribute on the current active span (if one exists).

    Args:
        key: Attribute key.
        value: Attribute value (should be JSON-serializable).
    """
    span = _current_span.get()
    if span:
        try:
            span.set_attribute(key, value)
        except Exception as e:
            logger.debug(f"Failed to set span attribute: {e}")


def record_event(name: str, attributes: Optional[dict] = None) -> None:
    """
    Record an event on the current active span.

    Args:
        name: Event name (e.g., "proposal_generated", "interaction_detected").
        attributes: Optional dict of event attributes.
    """
    px = _get_phoenix()
    if not px:
        return

    try:
        px.log_event(name, attributes=attributes)
    except Exception as e:
        logger.debug(f"Failed to record event: {e}")


__all__ = [
    "trace_agent_execution",
    "trace_llm_call",
    "trace_tool_call",
    "trace_workflow_step",
    "set_span_attribute",
    "record_event",
    "PHOENIX_AVAILABLE",
]
