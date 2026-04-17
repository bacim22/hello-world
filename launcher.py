import subprocess
import sys
import os

def launch():
    print("🚀 ActuAI Reserve Agent Launcher")

    # Check for .env file
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found. Copying .env.example to .env...")
        import shutil
        shutil.copy(".env.example", ".env")
        print("Please edit .env with your API keys.")

    print("🔧 Starting Chainlit application...")
    try:
        subprocess.run(["chainlit", "run", "app.py", "-w"], check=True)
    except KeyboardInterrupt:
        print("\n👋 ActuAI stopped.")
    except Exception as e:
        print(f"❌ Error launching app: {e}")

if __name__ == "__main__":
    launch()
