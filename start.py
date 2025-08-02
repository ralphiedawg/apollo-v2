import subprocess
from langchain_ollama import OllamaLLM
from langchain.agents import Tool, initialize_agent

# Tool: Check health
def check_health(_: str) -> str:
    try:
        out = subprocess.run(
            ["./go/apolloctl", "check_health"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return out.stdout
    except subprocess.CalledProcessError as e:
        return f"Health check failed: {e.stderr}"

# Tool: Get version
def get_version(_: str) -> str:
    try:
        out = subprocess.run(
            ["./go/apolloctl", "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return out.stdout
    except subprocess.CalledProcessError as e:
        return f"Version command failed: {e.stderr}"

# Tool: Canvas sync
def canvas_sync(_: str) -> str:
    try:
        out = subprocess.run(
            ["./go/apolloctl", "canvas_sync"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return out.stdout
    except subprocess.CalledProcessError as e:
        return f"Canvas sync failed: {e.stderr}"

llm = OllamaLLM(model="gemma3:4b")

tools = [
    Tool(
        name="check_health",
        func=check_health,
        description="Checks the health status of the Ollama system."
    ),
    Tool(
        name="get_version",
        func=get_version,
        description="Returns the version of Apollo V2 CLI."
    ),
]

agent = initialize_agent(
    tools,
    llm,
    agent_type="zero-shot-react-description"
)

def main():
    print("Apollo chat agent (intent execution demo). Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        result = agent.run(user_input)
        print(f"Apollo: {result}")

if __name__ == "__main__":
    main()
