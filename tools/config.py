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
"""
TTS API 配置管理模块
支持环境变量覆盖默认配置
"""
import os
from typing import Dict


class TTSConfig:
    """TTS API 配置类"""
    
    # 并发限制配置
    SHORT_TEXT_CONCURRENCY: int = int(os.getenv('SHORT_TEXT_CONCURRENCY', '10'))
    LONG_TEXT_CONCURRENCY: int = int(os.getenv('LONG_TEXT_CONCURRENCY', '3'))
    TEXT_LENGTH_THRESHOLD: int = int(os.getenv('TEXT_LENGTH_THRESHOLD', '200'))  # 区分长短文本的阈值
    
    # 超时配置（秒）
    SHORT_TEXT_TIMEOUT: int = int(os.getenv('SHORT_TEXT_TIMEOUT', '60'))
    MEDIUM_TEXT_TIMEOUT: int = int(os.getenv('MEDIUM_TEXT_TIMEOUT', '300'))
    LONG_TEXT_TIMEOUT: int = int(os.getenv('LONG_TEXT_TIMEOUT', '600'))
    
    # 队列配置
    QUEUE_MAX_SIZE: int = int(os.getenv('QUEUE_MAX_SIZE', '100'))
    WORKER_COUNT: int = int(os.getenv('WORKER_COUNT', '5'))
    ENABLE_QUEUE_MODE: bool = os.getenv('ENABLE_QUEUE_MODE', 'false').lower() == 'true'
    
    # 多进程配置
    WORKER_PROCESSES: int = int(os.getenv('WORKERS', '1'))  # 默认单进程
    
    @classmethod
    def get_timeout(cls, text_length: int) -> int:
        """
        根据文本长度返回超时时间
        
        Args:
            text_length: 文本长度（字符数）
            
        Returns:
            超时时间（秒）
        """
        if text_length <= 50:
            return cls.SHORT_TEXT_TIMEOUT
        elif text_length <= cls.TEXT_LENGTH_THRESHOLD:
            return cls.MEDIUM_TEXT_TIMEOUT
        else:
            return cls.LONG_TEXT_TIMEOUT
    
    @classmethod
    def get_semaphore_type(cls, text_length: int) -> str:
        """
        根据文本长度返回信号量类型
        
        Args:
            text_length: 文本长度（字符数）
            
        Returns:
            'short' 或 'long'
        """
        if text_length <= cls.TEXT_LENGTH_THRESHOLD:
            return 'short'
        else:
            return 'long'
    
    @classmethod
    def get_all_config(cls) -> Dict:
        """
        获取所有配置信息
        
        Returns:
            配置字典
        """
        return {
            'concurrency': {
                'short_text': cls.SHORT_TEXT_CONCURRENCY,
                'long_text': cls.LONG_TEXT_CONCURRENCY,
                'threshold': cls.TEXT_LENGTH_THRESHOLD
            },
            'timeout': {
                'short_text': cls.SHORT_TEXT_TIMEOUT,
                'medium_text': cls.MEDIUM_TEXT_TIMEOUT,
                'long_text': cls.LONG_TEXT_TIMEOUT
            },
            'queue': {
                'max_size': cls.QUEUE_MAX_SIZE,
                'worker_count': cls.WORKER_COUNT,
                'enabled': cls.ENABLE_QUEUE_MODE
            },
            'workers': cls.WORKER_PROCESSES
        }

