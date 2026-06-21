import time
from dataclasses import dataclass
from typing import Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    get_buffer_string,
)
from langchain_core.messages.ai import AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from portfolio_model.core.prompts import PORTFOLIO_SYSTEM_PROMPT
from portfolio_model.llms import (
    llm_quen_stream,
    llm_quen_stream_premium,
    llm_quen_summary_model,
    llm_quen_summary_model_premium,
)

# TODO: import your tools once ready, e.g.
#   from portfolio_model.core.tools import retrieve_information

memory = MemorySaver()
load_dotenv()


class InvokeRateLimitError(Exception):
    pass


def _invoke_with_retry(model, messages, max_attempts: int = 4, wait_seconds: int = 2):
    """Call model.invoke with up to max_attempts retries, waiting wait_seconds between each."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(max_attempts):
        try:
            return model.invoke(messages)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(wait_seconds)
    raise last_exc


@dataclass
class FinalState:
    values: Any


class StatePortfolioChat(MessagesState):
    query: str
    chat_history: Annotated[list[AnyMessage], add_messages]
    ch_string: Any | None
    are_previous_queries_required: bool
    use_premium: bool


def _get_filtered_messages(messages: list, summary_model=None) -> list:
    """Drop SystemMessages; summarise older messages when history exceeds 20."""
    if summary_model is None:
        summary_model = llm_quen_summary_model
    filtered = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    if len(filtered) <= 20:
        return filtered

    older = filtered[:-20]
    recent = filtered[-20:]

    # Slide boundary left so recent never starts with a dangling ToolMessage.
    while older and isinstance(recent[0], ToolMessage):
        recent = [older[-1]] + recent
        older = older[:-1]

    try:
        summary_response = _invoke_with_retry(
            summary_model,
            [
                SystemMessage(
                    content=(
                        "Summarise the following conversation history concisely. "
                        "Capture all key topics discussed, user interests, and any "
                        "pending questions. Be thorough but brief."
                    )
                ),
                HumanMessage(content=get_buffer_string(older)),
            ],
        )
    except Exception:  # noqa: BLE001
        # Summarization failed after all retries — skip it and return recent messages only.
        return recent
    summary_text = (
        summary_response.content
        if isinstance(summary_response.content, str)
        else str(summary_response.content)
    )
    return [
        HumanMessage(content=f"[Conversation history summary]\n{summary_text}")
    ] + recent


def portfolio_assistant(state: StatePortfolioChat):
    use_premium = state.get("use_premium", False)
    stream_model = llm_quen_stream_premium if use_premium else llm_quen_stream
    sum_model = (
        llm_quen_summary_model_premium if use_premium else llm_quen_summary_model
    )

    query = state.get("query")
    messages = state.get("messages")
    are_previous_queries_required = state.get("are_previous_queries_required")
    filtered_messages = _get_filtered_messages(messages, sum_model)

    query_message = (
        [HumanMessage(content=f"User query: <user_query> {query} </user_query>")]
        if are_previous_queries_required
        else []
    )

    full_messages = (
        [SystemMessage(content=PORTFOLIO_SYSTEM_PROMPT)]
        + filtered_messages
        + query_message
    )

    try:
        response = _invoke_with_retry(stream_model, full_messages)
    except Exception as exc:
        if use_premium:
            msg = (
                "**Rate limit is currently over.** Please contact Eshant directly:\n\n"
                "📧 [eshantdas4@gmail.com](mailto:eshantdas4@gmail.com)\n\n"
                "🔗 [linkedin.com/in/eshantdas](https://linkedin.com/in/eshantdas)"
            )
        else:
            msg = (
                "**The rate limit may have been hit.** You can still reach Eshant directly "
                "to ask more questions:\n\n"
                "📧 [eshantdas4@gmail.com](mailto:eshantdas4@gmail.com)\n\n"
                "🔗 [linkedin.com/in/eshantdas](https://linkedin.com/in/eshantdas)"
            )
        raise InvokeRateLimitError(msg) from exc

    return {
        "messages": query_message + [response],
        "ch_string": get_buffer_string(query_message + [response]),
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
# _tools: list[BaseTool] = []  # TODO: replace with [retrieve_information]

builder: StateGraph[
    StatePortfolioChat, None, StatePortfolioChat, StatePortfolioChat
] = StateGraph(StatePortfolioChat)

builder.add_node("portfolio_assistant", portfolio_assistant)
# builder.add_node("tools", ToolNode(tools=_tools))
builder.add_edge(START, "portfolio_assistant")
# builder.add_conditional_edges("portfolio_assistant", tools_condition)
# builder.add_edge("tools", "portfolio_assistant")
builder.add_edge("portfolio_assistant", END)

react_graph: CompiledStateGraph[
    StatePortfolioChat, None, StatePortfolioChat, StatePortfolioChat
] = builder.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# Public streaming entry point
# ---------------------------------------------------------------------------
async def generate_response(
    query: str,
    session_id: str = "1",
    are_previous_queries_required: bool = True,
    use_premium: bool = False,
):
    config = {"configurable": {"thread_id": session_id}}

    try:
        async for chunk in react_graph.astream(
            {
                "query": query,
                "are_previous_queries_required": are_previous_queries_required,
                "use_premium": use_premium,
            },
            config,
            stream_mode="messages",
        ):
            if (
                chunk[0].content
                and isinstance(chunk[0], AIMessageChunk)
                and chunk[1]["ls_temperature"] == 0.1
            ):
                chunk_content = chunk[0].content
                if isinstance(chunk_content, str):
                    yield chunk_content
                elif (
                    isinstance(chunk_content, list)
                    and chunk_content[0].get("type") == "text"
                    and "text" in chunk_content[0]
                ):
                    yield chunk_content[0]["text"]
    except InvokeRateLimitError as exc:
        yield str(exc)

    yield {"done": True}
