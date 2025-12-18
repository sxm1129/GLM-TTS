# Copyright (c) 2025 Zhipu AI Inc (authors: CogAudio Group Members)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import json
import logging
import base64
import io
import wave
import tempfile
import shutil
import time
import asyncio
from typing import Dict, Optional, Tuple
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import functions from gradio_app.py
from tools.gradio_app import (
    get_models,
    run_inference,
    clear_memory,
    MODEL_CACHE
)
import gradio as gr

# Import optimization modules
from tools.config import TTSConfig
from tools.concurrency_manager import ConcurrencyManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize FastAPI app
app = FastAPI(title="GLM-TTS API", version="1.0.0")

# Global variables
CACHE_FILE = "configs/prompt_cache.json"
TEMP_DIR = "temp_uploads"
PROMPT_CACHE: Dict[str, Dict[str, str]] = {}

# Concurrency manager
concurrency_manager = ConcurrencyManager()

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)


# Pydantic Models
class TTSResponse(BaseModel):
    success: bool
    message: str
    audio_base64: Optional[str] = None
    sample_rate: Optional[int] = None
    generation_time: Optional[float] = None  # Time in seconds
    error: Optional[str] = None


class PromptConfig(BaseModel):
    prompt_audio_path: str
    prompt_text: str


class PromptConfigResponse(BaseModel):
    index: str
    config: PromptConfig


# Helper Functions
def load_prompt_cache() -> Dict[str, Dict[str, str]]:
    """
    Load prompt cache from JSON file. Returns default config if file doesn't exist.
    """
    global PROMPT_CACHE
    
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                PROMPT_CACHE = json.load(f)
            logging.info(f"Loaded prompt cache from {CACHE_FILE}")
        except Exception as e:
            logging.error(f"Failed to load prompt cache: {e}")
            PROMPT_CACHE = get_default_prompt_cache()
    else:
        logging.info(f"Cache file not found, using default config")
        PROMPT_CACHE = get_default_prompt_cache()
        save_prompt_cache()
    
    # Validate all entries
    validated_cache = {}
    for index, config in PROMPT_CACHE.items():
        if validate_prompt_config(config):
            validated_cache[index] = config
        else:
            logging.warning(f"Invalid config for {index}, skipping")
    
    PROMPT_CACHE = validated_cache
    return PROMPT_CACHE


def get_default_prompt_cache() -> Dict[str, Dict[str, str]]:
    """
    Return default prompt cache configuration.
    """
    return {
        "exampleA": {
            "prompt_audio_path": "examples/prompt/jiayan_zh.wav",
            "prompt_text": "他当时还跟线下其他的站姐吵架，然后，打架进局子了。"
        },
        "exampleB": {
            "prompt_audio_path": "examples/prompt/jiayan_zh1.wav",
            "prompt_text": "他当时还跟线下其他的站姐吵架，然后，打架进局子了。"
        }
    }


def save_prompt_cache() -> None:
    """
    Save prompt cache to JSON file.
    """
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(PROMPT_CACHE, f, ensure_ascii=False, indent=4)
        logging.info(f"Saved prompt cache to {CACHE_FILE}")
    except Exception as e:
        logging.error(f"Failed to save prompt cache: {e}")
        raise


def validate_prompt_config(config: Dict[str, str]) -> bool:
    """
    Validate prompt configuration.
    """
    if not isinstance(config, dict):
        return False
    
    if "prompt_audio_path" not in config or "prompt_text" not in config:
        return False
    
    audio_path = config["prompt_audio_path"]
    if not isinstance(audio_path, str) or not audio_path.strip():
        return False
    
    # Check if file exists (handle both absolute and relative paths)
    if not os.path.isabs(audio_path):
        audio_path = os.path.join(os.getcwd(), audio_path)
    
    if not os.path.exists(audio_path):
        logging.warning(f"Audio file not found: {audio_path}")
        return False
    
    if not isinstance(config["prompt_text"], str) or not config["prompt_text"].strip():
        return False
    
    return True


def audio_to_base64(sample_rate: int, audio_data: np.ndarray) -> str:
    """
    Convert audio data to Base64 encoded WAV string.
    """
    # Ensure audio_data is int16
    if audio_data.dtype != np.int16:
        audio_data = audio_data.astype(np.int16)
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    # Get Base64 encoded string
    wav_buffer.seek(0)
    audio_base64 = base64.b64encode(wav_buffer.read()).decode('utf-8')
    return audio_base64


