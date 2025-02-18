"""
title: GoAPI/Midjourney API Pipe
author: Smiley Baltz
funding_url: https://github.com/jsmileyb
version: 0.1
description: Initial testing of the GoAPI/Midjourney API

DEVELOPER NOTES:

- Explore the OWUI logs to view/solve for addtional API calls to endpoints (title and tag generation calls)

"""

import os
from pydantic import BaseModel, Field
from typing import Generator, List, Union, Dict, Any, Optional
import aiohttp
import asyncio
import json


class Pipe:
    class Valves(BaseModel):
        BASE_URL: str = Field(default="https://api.goapi.ai/api/v1", description="Base URL for GoAPI")
        GOAPI_KEY: str = Field(default="", description="API key for GoAPI")
        MODEL_ID: str = Field(default="midjourney", description="Model identifier")
        DEFAULT_ASPECT_RATIO: str = Field(default="1:1", description="Default aspect ratio for image generation")
        DEFAULT_PROCESS_MODE: str = Field(default="fast", description="Default processing mode for image generation")

    def __init__(self):
        self.type = "pipe"
        self.id = "echo_pipe"
        self.name = "Echo Pipe"
        self.valves = self.Valves(
            **{
                "GOAPI_KEY": os.getenv("GOAPI_KEY", "")
            }
        )
        if not self.valves.GOAPI_KEY:
            raise ValueError("Warning: GOAPI_KEY is not set in environment variables.")
        

    async def _submit_task(self, payload: str):
        """
        Asynchronously submits an image generation task to GoAPI.
        Returns the task_id if submission is successful, or None otherwise.
        """
        base_url = "https://api.goapi.ai/api/v1"
        headers = {
            "x-api-key": self.valves.GOAPI_KEY,
            "Content-Type": "application/json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{base_url}/task", json=payload, headers=headers) as response:
                    data = await response.json()
                    if response.status == 200 and data.get("code") == 200:
                        return data["data"]["task_id"]
                    return None
        except Exception as e:
            return None
        
    async def _check_task_status(self, task_id: str) -> Optional[List[str]]:
        """
        Polls the task status using exponential backoff.
        Returns a list of image URLs when the task is completed, or None otherwise.
        """
        headers = {
            "x-api-key": self.valves.GOAPI_KEY,
            "Content-Type": "application/json"
        }
        delay = 5
        max_retries = 10
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(max_retries):
                    async with session.get(f"{self.valves.BASE_URL}/task/{task_id}", headers=headers) as response:
                        data = await response.json()
                        if response.status == 200 and data.get("code") == 200:
                            status = data["data"]["status"]
                            if status == "completed":
                                return data["data"]["output"]
                            elif status == "failed":
                                return None
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 60)
            return None
        except Exception as e:
            return None
    
    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans the data to remove unnecessary fields.
        """
        # Generate download links dynamically based on number of images
        download_options = "\n".join([
            f"            * [Download Image {i+1}]({url})" 
            for i, url in enumerate(data['image_urls'])
        ])

        markdown_response = f"""![Generated Image]({data['image_url']})  {download_options}  
        **Available Actions**: {', '.join(data['actions'])}"""

        return {
            "success": True,
            "markdown": markdown_response
        }


    async def _process_midjourney(self, prompt: str):
        """
        Handles task submission and status polling.
        Returns a dictionary with success status, main image URL, all image URLs, and available actions.
        """
        print(f"Processing prompt: {prompt}")
        
        payload = {
            "model": self.valves.MODEL_ID,
            "task_type": "imagine",
            "input": {
                "prompt": prompt,
                "aspect_ratio": self.valves.DEFAULT_ASPECT_RATIO,
                "process_mode": self.valves.DEFAULT_PROCESS_MODE
            }
        }

        task_id = await self._submit_task(payload)
        
        if not task_id:
            return {"success": False, "error": "Failed to submit task"}
        
        output = await self._check_task_status(task_id)

        if not output:
            return {"success": False, "error": "Task did not complete successfully"}

        cleaned_data = self._clean_data({
            "success": True,
            "image_url": output["image_url"],
            "image_urls": output["image_urls"],
            "actions": output["actions"]
        })
    
        return cleaned_data

    def pipes(self) -> List[dict]:
        """
        Returns information about available pipes. Since this is a simple echo pipe,
        we will return a static description.
        """
        return [{"id": self.id, "name": self.name}]

    async def pipe(self, body: dict) -> Union[str, Generator]:
        """
        Handles the pipe request.
        """
        result = await self._process_midjourney(body["messages"][-1]["content"])
        if result["success"]:
            return result["markdown"]
        else:
            return "Failed to generate image"

