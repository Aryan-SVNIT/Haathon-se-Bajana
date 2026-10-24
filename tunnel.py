"""Helper script to launch an ngrok tunnel to the multiplayer server.

Usage:
    .\\.venv\\python.exe tunnel.py <optional_authtoken>
"""
import sys
import os
from pyngrok import ngrok

def main():
    token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NGROK_AUTHTOKEN")
    if token:
        ngrok.set_auth_token(token)
        print("Authtoken saved.")
    
    try:
        tunnel = ngrok.connect(8080, "http")
        print(f"\n==========================================")
        print(f"NGROK TUNNEL ACTIVE: {tunnel.public_url}")
        print(f"==========================================\n")
        ngrok_process = ngrok.get_ngrok_process()
        ngrok_process.proc.wait()
    except Exception as e:
        print(f"Error starting ngrok tunnel: {e}")
        print("To get a free token, sign up at: https://dashboard.ngrok.com/signup")
        print("Then run: .\\.venv\\python.exe tunnel.py <YOUR_AUTHTOKEN>")

if __name__ == "__main__":
    main()
