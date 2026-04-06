import sys
import os

# Add the current directory to sys.path so we can import agents
sys.path.append(os.getcwd())

from agents.screen_agent import ScreenAgent

def main():
    agent = ScreenAgent()
    print("Capturing screen and performing OCR...")
    result = agent.execute("read")
    
    if result.get("success"):
        print("\n--- OCR RESULTS ---")
        print(result.get("text"))
        print("-------------------\n")
    else:
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    main()
