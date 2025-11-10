from langchain_openai import ChatOpenAI
import streamlit as st
import os


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

LOCAL_MODEL_NAME = os.environ.get("LOCAL_MODEL_NAME", "llama3.2:latest")
LOCAL_BASE_URL = os.environ.get("LOCAL_BASE_URL", "http://ollama:11434/v1")

REMOTE_MODEL_NAME = os.environ.get("REMOTE_MODEL_NAME", "qwen/qwen3-30b-a3b:free")
REMOTE_BASE_URL = os.environ.get("REMOTE_BASE_URL", "https://openrouter.ai/api/v1")

####################### Models #######################

local_llm = ChatOpenAI(
    model = LOCAL_MODEL_NAME,
    api_key = "ollama",  # dummy value for local usage
    base_url = LOCAL_BASE_URL
)

cloud_llm = ChatOpenAI(
    model = REMOTE_MODEL_NAME,
    api_key = OPENROUTER_API_KEY,
    base_url = REMOTE_BASE_URL
)

####################### App #######################

st.title("Talk to me...")

think_harder = st.checkbox(
    "Think harder",
    value = False
)

st.session_state.setdefault(
    "messages", 
    []
)

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

prompt = st.chat_input("Type your message...")

if prompt:

    # user message 
    st.session_state["messages"].append(
        {
            "role": "user", 
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.write(prompt)


    # context management
    context = ""

    for msg in st.session_state["messages"]:
        role = msg["role"]
        content = msg["content"]
        context += f"{role}: {content}\n"

    # manage model selection
    if think_harder:
        llm = cloud_llm
    else:
        llm = local_llm

    # get response from model
    response = llm.invoke(
        context
    )

    # assistant message
    st.session_state["messages"].append(
        {
            "role": "assistant", 
            "content": response.content
        }
    )

    with st.chat_message("assistant"):
        st.write(response.content)