import subprocess

DEFAULT_MODEL = "phi3:3.8b"

def list_models():
    """Returns a list of models installed in ollama."""
    try:
        proc = subprocess.run(["ollama", "list"], capture_output=True, check=False, timeout=10)
        lines = proc.stdout.decode(errors="ignore").splitlines()
        models = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models or ["llama2"]
    except Exception as e:
        return [DEFAULT_MODEL]

def ask_ai(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 600, **opts) -> str:
    """Send a prompt to Ollama and return the model's response. Handles timeout/errors."""
    cmd = ["ollama", "run", model]
    # (TODO: pass fun options as env/config if needed)
    try:
        proc = subprocess.run(
            cmd,
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout
        )
        output = proc.stdout.decode("utf-8", errors="ignore")
        err = proc.stderr.decode("utf-8", errors="ignore")
        if not output.strip() and err:
            return f"[Ollama error: {err.strip()}]"
        return output.strip() or "[No response from model]"
    except subprocess.TimeoutExpired:
        return "[Ollama error: response timed out]"
    except Exception as e:
        return f"[Ollama error: {e}]"

if __name__ == "__main__":
    models = list_models()
    print(f"Available Ollama models: {models}")
    print(f"Default model: {DEFAULT_MODEL}")
    print("Ask the AI (type 'quit' to exit):")
    picked = input(f"Pick model or ENTER for '{DEFAULT_MODEL}': ").strip() or DEFAULT_MODEL
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        print("Thinking...")
        response = ask_ai(user_input, model=picked)
        print(f"AI: {response}\n")
