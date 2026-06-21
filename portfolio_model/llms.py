import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


llm_quen_stream = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.1,
    reasoning_effort="none",
    api_key=os.environ.get("GROQ_API_KEY1"),
)

llm_quen_summary_model = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.0,
    reasoning_effort="none",
    api_key=os.environ.get("GROQ_API_KEY1"),
)


llm_quen_stream_premium = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.1,
    reasoning_effort="none",
    api_key=os.environ.get("GROQ_API_KEY2"),
)

llm_quen_summary_model_premium = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.0,
    reasoning_effort="none",
    api_key=os.environ.get("GROQ_API_KEY2"),
)
