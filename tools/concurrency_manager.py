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
并发控制管理模块
基于文本长度管理不同的并发限制
"""
import asyncio
import time
from typing import Dict, Optional
from tools.config import TTSConfig


class ConcurrencyManager:
    """并发控制管理器"""
    
    def __init__(self):
        """初始化并发管理器"""
        self.short_text_semaphore: Optional[asyncio.Semaphore] = None
        self.long_text_semaphore: Optional[asyncio.Semaphore] = None
        self.stats: Dict[str, int] = {
            'short_text_active': 0,
            'long_text_active': 0,
            'short_text_total': 0,
            'long_text_total': 0
        }
        self._lock = asyncio.Lock()
    
    def initialize(self):
        """初始化信号量"""
        self.short_text_semaphore = asyncio.Semaphore(TTSConfig.SHORT_TEXT_CONCURRENCY)
        self.long_text_semaphore = asyncio.Semaphore(TTSConfig.LONG_TEXT_CONCURRENCY)
    
    def get_semaphore(self, text_length: int) -> asyncio.Semaphore:
        """
        根据文本长度获取对应的信号量
        
        Args:
            text_length: 文本长度（字符数）
            
        Returns:
            对应的信号量对象
        """
        if text_length <= TTSConfig.TEXT_LENGTH_THRESHOLD:
            return self.short_text_semaphore
        else:
            return self.long_text_semaphore
    
    async def acquire(self, text_length: int):
        """
        获取并发许可
        
        Args:
            text_length: 文本长度（字符数）
        """
        semaphore = self.get_semaphore(text_length)
        await semaphore.acquire()
        
        async with self._lock:
            if text_length <= TTSConfig.TEXT_LENGTH_THRESHOLD:
                self.stats['short_text_active'] += 1
                self.stats['short_text_total'] += 1
            else:
                self.stats['long_text_active'] += 1
                self.stats['long_text_total'] += 1
    
    async def release(self, text_length: int):
        """
        释放并发许可
        
        Args:
            text_length: 文本长度（字符数）
        """
        semaphore = self.get_semaphore(text_length)
        semaphore.release()
        
        # 更新统计信息（需要锁保护）
        async with self._lock:
            if text_length <= TTSConfig.TEXT_LENGTH_THRESHOLD:
                self.stats['short_text_active'] = max(0, self.stats['short_text_active'] - 1)
            else:
                self.stats['long_text_active'] = max(0, self.stats['long_text_active'] - 1)
    
    async def get_stats(self) -> Dict:
        """
        获取并发统计信息
        
        Returns:
            统计信息字典
        """
        async with self._lock:
            return {
                'short_text': {
                    'active': self.stats['short_text_active'],
                    'total': self.stats['short_text_total'],
                    'limit': TTSConfig.SHORT_TEXT_CONCURRENCY,
                    'available': TTSConfig.SHORT_TEXT_CONCURRENCY - self.stats['short_text_active']
                },
                'long_text': {
                    'active': self.stats['long_text_active'],
                    'total': self.stats['long_text_total'],
                    'limit': TTSConfig.LONG_TEXT_CONCURRENCY,
                    'available': TTSConfig.LONG_TEXT_CONCURRENCY - self.stats['long_text_active']
                }
            }

