# @plugin:name: 数据处理工具
# @plugin:description: 提供常用的数据处理功能，包括数据清洗、转换、验证等
# @plugin:kind: skill
# @plugin:entrypoint: main
# @plugin:tags: 数据处理, 工具, 示例

"""数据处理工具插件

这是一个示例插件，演示如何创建和上传自定义技能到AI工坊。
"""


def clean_data(data):
    """清洗数据：去除空值和重复项"""
    if isinstance(data, list):
        # 去除None和空字符串
        cleaned = [item for item in data if item is not None and item != '']
        # 去重
        cleaned = list(set(cleaned))
        return cleaned
    return data


def validate_email(email):
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def main(input_data):
    """技能主函数

    Args:
        input_data (dict): 输入数据，格式：
            {
                'action': 'clean' | 'validate_email',
                'data': 待处理的数据
            }

    Returns:
        dict: 处理结果
    """
    action = input_data.get('action', 'clean')
    data = input_data.get('data')

    if action == 'clean':
        result = clean_data(data)
        return {
            'status': 'success',
            'action': 'clean',
            'result': result,
            'count': len(result) if isinstance(result, list) else 1
        }

    elif action == 'validate_email':
        is_valid = validate_email(data)
        return {
            'status': 'success',
            'action': 'validate_email',
            'email': data,
            'is_valid': is_valid
        }

    else:
        return {
            'status': 'error',
            'message': f'未知的操作: {action}'
        }


if __name__ == '__main__':
    # 测试代码
    print("测试1: 清洗数据")
    test1 = main({
        'action': 'clean',
        'data': ['apple', 'banana', None, 'apple', '', 'cherry']
    })
    print(test1)

    print("\n测试2: 验证邮箱")
    test2 = main({
        'action': 'validate_email',
        'data': 'test@example.com'
    })
    print(test2)
