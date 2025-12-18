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
import gradio as gr
import torch
import numpy as np
import logging
import os
from glmtts_inference import (
    load_models,
    generate_long,
    local_llm_forward,
    DEVICE
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global cache to store loaded models
MODEL_CACHE = {
    "loaded": False,
    "sample_rate": None,
    "use_phoneme": None,
    "components": None
}

def get_models(use_phoneme=False, sample_rate=24000):
    """
    Lazy loader for models. Reloads if sample_rate or use_phoneme changes.
    """
    # Check if loaded and if sample_rate and use_phoneme match
    if (MODEL_CACHE["loaded"] and 
        MODEL_CACHE["sample_rate"] == sample_rate and 
        MODEL_CACHE["use_phoneme"] == use_phoneme):
        return MODEL_CACHE["components"]
    
    logging.info(f"Loading models with sample_rate={sample_rate}...")
    
    # Clean up old models if they exist to save VRAM before loading new ones
    if MODEL_CACHE["components"]:
        del MODEL_CACHE["components"]
        import gc
        gc.collect()
        torch.cuda.empty_cache()

    # Load models using the function from glmtts_inference.py
    frontend, text_frontend, speech_tokenizer, llm, flow = load_models(
        use_phoneme=use_phoneme, 
        sample_rate=sample_rate
    )
    
    MODEL_CACHE["components"] = (frontend, text_frontend, speech_tokenizer, llm, flow)
    MODEL_CACHE["sample_rate"] = sample_rate
    MODEL_CACHE["use_phoneme"] = use_phoneme
    MODEL_CACHE["loaded"] = True
    logging.info(f"Models loaded successfully. (sample_rate={sample_rate}, use_phoneme={use_phoneme})")
    return MODEL_CACHE["components"]

def custom_local_llm_forward(llm, prompt_text_token, tts_text_token, prompt_speech_token, 
                              beam_size=1, sampling=25, sample_method="ras"):
    """
    Custom wrapper for local_llm_forward with all parameters.
    """
    return local_llm_forward(
        llm=llm,
        prompt_text_token=prompt_text_token,
        tts_text_token=tts_text_token,
        prompt_speech_token=prompt_speech_token,
        beam_size=beam_size,
        sampling=sampling,
        sample_method=sample_method
    )

def run_inference(prompt_text, prompt_audio_path, input_text, seed, sample_rate, 
                  use_cache, use_phoneme, sample_method, sampling, beam_size):
    """
    Main inference handler for Gradio with all advanced features.
    """
    if not input_text:
        raise gr.Error("Please provide text to synthesize.")
    if not prompt_audio_path:
        raise gr.Error("Please upload a prompt audio file.")
    if not prompt_text:
        gr.Warning("Prompt text is empty. Results might be suboptimal.")

    try:
        # 1. Load Models (Pass sample_rate and use_phoneme)
        frontend, text_frontend, _, llm, flow = get_models(use_phoneme=use_phoneme, sample_rate=sample_rate)

        # 2. Pre-process Prompt (Text Normalization)
        norm_prompt_text = text_frontend.text_normalize(prompt_text) + ' '
        norm_input_text = text_frontend.text_normalize(input_text)
        
        logging.info(f"Normalized Prompt: {norm_prompt_text}")
        logging.info(f"Normalized Input: {norm_input_text}")

        # 3. Extract Features & Tokens
        # Extract prompt text tokens
        prompt_text_token = frontend._extract_text_token(norm_prompt_text)
        
        # Extract prompt speech tokens (expects a list of paths)
        prompt_speech_token = frontend._extract_speech_token([prompt_audio_path])
        
        # Extract speech features and speaker embedding for Flow
        # Update: Pass sample_rate to feature extraction
        speech_feat = frontend._extract_speech_feat(prompt_audio_path, sample_rate=sample_rate)
        embedding = frontend._extract_spk_embedding(prompt_audio_path)

        # 4. Prepare Cache Dictionary
        cache_speech_token_list = [prompt_speech_token.squeeze().tolist()]
        flow_prompt_token = torch.tensor(cache_speech_token_list, dtype=torch.int32).to(DEVICE)
        
        cache = {
            'cache_text': [norm_prompt_text],
            'cache_text_token': [prompt_text_token],
            'cache_speech_token': cache_speech_token_list,
            'use_cache': use_cache
        }

        # 5. Run Generation with custom local_llm_forward
        # Ensure parameters are correct types
        beam_size = int(beam_size)
        sampling = int(sampling)
        
        # Create a partial function with beam_size and sampling parameters
        from functools import partial
        custom_llm_forward = partial(
            custom_local_llm_forward,
            beam_size=beam_size,
            sampling=sampling,
            sample_method=sample_method
        )
        
        tts_speech, _, _, _ = generate_long(
            frontend=frontend,
            text_frontend=text_frontend,
            llm=llm,
            flow=flow,
            text_info=['', norm_input_text],
            cache=cache,
            embedding=embedding,
            flow_prompt_token=flow_prompt_token,
            speech_feat=speech_feat,
            sample_method=sample_method,
            seed=seed,
            device=DEVICE,
            use_phoneme=use_phoneme,
            local_llm_forward=custom_llm_forward
        )

        # 6. Post-process Audio
        # Convert torch tensor to int16 numpy array for Gradio
        audio_data = tts_speech.squeeze().cpu().numpy()
        # Clamp to ensure no clipping before conversion
        audio_data = np.clip(audio_data, -1.0, 1.0)
        audio_int16 = (audio_data * 32767.0).astype(np.int16)

        # Update: Return dynamic sample_rate instead of hardcoded 32000
        return (sample_rate, audio_int16)

    except Exception as e:
        logging.error(f"Inference failed: {e}")
        import traceback
        traceback.print_exc()
        raise gr.Error(f"Inference failed: {str(e)}")

def clear_memory():
    """
    Clears VRAM and resets the model cache.
    """
    global MODEL_CACHE
    if MODEL_CACHE["components"]:
        del MODEL_CACHE["components"]
    MODEL_CACHE["components"] = None
    MODEL_CACHE["loaded"] = False
    MODEL_CACHE["sample_rate"] = None
    MODEL_CACHE["use_phoneme"] = None
    
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    return "Memory cleared. Models will reload on next inference."

# --- Gradio UI Layout ---

with gr.Blocks(title="GLMTTS Inference") as app:
    gr.Markdown("# 🎵 GLMTTS Open Source Demo")
    gr.Markdown("Zero-shot text-to-speech generation using GLMTTS models.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Zero-Shot Prompt Settings")
            
            prompt_audio = gr.Audio(
                label="Upload Prompt Audio (Reference Voice)",
                type="filepath",
                value=os.path.join("examples", "prompt", "jiayan_zh.wav")
            )
            
            prompt_text = gr.Textbox(
                label="Prompt Text",
                placeholder="Enter the exact text spoken in the prompt audio...",
                lines=2,
                info="Accurate prompt text improves speaker similarity.",
                value="他当时还跟线下其他的站姐吵架，然后，打架进局子了。"
            )

            gr.Markdown("### 2. Input Settings")
            input_text = gr.Textbox(
                label="Text to Synthesize",
                value="我最爱吃人参果，你喜欢吃吗？", 
                lines=5
            )
            
            with gr.Accordion("Advanced Settings", open=True):
                # Basic Settings
                sample_rate = gr.Radio(
                    choices=[24000, 32000], 
                    value=24000, 
                    label="Sample Rate (Hz)",
                    info="Choose 32000 for higher quality if model supports it."
                )
                seed = gr.Number(label="Seed", value=42, precision=0, info="Random seed for reproducibility")
                use_cache = gr.Checkbox(label="Use KV Cache", value=True, info="Faster generation for long text.")
                
                # Phoneme Control
                use_phoneme = gr.Checkbox(
                    label="启用音素控制 (Phoneme Control)", 
                    value=False, 
                    info="解决多音字和生僻字发音问题，提高发音准确性"
                )
                
                # Sampling Settings
                sample_method = gr.Radio(
                    choices=["ras", "topk"], 
                    value="ras", 
                    label="采样方法 (Sampling Method)",
                    info="ras: Repetition-Aware Sampling (推荐) | topk: Top-K采样"
                )
                sampling = gr.Slider(
                    minimum=1, 
                    maximum=100, 
                    value=25, 
                    step=1, 
                    label="采样参数 (Sampling/Top-K)",
                    info="控制采样时的候选token数量，值越大多样性越高但可能降低质量"
                )
                beam_size = gr.Slider(
                    minimum=1, 
                    maximum=5, 
                    value=1, 
                    step=1, 
                    label="Beam Size (束搜索)",
                    info="值>1使用束搜索提升质量，但会增加计算时间和显存占用"
                )

            generate_btn = gr.Button("🚀 Generate Audio", variant="primary", size="lg")
            clear_btn = gr.Button("🧹 Clear VRAM", variant="secondary")

        with gr.Column(scale=1):
            gr.Markdown("### 3. Output")
            output_audio = gr.Audio(label="Synthesized Result")
            status_msg = gr.Textbox(label="System Status", interactive=False)

    # Event Bindings
    generate_btn.click(
        fn=run_inference,
        inputs=[
            prompt_text, 
            prompt_audio, 
            input_text, 
            seed, 
            sample_rate, 
            use_cache,
            use_phoneme,
            sample_method,
            sampling,
            beam_size
        ],
        outputs=[output_audio]
    )

    clear_btn.click(
        fn=clear_memory,
        inputs=None,
        outputs=[status_msg]
    )

if __name__ == "__main__":
    app.queue().launch(
        server_name="0.0.0.0", 
        server_port=8048, 
        theme=gr.themes.Soft(),
        share=False
    )