def tts_inference_wrapper(
    prompt_text: str,
    prompt_audio_path: str,
    input_text: str,
    seed: int = 42,
    sample_rate: int = 24000,
    use_cache: bool = True,
    use_phoneme: bool = False,
    sample_method: str = "ras",
    sampling: int = 25,
    beam_size: int = 1
) -> Tuple[int, np.ndarray]:
    """
    Wrapper for run_inference that handles errors properly for API.
    """
    try:
        # Call the original run_inference function
        result = run_inference(
            prompt_text=prompt_text,
            prompt_audio_path=prompt_audio_path,
            input_text=input_text,
            seed=seed,
            sample_rate=sample_rate,
            use_cache=use_cache,
            use_phoneme=use_phoneme,
            sample_method=sample_method,
            sampling=sampling,
            beam_size=beam_size
        )
        return result
    except gr.Error as e:
        # Convert Gradio errors to HTTP exceptions
        logging.error(f"Inference error (Gradio): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Inference error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


# Load prompt cache on startup
@app.on_event("startup")
async def startup_event():
    load_prompt_cache()
    # Initialize concurrency manager
    concurrency_manager.initialize()
    logging.info("Concurrency manager initialized")
    logging.info(f"Configuration: {TTSConfig.get_all_config()}")


# API Endpoints
@app.post("/api/v1/tts", response_model=TTSResponse)
async def generate_tts(
    input_text: str = Form(...),
    index: Optional[str] = Form(None),
    prompt_text: Optional[str] = Form(None),
    prompt_audio: Optional[UploadFile] = File(None),
    seed: int = Form(42),
    sample_rate: int = Form(24000),
    use_cache: bool = Form(True),
    use_phoneme: bool = Form(False),
    sample_method: str = Form("ras"),
    sampling: int = Form(25),
    beam_size: int = Form(1)
):
    """
    Generate TTS audio. Supports two modes:
    1. Index mode: Use pre-cached prompt configuration (provide 'index')
    2. Upload mode: Upload prompt audio and provide prompt_text
    """
    start_time = time.time()  # Record start time
    try:
        # Validate input_text
        if not input_text or not input_text.strip():
            raise HTTPException(status_code=400, detail="input_text is required")
        
        # Validate sample_rate
        if sample_rate not in [24000, 32000]:
            raise HTTPException(status_code=400, detail="sample_rate must be 24000 or 32000")
        
        # Validate sample_method
        if sample_method not in ["ras", "topk"]:
            raise HTTPException(status_code=400, detail="sample_method must be 'ras' or 'topk'")
        
        # Validate sampling and beam_size ranges
        if not (1 <= sampling <= 100):
            raise HTTPException(status_code=400, detail="sampling must be between 1 and 100")
        if not (1 <= beam_size <= 5):
            raise HTTPException(status_code=400, detail="beam_size must be between 1 and 5")
        
        # Determine prompt source
        final_prompt_text = None
        final_prompt_audio_path = None
        temp_file_path = None
        
        try:
            if index:
                # Index mode: use cached configuration
                if index not in PROMPT_CACHE:
                    raise HTTPException(status_code=404, detail=f"Prompt index '{index}' not found")
                
                config = PROMPT_CACHE[index]
                final_prompt_text = config["prompt_text"]
                final_prompt_audio_path = config["prompt_audio_path"]
                
                # Handle relative paths
                if not os.path.isabs(final_prompt_audio_path):
                    final_prompt_audio_path = os.path.join(os.getcwd(), final_prompt_audio_path)
                
                if not os.path.exists(final_prompt_audio_path):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Audio file not found for index '{index}': {final_prompt_audio_path}"
                    )
                
                logging.info(f"Using cached prompt config: index={index}")
            
            elif prompt_audio and prompt_text:
                # Upload mode: use uploaded file
                if not prompt_text.strip():
                    raise HTTPException(status_code=400, detail="prompt_text cannot be empty")
                
                # Save uploaded file to temp directory
                file_ext = os.path.splitext(prompt_audio.filename)[1] or ".wav"
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=file_ext,
                    dir=TEMP_DIR
                )
                temp_file_path = temp_file.name
                
                # Write uploaded content to temp file
                shutil.copyfileobj(prompt_audio.file, temp_file)
                temp_file.close()
                
                final_prompt_text = prompt_text
                final_prompt_audio_path = temp_file_path
                
                logging.info(f"Using uploaded prompt audio: {temp_file_path}")
            
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either 'index' or both 'prompt_audio' and 'prompt_text' must be provided"
                )
            
            # Get text length for concurrency control and timeout
            text_length = len(input_text)
            timeout = TTSConfig.get_timeout(text_length)
            
            # Acquire concurrency permit
            await concurrency_manager.acquire(text_length)
            
            try:
                # Run inference with timeout
                async def run_inference_async():
                    # Run inference in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: tts_inference_wrapper(
                            prompt_text=final_prompt_text,
                            prompt_audio_path=final_prompt_audio_path,
                            input_text=input_text,
                            seed=seed,
                            sample_rate=sample_rate,
                            use_cache=use_cache,
                            use_phoneme=use_phoneme,
                            sample_method=sample_method,
                            sampling=sampling,
                            beam_size=beam_size
                        )
                    )
                
                sample_rate_result, audio_data = await asyncio.wait_for(
                    run_inference_async(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=408,
                    detail=f"Request timeout after {timeout} seconds. Text length: {text_length} characters."
                )
            finally:
                # Release concurrency permit
                await concurrency_manager.release(text_length)
            
            # Convert to Base64
            audio_base64 = audio_to_base64(sample_rate_result, audio_data)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            return TTSResponse(
                success=True,
                message="TTS generation successful",
                audio_base64=audio_base64,
                sample_rate=sample_rate_result,
                generation_time=round(generation_time, 2)  # Round to 2 decimal places
            )
        
        finally:
            # Clean up temp file if created
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logging.warning(f"Failed to delete temp file {temp_file_path}: {e}")
    
    except HTTPException:
        raise
    except Exception as e:
        generation_time = time.time() - start_time
        logging.error(f"Unexpected error in TTS generation: {e}")
        import traceback
        traceback.print_exc()
        return TTSResponse(
            success=False,
            message="TTS generation failed",
            error=str(e),
            generation_time=round(generation_time, 2)
        )


@app.get("/api/v1/prompts")
async def list_prompts():
    """
    List all available prompt configurations.
    """
    return {
        "success": True,
        "prompts": [
            {"index": index, "config": config}
            for index, config in PROMPT_CACHE.items()
        ]
    }


@app.get("/api/v1/prompts/{index}", response_model=PromptConfigResponse)
async def get_prompt(index: str):
    """
    Get prompt configuration for a specific index.
    """
    if index not in PROMPT_CACHE:
        raise HTTPException(status_code=404, detail=f"Prompt index '{index}' not found")
    
    return PromptConfigResponse(
        index=index,
        config=PromptConfig(**PROMPT_CACHE[index])
    )


@app.post("/api/v1/prompts")
async def add_prompt(
    index: str = Form(...),
    prompt_audio_path: str = Form(...),
    prompt_text: str = Form(...)
):
    """
    Add a new prompt configuration.
    """
    if index in PROMPT_CACHE:
        raise HTTPException(status_code=400, detail=f"Prompt index '{index}' already exists")
    
    config = {
        "prompt_audio_path": prompt_audio_path,
        "prompt_text": prompt_text
    }
    
    if not validate_prompt_config(config):
        raise HTTPException(status_code=400, detail="Invalid prompt configuration")
    
    PROMPT_CACHE[index] = config
    save_prompt_cache()
    
    return {
        "success": True,
        "message": f"Prompt '{index}' added successfully",
        "index": index,
        "config": config
    }


@app.put("/api/v1/prompts/{index}")
async def update_prompt(
    index: str,
    prompt_audio_path: str = Form(...),
    prompt_text: str = Form(...)
):
    """
    Update an existing prompt configuration.
    """
    if index not in PROMPT_CACHE:
        raise HTTPException(status_code=404, detail=f"Prompt index '{index}' not found")
    
    config = {
        "prompt_audio_path": prompt_audio_path,
        "prompt_text": prompt_text
    }
    
    if not validate_prompt_config(config):
        raise HTTPException(status_code=400, detail="Invalid prompt configuration")
    
    PROMPT_CACHE[index] = config
    save_prompt_cache()
    
    return {
        "success": True,
        "message": f"Prompt '{index}' updated successfully",
        "index": index,
        "config": config
    }


@app.delete("/api/v1/prompts/{index}")
async def delete_prompt(index: str):
    """
    Delete a prompt configuration.
    """
    if index not in PROMPT_CACHE:
        raise HTTPException(status_code=404, detail=f"Prompt index '{index}' not found")
    
    del PROMPT_CACHE[index]
    save_prompt_cache()
    
    return {
        "success": True,
        "message": f"Prompt '{index}' deleted successfully"
    }


@app.get("/api/v1/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "model_loaded": MODEL_CACHE.get("loaded", False),
        "model_sample_rate": MODEL_CACHE.get("sample_rate"),
        "model_use_phoneme": MODEL_CACHE.get("use_phoneme"),
        "prompt_cache_count": len(PROMPT_CACHE)
    }


@app.get("/api/v1/stats/concurrency")
async def get_concurrency_stats():
    """
    Get concurrency statistics.
    """
    stats = await concurrency_manager.get_stats()
    return {
        "success": True,
        "stats": stats,
        "config": TTSConfig.get_all_config()
    }


@app.post("/api/v1/clear_cache")
async def clear_model_cache():
    """
    Clear model cache to free VRAM.
    """
    try:
        message = clear_memory()
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logging.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8049)

