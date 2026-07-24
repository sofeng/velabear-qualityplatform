"""文本分析工具

提供基础的文本分析功能
"""
from collections import Counter
import re


def word_count(text):
    """统计词频

    Args:
        text (str): 待分析的文本

    Returns:
        dict: 词频统计结果
    """
    # 简单分词（按空格和标点符号）
    words = re.findall(r'\w+', text.lower())
    counter = Counter(words)

    return {
        'total_words': len(words),
        'unique_words': len(counter),
        'top_10': counter.most_common(10)
    }


def keyword_extract(text, top_n=5):
    """提取关键词（简单实现）

    Args:
        text (str): 待分析的文本
        top_n (int): 返回前N个关键词

    Returns:
        list: 关键词列表
    """
    # 简单实现：过滤停用词后取高频词
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'are', 'was', 'were'}

    words = re.findall(r'\w+', text.lower())
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]

    counter = Counter(filtered_words)
    keywords = [word for word, count in counter.most_common(top_n)]

    return keywords


def analyze(input_data):
    """分析主函数

    Args:
        input_data (dict): 输入数据
            - text: 待分析文本
            - mode: 分析模式 (word_count | keyword_extract)

    Returns:
        dict: 分析结果
    """
    text = input_data.get('text', '')
    mode = input_data.get('mode', 'word_count')

    if not text:
        return {
            'status': 'error',
            'message': '文本不能为空'
        }

    if mode == 'word_count':
        result = word_count(text)
        return {
            'status': 'success',
            'mode': 'word_count',
            'result': result
        }

    elif mode == 'keyword_extract':
        result = keyword_extract(text)
        return {
            'status': 'success',
            'mode': 'keyword_extract',
            'keywords': result
        }

    else:
        return {
            'status': 'error',
            'message': f'未知的分析模式: {mode}'
        }


if __name__ == '__main__':
    # 测试
    test_text = """
    Python is a high-level programming language.
    It is widely used for web development, data analysis, and machine learning.
    Python has a simple and readable syntax.
    """

    print("测试1: 词频统计")
    result1 = analyze({'text': test_text, 'mode': 'word_count'})
    print(result1)

    print("\n测试2: 关键词提取")
    result2 = analyze({'text': test_text, 'mode': 'keyword_extract'})
    print(result2)
