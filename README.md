# Sovereign AI Assistant

This repository contains the code and resources for the Sovereign AI Assistant, an advanced AI-powered tool designed to provide personalized assistance and support for various tasks on a host device. The basic assistant is built using open-source technologies and can be customized to meet specific user needs.

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
|-src
|  |-app.py                 # Main application file for the AI assistant
|  |-requirements.txt       # Python dependencies
|  |-Dockerfile             # Dockerfile for building the application container
|  |-docker-compose.yaml    # Docker Compose file for orchestrating containers
|  |-.env                   # Environment variables for configuration
|
|-README.md                 # Project documentation
|-.gitignore                # Git ignore file
|-License                   # License information
```

---

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

3. **Build and Run the Docker Container for Ollama LLM**
    ```bash
    docker compose up -d --build
    docker compose ps
    docker compose logs -f ai-app   # Ctrl+C to stop tailing 
    docker compose logs -f ollama   # watch for “Serving on 0.0.0.0:11434”
    ```

4. **Reboot Docker Containers**
    ```bash
    docker compose up -d
    ```

5. **Small Health Check**
    ```bash
    docker compose exec ollama sh -lc 'ollama --version'
    docker compose exec ollama sh -lc 'ollama list'
    docker compose exec ollama sh -lc 'ollama pull llama3.2:3b'     # small, CPU-friendly
    docker compose exec ollama sh -lc 'ollama run llama3.2:3b "Say hello in one short   sentence."'

    ```

6. **Rebooting the App**
    ```bash
    docker compose stop && docker compose up -d
    ```

7. **Access the Chat Interface**
    Open your web browser and navigate to `http://localhost:8501` to access the chat interface of the Sovereign AI Assistant.

8. **Shutting Down**
    To stop and remove the Docker containers, run:
    ```bash
    docker compose down
    ```

    or use the following command to also remove anonymous volumes:
    ```bash
    docker compose down -v
    ```



