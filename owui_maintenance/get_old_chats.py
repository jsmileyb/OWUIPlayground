import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get your JWT token from the environment variable
jwt_token = os.getenv("OWUI_API_KEY")
if not jwt_token:
    raise ValueError("JWT token not found in .env file under OWUI_API_KEY")

# Optionally, get your base URL from the environment (or hardcode it)
base_url = os.getenv("OWUI_ROOT", "http://localhost")  # adjust as needed

# Construct the URL for the API key authentication endpoint
url = f"{base_url}/api/v1/auths/api_key"

# Set up the request headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {jwt_token}"
}

# Make the POST request
response = requests.post(url, headers=headers)
response.raise_for_status()  # Raise an error for bad responses

# Parse the JSON response and extract the API key
data = response.json()
api_key = data.get("api_key")
if not api_key:
    raise ValueError("API key not found in the response.")

print(f"Your API key is: {api_key}")
