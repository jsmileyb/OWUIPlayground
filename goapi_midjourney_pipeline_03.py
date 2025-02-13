import time
import requests
import os
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class Pipeline:
    class Valves(BaseModel):
        """Holds API key and configuration values."""
        GOAPI_KEY: str = Field(default="")  # Remove hardcoded key

    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.name = "GoAPI Midjourney Pipeline"
        self.valves = self.Valves(
            GOAPI_KEY=os.getenv("GOAPI_KEY", "")
        )

        if not self.valves.GOAPI_KEY:
            raise ValueError("GOAPI_KEY is required. Set it in your .env file.")

        # API Endpoints
        self.TASK_URL = "https://api.goapi.ai/api/v1/task"
        self.TASK_STATUS_URL = self.TASK_URL + "/{task_id}"

        # Request headers
        self.headers = {
            "x-api-key": self.valves.GOAPI_KEY,
            "Content-Type": "application/json"
        }

    def submit_task(self, prompt: str, aspect_ratio: str = "1:1", process_mode: str = "fast") -> Union[str, None]:
        """Submits an image generation request to GoAPI and returns a task_id."""
        payload = {
            "model": "midjourney",
            "task_type": "imagine",
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "process_mode": process_mode
            }
        }

        print(f"\n[DEBUG] Submitting task with payload: {payload}")  # Debugging

        response = requests.post(self.TASK_URL, json=payload, headers=self.headers)
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"\n[ERROR] Response is not JSON. Raw response: {response.text}")
            return None

        print(f"\n[DEBUG] GoAPI Response: {data}")  # Debugging

        if response.status_code == 200 and data.get("code") == 200:
            task_id = data["data"]["task_id"]
            print(f"\n✅ Task submitted successfully! Task ID: {task_id}")
            return task_id
        else:
            print(f"\n[ERROR] Task submission failed: {data.get('message', 'Unknown error')}")
            return None

    def check_task_status(self, task_id: str) -> Union[List[str], None]:
        """Polls the task status until completion and returns the image URLs."""
        max_retries = 10
        retry_delay = 5  # Start with a 5-second delay

        for attempt in range(max_retries):
            print(f"\n[DEBUG] Checking task status (Attempt {attempt + 1})...")
            response = requests.get(self.TASK_STATUS_URL.format(task_id=task_id), headers=self.headers)

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError:
                print(f"\n[ERROR] Response is not JSON. Raw response: {response.text}")
                return None

            if response.status_code == 200 and data.get("code") == 200:
                task_data = data["data"]
                status = task_data["status"]
                progress = task_data["output"].get("progress", 0)
                print(f"\n[DEBUG] Task Status: {status} (Progress: {progress}%)")

                # Check for error information
                if task_data.get("error", {}).get("code"):
                    error_msg = task_data["error"].get("message", "Unknown error")
                    print(f"\n[ERROR] Task error: {error_msg}")
                    return None

                if status == "completed":
                    # Try to get image URLs from both possible sources
                    image_urls = task_data["output"].get("image_urls", [])
                    temp_urls = task_data["output"].get("temporary_image_urls", [])
                    
                    # Use temporary URLs if main URLs are not available
                    final_urls = image_urls if image_urls else temp_urls
                    
                    if final_urls:
                        print("\n🎉 Task completed! Here are the image URLs:")
                        for url in final_urls:
                            print(url)
                        return final_urls
                    else:
                        print("\n[ERROR] No image URLs found in completed response")
                        return None
                elif status == "failed":
                    print("\n[ERROR] Task failed. Check logs for details.")
                    return None
                elif status == "pending":
                    print(f"\n⏳ Task is still processing... Progress: {progress}%")
            else:
                print(f"\n[ERROR] Failed to retrieve task status: {data.get('message', 'Unknown error')}")

            # Wait before the next attempt
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

        print("\n[ERROR] Max retries reached. Task did not complete in time.")
        return None

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        """Handles the API request pipeline."""
        prompt = body.get("prompt", "").strip()

        if not prompt:
            return "[ERROR] No prompt provided."

        aspect_ratio = body.get("aspect_ratio", "1:1")
        process_mode = body.get("process_mode", "fast")

        task_id = self.submit_task(prompt, aspect_ratio, process_mode)
        if not task_id:
            return "[ERROR] Could not submit task."

        return self.check_task_status(task_id)
