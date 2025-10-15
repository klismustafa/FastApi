from typing import Optional
import httpx
from fastapi import HTTPException
import os
from dotenv import load_dotenv
from pathlib import Path

# Get the directory containing this file
BASE_DIR = Path(__file__).resolve().parent

# Load .env file explicitly from the correct path
load_dotenv(BASE_DIR / '.env')

# Try to get the secret
UPLOADTHING_SECRET = os.getenv("UPLOADTHING_SECRET")
if not UPLOADTHING_SECRET:
    print("Debug: Looking for .env in:", BASE_DIR)
    raise ValueError("UPLOADTHING_SECRET environment variable is not set")

class UploadThingClient:
    def __init__(self):
        self.api_key = UPLOADTHING_SECRET
        self.base_url = "https://uploadthing.com/api"
        
    async def upload_file(self, file_data: bytes, file_name: str, content_type: str) -> Optional[str]:
        headers = {
            "X-Upload-Key": self.api_key,
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get presigned URL
                presign_response = await client.post(
                    f"{self.base_url}/uploadFiles",
                    headers=headers,
                    json={
                        "files": [{
                            "name": file_name,
                            "type": content_type,
                        }]
                    }
                )
                
                if presign_response.status_code != 200:
                    error_text = await presign_response.text()
                    raise HTTPException(
                        status_code=presign_response.status_code,
                        detail=f"Failed to get upload URL: {error_text}"
                    )
                
                # Parse the JSON response without using await
                presigned_data = None
                try:
                    presigned_data = presign_response.json()
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Invalid JSON response from upload service: {str(e)}"
                    )
                
                if not isinstance(presigned_data, dict) or 'data' not in presigned_data or not isinstance(presigned_data['data'], list):
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid response format from upload service"
                    )
                
                if not presigned_data['data'] or 'url' not in presigned_data['data'][0]:
                    raise HTTPException(
                        status_code=500,
                        detail="Missing upload URL in response"
                    )
                
                # Upload file to the presigned URL
                upload_url = presigned_data['data'][0]['url']
                upload_headers = {"Content-Type": content_type}
                
                upload_response = await client.put(
                    upload_url,
                    content=file_data,
                    headers=upload_headers
                )
                
                if upload_response.status_code != 200:
                    error_text = await upload_response.text()
                    raise HTTPException(
                        status_code=upload_response.status_code,
                        detail=f"Failed to upload file: {error_text}"
                    )
                
                # Get the file URL from the presigned data
                if 'fileUrl' not in presigned_data['data'][0]:
                    raise HTTPException(
                        status_code=500,
                        detail="Missing file URL in response"
                    )
                
                return presigned_data['data'][0]['fileUrl']
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Upload service connection error: {str(e)}"
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}"
            )

uploadthing_client = UploadThingClient()