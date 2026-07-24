/**
 * Playwright快照文件解析器
 * 用于解析.yml格式的页面快照文件
 */
import yaml from 'js-yaml'

const PRIVATE_USE_CHAR_RE = /[\uE000-\uF8FF]/g
const cleanSnapshotText = value => String(value || '').replace(PRIVATE_USE_CHAR_RE, '').replace(/\s+/g, ' ').trim()

class PlaywrightSnapshotParser {
  /**
   * 解析YAML内容为元素树
   * @param {string} ymlContent - YAML文件内容
   * @returns {Object} 解析后的元素树
   */
  parse(ymlContent) {
    try {
      const rawData = yaml.load(ymlContent)
      return this.buildElementTree(rawData)
    } catch (error) {
      console.error('YAML解析失败:', error)
      throw new Error('快照文件格式错误')
    }
  }

  /**
   * 构建元素树结构
   * @param {Array|Object} nodes - 原始节点数据
   * @param {Object} parent - 父节点
   * @param {Array} path - 节点路径
   * @returns {Array} 元素树
   */
  buildElementTree(nodes, parent = null, path = []) {
    if (!nodes) return []

    // 如果是单个对象，转为数组
    if (!Array.isArray(nodes)) {
      nodes = [nodes]
    }

    return nodes.map((node, index) => {
      const currentPath = [...path, index]
      const element = this.parseElement(node, parent, currentPath)

      // 递归处理子节点
      if (node && typeof node === 'object') {
        const children = []
        Object.keys(node).forEach(key => {
          if (Array.isArray(node[key])) {
            children.push(...this.buildElementTree(node[key], element, currentPath))
          }
        })
        element.children = children
      }

      return element
    })
  }

  /**
   * 解析单个元素
   * @param {Object|String} node - 节点数据
   * @param {Object} parent - 父元素
   * @param {Array} path - 路径
   * @returns {Object} 元素对象
   */
  parseElement(node, parent, path) {
    const element = {
      id: `element_${path.join('_')}`,
      path: path,
      parent: parent,
      children: [],
      raw: node
    }

    if (typeof node === 'string') {
      // 字符串节点，解析元素信息
      const parsed = this.parseElementString(node)
      Object.assign(element, parsed)
    } else if (node && typeof node === 'object') {
      // 对象节点
      const firstKey = Object.keys(node)[0]
      if (firstKey) {
        const parsed = this.parseElementString(firstKey)
        Object.assign(element, parsed)
      }
    }

    return element
  }

  /**
   * 解析元素字符串
   * 例如: button "汪芜 " [ref=e912] [cursor=pointer]
   * @param {string} str - 元素字符串
   * @returns {Object} 解析结果
   */
  parseElementString(str) {
    if (!str || typeof str !== 'string') {
      return {
        type: 'unknown',
        text: '',
        ref: null,
        attributes: {}
      }
    }

    const result = {
      type: 'generic',
      text: '',
      ref: null,
      attributes: {},
      selectors: []
    }

    // 提取元素类型（第一个单词）
    const typeMatch = str.match(/^(\w+)/)
    if (typeMatch) {
      result.type = typeMatch[1]
    }

    // 提取文本内容（引号中的内容）
    const textMatch = str.match(/"([^"]+)"/)
    if (textMatch) {
      result.text = cleanSnapshotText(textMatch[1])
    }

