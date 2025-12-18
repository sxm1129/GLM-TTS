#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源监控脚本
监控 GPU 显存、CPU、内存使用情况
"""

import time
import subprocess
import csv
import sys
import signal
import os
from datetime import datetime


class ResourceMonitor:
    def __init__(self, output_file: str = "resource_monitor.csv", interval: float = 0.5):
        self.output_file = output_file
        self.interval = interval
        self.running = True
        self.csv_file = None
        self.writer = None
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """处理退出信号"""
        self.running = False
        print("\n收到退出信号，正在停止监控...")
    
    def get_gpu_memory(self):
        """获取 GPU 显存使用情况"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                line = result.stdout.strip().split('\n')[0]
                used, total = map(int, line.split(', '))
                return {
                    'gpu_memory_used_mb': used,
                    'gpu_memory_total_mb': total,
                    'gpu_memory_usage_percent': round(used / total * 100, 2) if total > 0 else 0
                }
        except Exception as e:
            pass
        return {
            'gpu_memory_used_mb': 0,
            'gpu_memory_total_mb': 0,
            'gpu_memory_usage_percent': 0
        }
    
    def get_cpu_memory(self):
        """获取 CPU 和内存使用情况"""
        try:
            # 获取 CPU 使用率
            result = subprocess.run(
                ['top', '-bn1'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                cpu_line = [l for l in lines if '%Cpu(s)' in l]
                if cpu_line:
                    cpu_parts = cpu_line[0].split(',')
                    cpu_idle = float(cpu_parts[3].split('%')[0].strip())
                    cpu_usage = round(100 - cpu_idle, 2)
                else:
                    cpu_usage = 0
            else:
                cpu_usage = 0
            
            # 获取内存使用
            result = subprocess.run(
                ['free', '-m'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                mem_line = lines[1].split()
                mem_total = int(mem_line[1])
                mem_used = int(mem_line[2])
                mem_usage_percent = round(mem_used / mem_total * 100, 2) if mem_total > 0 else 0
            else:
                mem_total = 0
                mem_used = 0
                mem_usage_percent = 0
            
            return {
                'cpu_usage_percent': cpu_usage,
                'memory_total_mb': mem_total,
                'memory_used_mb': mem_used,
                'memory_usage_percent': mem_usage_percent
            }
        except Exception as e:
            return {
                'cpu_usage_percent': 0,
                'memory_total_mb': 0,
                'memory_used_mb': 0,
                'memory_usage_percent': 0
            }
    
    def monitor(self):
        """开始监控"""
        print(f"开始监控资源使用情况...")
        print(f"输出文件: {self.output_file}")
        print(f"采样间隔: {self.interval} 秒")
        print("按 Ctrl+C 停止监控\n")
        
        # 打开 CSV 文件
        self.csv_file = open(self.output_file, 'w', newline='', encoding='utf-8')
        fieldnames = [
            'timestamp',
            'gpu_memory_used_mb',
            'gpu_memory_total_mb',
            'gpu_memory_usage_percent',
            'cpu_usage_percent',
            'memory_total_mb',
            'memory_used_mb',
            'memory_usage_percent'
        ]
        self.writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.writer.writeheader()
        
        try:
            while self.running:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                
                # 获取资源使用情况
                gpu_info = self.get_gpu_memory()
                cpu_info = self.get_cpu_memory()
                
                # 写入 CSV
                row = {
                    'timestamp': timestamp,
                    **gpu_info,
                    **cpu_info
                }
                self.writer.writerow(row)
                self.csv_file.flush()
                
                # 打印当前状态
                print(f"[{timestamp}] GPU: {gpu_info['gpu_memory_used_mb']}/{gpu_info['gpu_memory_total_mb']}MB "
                      f"({gpu_info['gpu_memory_usage_percent']}%) | "
                      f"CPU: {cpu_info['cpu_usage_percent']}% | "
                      f"Memory: {cpu_info['memory_used_mb']}/{cpu_info['memory_total_mb']}MB "
                      f"({cpu_info['memory_usage_percent']}%)")
                
                time.sleep(self.interval)
        except KeyboardInterrupt:
            pass
        finally:
            if self.csv_file:
                self.csv_file.close()
            print(f"\n监控已停止，数据已保存到: {self.output_file}")


def main():
    """主函数"""
    output_file = sys.argv[1] if len(sys.argv) > 1 else "resource_monitor.csv"
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    
    monitor = ResourceMonitor(output_file=output_file, interval=interval)
    monitor.monitor()


if __name__ == "__main__":
    main()


