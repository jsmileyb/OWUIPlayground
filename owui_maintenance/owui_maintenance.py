import os
import json
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

class OpenWebUIClient:
    """Client to handle authentication and API requests for Open WebUI."""
    
    def __init__(self):
        self.base_url = os.getenv("OWUI_ROOT")
        self.jwt_token = os.getenv("OWUI_API_KEY")
        self.api_key = None  # Store API key after retrieval
        self.report_dir = os.getenv("OWUI_REPORT_DIR")  # Default to 'reports' if not set
        
        if not self.jwt_token:
            raise ValueError("JWT token not found in .env file under OWUI_API_KEY")
        
    def authenticate(self):
        """Retrieve API key and store it in the instance for future calls."""
        url = f"{self.base_url}/api/v1/auths/api_key"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}"
        }
        
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        self.api_key = data.get("api_key")
        
        if not self.api_key:
            raise ValueError("API key not found in response.")
        
        print("API Key retrieved successfully.")

    def get_headers(self):
        """Returns the headers required for authenticated requests."""
        if not self.api_key:
            self.authenticate()  # Retrieve API key if not already set
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def get_users(self):
        """Example function to fetch users using the authenticated API key."""
        url = f"{self.base_url}/api/v1/users/"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()
    

    def get_all_chats(self):
        """Retrieve all chat logs from Open WebUI and save them to a JSON file."""
        url = f"{self.base_url}/api/v1/chats/all/db"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        chat_data = response.json()

        # Ensure the report directory exists
        os.makedirs(self.report_dir, exist_ok=True)

        # Generate a filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.report_dir, f"owui_chats_{timestamp}.json")

        # Save the chat data to a JSON file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=4)

        print(f"Chat logs saved to: {file_path}")

# Example Usage:
if __name__ == "__main__":
    client = OpenWebUIClient()
    client.authenticate()  # Retrieve API key once
    # users = client.get_users()
    # print(f"Users: {users}")
    client.get_all_chats()  # Fetch and save chats
    print("Chats saved to: owui_chats_<timestamp>.json")
