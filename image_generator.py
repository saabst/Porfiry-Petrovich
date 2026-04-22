import aiohttp
import asyncio
import os
from typing import Optional

class ImageGenerator:
    def __init__(self, provider: str = "pollinations", width: int = 1024, height: int = 1024):
        self.provider = provider
        self.width = width
        self.height = height
    
    async def generate(self, prompt: str, output_path: str) -> Optional[str]:
        if self.provider != "pollinations":
            return None
        short_prompt = prompt[:200].replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{short_prompt}?width={self.width}&height={self.height}&nologo=true"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(await resp.read())
                        return output_path
                    else:
                        print(f"Image generation failed: {resp.status}")
                        return None
        except Exception as e:
            print(f"Image error: {e}")
            return None