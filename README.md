# Sovereign AI Assistant

This repository contains the code and resources for the Sovereign AI Assistant, an advanced AI-powered tool designed to provide personalized assistance and support for various tasks on a host device. The basic assistant is built using open-source technologies and can be customized to meet specific user needs.

---
## Demo
!demo is loading! 
<center>
<img src="docs/Demo_GraphRAG_Agent.gif" alt="Project Overview" width="1000"/>
</center>


---

## Features

1. Chat Interface to interact with the AI assistant.
2. Integration with Ollama LLM for advanced language processing.
3. Dockerized setup for easy deployment and scalability.
4. Choice between small LLM (sLLM) and large LLM for different performance needs inntegrating both Ollama and cloud based service from OpenRouter.

---

## Tech Stack

- **Docker**: Used for containerization of Ollama LLM service to ensure consistent environments across different systems.
- **Ollama**: Provides the large language model (LLM) capabilities for the assistant.
- **VS-Code**: Integrated development environment used for coding and debugging.
- **Python**: Primary programming language used for the assistant's development.
- **LangChain**: Framework for building applications with language models.
- **Streamlit**: Used for creating the user interface of the assistant.

---

## Project Structure
```bash
sovereign_ai_assistant/
├── docs/
├── src/ 
│   ├── data/*                      # data folder for Neo4j and other data storage
│   ├── frontend/                   # frontend code for the chat interface
│   │   ├── __init__.py
│   │   └── app.py
│   ├── backend/                    # backend code for handling requests and integrating with Ollama and Neo4j
│   │   ├── iirds/
│   │   │   ├── __init__.py
│   │   │   ├── content_extract.py
│   │   │   ├── ingest.py
│   │   │   └── rdf_extract.py
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── chroma_store.py
│   │   │   ├── embeddings.py
│   │   │   ├── chunking.py
│   │   │   ├── neo4j_store.py
│   │   │   └── pipeline.py
│   │   ├── __init__.py
│   │   ├── llm_router.py
│   │   └── main.py
│   ├── .env
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └──  requirements.txt
├── .gitignore
├── .dockerignore
└── README.md
```

## Getting Started

### Prerequisites
- Docker installed on your machine.
- Basic knowledge of Docker and command-line operations.
- Python 3.12 or higher installed.
- VS-Code installed for development.

### Setup Instructions

1. **Clone the Repository**
    ```bash
    git clone <link>
    ```

2. **Navigate to the Project Directory**
    ```bash
    cd sovereign-ai-assistant
    ```

3. **Configure Environment Variables**
    - Open the `.env` file located in the `src` directory.
    - Set the `OPENROUTER_API_KEY` with your OpenRouter API key.
    - Adjust other environment variables as needed.

4. **Build and Run the Docker Containers for the application**
    ```bash
    # navigate to the src directory where the implementation lives
    cd src

    # build and start the containers in detached mode
    docker compose up -d --build

    # check the status of the containers
    docker compose ps

    # in a new Terminal window, tail the logs to monitor startup
    docker compose logs -f frontend   # Ctrl+C to stop tailing
    docker compose logs -f backend    # Ctrl+C to stop tailing
    ```

5. **Open Chat and DB Interfaces**
    - **Chat Interface:** Open your web browser and navigate to `http://localhost:8501` or `http://127.0.0.1:8501`.
    - **Neo4j Database Interface:** Open your web browser and navigate to `http://localhost:7474/browser/` or `http://127.0.0.1:7474/browser/`. Use the credentials set in the `.env` file to log in.

6. **Reboot Docker Containers**
    ```bash
    docker compose up -d
    ```

7. **Download Models in Ollama**
    ```bash
    docker compose exec ollama sh -lc 'ollama pull llama3.2:latest'          # pulling sLLM, large, GPU-recommended
    docker compose exec ollama sh -lc 'ollama pull nomic-embed-text:latest'  # embedding model
    ```

8. **Small Health Check Ollama**
    ```bash
    docker compose exec ollama sh -lc 'ollama --version'
    docker compose exec ollama sh -lc 'ollama list'
    docker compose exec ollama sh -lc 'ollama pull llama3.2:3b'     # small, CPU-friendly
    docker compose exec ollama sh -lc 'ollama run llama3.2:3b "Say hello in one short   sentence."'
    ```

9. **Rebooting the App**
    ```bash
    docker compose stop && docker compose up -d
    ```

10. **Access the Chat Interface**
    - Open your web browser and navigate to `http://localhost:8501` to access the chat interface of the Sovereign AI Assistant.

11. **Shutting Down**
    To stop and remove the Docker containers, run:
    ```bash
    docker compose down
    ```

    or use the following command to also remove anonymous volumes:
    ```bash
    docker compose down -v
    ```

---
### Using the Application

1. **UI Interaction**
    - Sidebar on the left for Data Ingestion, iiRDS-Filtering and Agent Settings (e.g., local model (default) or switch to remote models, adjusting temperature).
    - Main chat area for interacting with the AI assistant.
    - Response area for displaying the assistant's replies.

2. **Data Ingestion**
    - Convert your .iirds to a .zip file. Your .iirds folder should contain a folder for the metadata (META-INF) and a folder for the content (content) next to a mimetype xml-file.
    - Upload the .zip file using the Data Ingestion section in the sidebar. Start with the first folder of your iiRDS collection and then repeat the process for the remaining folders. You should get a confirmation message once the ingestion is complete.

3. **Chatting with the Assistant**
    - Open the chat interface at `http://localhost:8501`.
    - Type your queries or commands in the input box at the bottom of the chat area.
    - Press Enter or click the send button to submit your message.
    - The assistant will process your input and provide a response in the chat area.

    > **_NOTE:_**
        In case you use the OpenRouter API, ensure your API key is correctly set in the `.env` file. 
        Sometimes, the free tier of OpenRouter may have limitations or downtimes and a response with an error message may occur. Simply retry your query after some time.

4. **Running Queries on Neo4j**
    - Access the Neo4j browser at `http://localhost:7474/browser/`.
    - Use Cypher queries to interact with the ingested iiRDS data.


5. **Running Queries through the CLI**
    - You can also run Cypher queries directly from the command line using Docker:
    ```bash
    curl -X POST "http://localhost:8001/query" \
        -H "Content-Type: application/json" \
        -d '{
            "question": "How do I safely operate the device?",
            "filters": {},
            "mode": "local",
            "debug": true
        }'
    ```
