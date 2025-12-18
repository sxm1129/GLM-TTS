#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 Phoneme 功能的实际转换效果
查看启用 Phoneme 时文本是如何被转换的
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cosyvoice.cli.frontend import TextFrontEnd

# 测试文本片段（包含多音字）
TEST_SENTENCES = [
    "今天早上，音乐学院的学生在操场上排队走行。",
    "队伍前面走在最长的那一行，是新来的辅导员长老师。",
    "他姓重，却一点也不严肃，大家都叫他\"老乐\"，因为他既会弹钢琴，又会拉大提琴，还会自己编曲。",
    "想学好音乐，不只要把乐谱看懂，节奏数对，还要把每一个音调听准。",
    "这样别人才听得舒服，心里才觉得乐。",
    "排练开始前，老师特意调整了一下音响的音量，又把每个人的站位重新安排了一遍。",
    "要想把事情办得更好，就要学会分别轻重缓急。",
    "有时候看起来很重要的事，其实并不难；反而是那些看上去很重复的小事，最考验人。",
    "天突然空下起小雨，操场上渐渐显出一点点雨点的水花。",
    "只要把话筒的音量再调一调就行。",
]

def test_phoneme_conversion():
    """测试 Phoneme 转换"""
    print("="*80)
    print("Phoneme 功能转换调试")
    print("="*80 + "\n")
    
    # 创建启用和禁用 Phoneme 的前端
    frontend_enabled = TextFrontEnd(use_phoneme=True)
    frontend_disabled = TextFrontEnd(use_phoneme=False)
    
    print("测试文本转换对比：\n")
    
    for i, text in enumerate(TEST_SENTENCES, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}: {text}")
        print(f"{'='*80}")
        
        # 文本归一化（禁用 Phoneme）
        normalized_disabled = frontend_disabled.text_normalize(text)
        print(f"\n[禁用 Phoneme] 归一化后: {normalized_disabled}")
        
        # 文本归一化（启用 Phoneme）
        normalized_enabled = frontend_enabled.text_normalize(text)
        print(f"[启用 Phoneme] 归一化后: {normalized_enabled}")
        
        # G2P 转换（启用 Phoneme）
        if frontend_enabled.use_phoneme:
            g2p_result = frontend_enabled.g2p_infer(normalized_enabled)
            print(f"[启用 Phoneme] G2P 转换后: {g2p_result}")
            
            # 对比原始文本和转换结果
            if g2p_result != normalized_enabled:
                print(f"\n📝 转换差异:")
                print(f"  原始: {normalized_enabled}")
                print(f"  转换: {g2p_result}")
                
                # 找出被替换的字符
                import re
                phoneme_pattern = r'<\|[^|]+\|>'
                phonemes = re.findall(phoneme_pattern, g2p_result)
                if phonemes:
                    print(f"  音素标记: {phonemes}")
        
        print()

def analyze_replace_dict():
    """分析替换字典"""
    print("\n" + "="*80)
    print("G2P 替换字典分析")
    print("="*80 + "\n")
    
    replace_dict_path = "configs/G2P_replace_dict.jsonl"
    if os.path.exists(replace_dict_path):
        with open(replace_dict_path, 'r', encoding='utf-8') as f:
            replace_dict = {}
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                replace_dict.update(d)
        
        print(f"替换字典条目数: {len(replace_dict)}")
        print("\n替换规则:")
        for key, value in replace_dict.items():
            print(f"  '{key}' → {value}")
    else:
        print(f"❌ 替换字典文件不存在: {replace_dict_path}")

def analyze_able_list():
    """分析可替换字符列表"""
    print("\n" + "="*80)
    print("G2P 可替换字符列表分析")
    print("="*80 + "\n")
    
    able_path = "configs/G2P_able_1word.json"
    if os.path.exists(able_path):
        import json
        with open(able_path, 'r', encoding='utf-8') as f:
            able_list = json.load(f)
        
        print(f"可替换字符总数: {len(able_list)}")
        
        # 检查测试文本中的多音字是否在列表中
        test_chars = set()
        for text in TEST_SENTENCES:
            for char in text:
                if '\u4e00' <= char <= '\u9fff':  # 中文字符
                    test_chars.add(char)
        
        print(f"\n测试文本中的中文字符数: {len(test_chars)}")
        
        # 找出测试文本中的多音字
        multitone_chars = ['行', '长', '重', '乐', '量', '别', '空', '调', '数', '显']
        in_able_list = []
        not_in_able_list = []
        
        for char in multitone_chars:
            if char in able_list:
                in_able_list.append(char)
            else:
                not_in_able_list.append(char)
        
        print(f"\n多音字在可替换列表中:")
        for char in in_able_list:
            print(f"  ✅ '{char}'")
        
        if not_in_able_list:
            print(f"\n多音字不在可替换列表中:")
            for char in not_in_able_list:
                print(f"  ❌ '{char}'")
    else:
        print(f"❌ 可替换字符列表文件不存在: {able_path}")

if __name__ == "__main__":
    import json
    test_phoneme_conversion()
    analyze_replace_dict()
    analyze_able_list()