    // 提取ref
    const refMatch = str.match(/\[ref=([^\]]+)\]/)
    if (refMatch) {
      result.ref = refMatch[1]
    }

    // 提取其他属性
    const attrMatches = str.matchAll(/\[([^\]=]+)(?:=([^\]]+))?\]/g)
    for (const match of attrMatches) {
      const key = match[1]
      const value = match[2] || true
      if (key !== 'ref') {
        result.attributes[key] = value
      }
    }

    // 生成可能的选择器
    result.selectors = this.generateSelectors(result)

    return result
  }

  /**
   * 生成元素选择器
   * @param {Object} element - 元素对象
   * @returns {Array} 选择器列表
   */
  generateSelectors(element) {
    const selectors = []

    // 基于ref的选择器
    if (element.ref) {
      selectors.push({
        type: 'data-ref',
        value: `[data-ref="${element.ref}"]`,
        priority: 1
      })
    }

    // 基于文本的选择器
    if (element.text) {
      const escapedText = element.text.replace(/"/g, '\\"')
      switch (element.type) {
        case 'button':
          selectors.push({
            type: 'text',
            value: `button:has-text("${escapedText}")`,
            priority: 2
          })
          break
        case 'link':
        case 'a':
          selectors.push({
            type: 'text',
            value: `a:has-text("${escapedText}")`,
            priority: 2
          })
          break
        default:
          selectors.push({
            type: 'text',
            value: `text="${escapedText}"`,
            priority: 3
          })
      }
    }

    // 基于类型的选择器
    if (element.type && element.type !== 'generic') {
      selectors.push({
        type: 'tag',
        value: element.type,
        priority: 4
      })
    }

    // 基于role的选择器
    const roleMap = {
      'button': 'button',
      'link': 'link',
      'textbox': 'textbox',
      'checkbox': 'checkbox',
      'radio': 'radio',
      'iframe': 'iframe'
    }
    if (roleMap[element.type]) {
      selectors.push({
        type: 'role',
        value: `role=${roleMap[element.type]}`,
        priority: 2
      })
    }

    return selectors.sort((a, b) => a.priority - b.priority)
  }

  /**
   * 查找元素
   * @param {Array} tree - 元素树
   * @param {Function} predicate - 查找条件
   * @returns {Object|null} 找到的元素
   */
  findElement(tree, predicate) {
    for (const element of tree) {
      if (predicate(element)) {
        return element
      }
      if (element.children && element.children.length > 0) {
        const found = this.findElement(element.children, predicate)
        if (found) return found
      }
    }
    return null
  }

  /**
   * 查找所有匹配的元素
   * @param {Array} tree - 元素树
   * @param {Function} predicate - 查找条件
   * @returns {Array} 所有匹配的元素
   */
  findAllElements(tree, predicate) {
    const results = []
    for (const element of tree) {
      if (predicate(element)) {
        results.push(element)
      }
      if (element.children && element.children.length > 0) {
        results.push(...this.findAllElements(element.children, predicate))
      }
    }
    return results
  }

  /**
   * 提取可交互元素
   * @param {Array} tree - 元素树
   * @returns {Array} 可交互元素列表
   */
  extractInteractiveElements(tree) {
    const interactiveTypes = [
      'button', 'link', 'a', 'textbox', 'input', 'checkbox',
      'radio', 'select', 'tab', 'menuitem', 'iframe', 'frame'
    ]

    return this.findAllElements(tree, element => {
      return interactiveTypes.includes(element.type) ||
        element.attributes.cursor === 'pointer' ||
        element.attributes.role
    })
  }

  /**
   * 获取元素的完整路径选择器
   * @param {Object} element - 元素对象
   * @returns {string} 路径选择器
   */
  getElementPathSelector(element) {
    const path = []
    let current = element

    while (current) {
      if (current.ref) {
        path.unshift(`[data-ref="${current.ref}"]`)
        break
      } else if (current.text && current.type !== 'generic') {
        path.unshift(`${current.type}:has-text("${current.text}")`)
      } else if (current.type && current.type !== 'generic') {
        path.unshift(current.type)
      }
      current = current.parent
    }

    return path.join(' >> ')
  }

  /**
   * 将元素树转换为简化的JSON格式
   * @param {Array} tree - 元素树
   * @returns {Array} 简化的JSON
   */
  toSimpleJSON(tree) {
    return tree.map(element => ({
      id: element.id,
      type: element.type,
      text: element.text,
      ref: element.ref,
      attributes: element.attributes,
      selectors: element.selectors,
      children: element.children ? this.toSimpleJSON(element.children) : []
    }))
  }
}

export default new PlaywrightSnapshotParser()
