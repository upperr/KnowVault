/**
 * Markdown 渲染工具 - 将 Markdown 文本转换为 HTML
 * 支持：标题、加粗、列表、引用、代码块、行内代码、表格
 */

// 转义 HTML，但保留占位符 %%...%%
export function escapeHtml(text) {
  if (!text) return ''
  
  // 转义 < > & " '，但保留 %%...%% 占位符
  return text
    .replace(/%%[A-Z]+[0-9]+%%/g, (match) => `%%ESCAPED${match}%%`)  // 临时保护占位符
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/%%ESCAPED(%%[A-Z]+[0-9]+%%)%%/g, '$1')  // 恢复占位符
}

// 渲染表格 HTML
function renderTableHTML(rows, escapeFn) {
  if (rows.length === 0) return ''
  
  let html = '<table><thead><tr>'
  
  // 第一行作为表头
  rows[0].forEach(cell => {
    // 先保护单元格内的 HTML 标签
    const cellHtmlTags = []
    let processedCell = cell.replace(/<([a-z][a-z0-9]*(?:\s+[^>]*)?)>([\s\S]*?)<\/\1>|<([a-z][a-z0-9]*(?:\s+[^>]*)?)\s*\/?>/gi, (match) => {
      cellHtmlTags.push(match)
      return `%%CELLTAG${cellHtmlTags.length - 1}%%`
    })
    // 转义
    processedCell = escapeFn(processedCell)
    // 恢复 HTML 标签
    cellHtmlTags.forEach((tag, i) => {
      processedCell = processedCell.replace(`%%CELLTAG${i}%%`, tag)
    })
    html += '<th>' + processedCell + '</th>'
  })
  
  html += '</tr></thead><tbody>'
  
  // 其余行作为数据行
  for (let i = 1; i < rows.length; i++) {
    html += '<tr>'
    rows[i].forEach(cell => {
      // 先保护单元格内的 HTML 标签
      const cellHtmlTags = []
      let processedCell = cell.replace(/<([a-z][a-z0-9]*(?:\s+[^>]*)?)>([\s\S]*?)<\/\1>|<([a-z][a-z0-9]*(?:\s+[^>]*)?)\s*\/?>/gi, (match) => {
        cellHtmlTags.push(match)
        return `%%CELLTAG${cellHtmlTags.length - 1}%%`
      })
      // 转义
      processedCell = escapeFn(processedCell)
      // 恢复 HTML 标签
      cellHtmlTags.forEach((tag, i) => {
        processedCell = processedCell.replace(`%%CELLTAG${i}%%`, tag)
      })
      html += '<td>' + processedCell + '</td>'
    })
    html += '</tr>'
  }
  
  html += '</tbody></table>'
  return html
}

// 渲染表格（从 markdown 文本中提取）
function renderTable(html, htmlTags) {
  const lines = html.split('<br>')
  let inTable = false
  let tableHtml = ''
  let rows = []
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    
    // 检测表格行 (包含 | 的行)
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) {
        inTable = true
        rows = []
      }
      
      // 跳过分隔行 (|---|---|)
      if (line.match(/^\|[\s\-:|]+\|$/)) {
        continue
      }
      
      // 解析单元格
      const cells = line.split('|').slice(1, -1).map(c => c.trim())
      rows.push(cells)
    } else {
      // 输出表格并重置
      if (inTable && rows.length > 0) {
        tableHtml += renderTableHTML(rows, escapeHtml)
        inTable = false
        rows = []
      }
      tableHtml += lines[i] + '<br>'
    }
  }
  
  // 处理末尾的表格
  if (inTable && rows.length > 0) {
    tableHtml += renderTableHTML(rows, escapeHtml)
  }
  
  return tableHtml
}

/**
 * 将 Markdown 文本转换为 HTML
 * @param {string} text - Markdown 文本
 * @returns {string} - HTML 字符串
 */
export function renderMarkdown(text) {
  if (!text) return ''
  
  let html = text
  
  // 1. 保护代码块（先提取，最后恢复）
  const codeBlocks = []
  html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
    codeBlocks.push('<pre><code>' + escapeHtml(code.trim()) + '</code></pre>')
    return `%%CODEBLOCK${codeBlocks.length - 1}%%`
  })
  
  // 2. 保护行内代码
  const inlineCodes = []
  html = html.replace(/`([^`]+)`/g, (match, code) => {
    inlineCodes.push('<code>' + escapeHtml(code) + '</code>')
    return `%%INLINECODE${inlineCodes.length - 1}%%`
  })
  
  // 3. 保护已有的 HTML 标签（LLM 可能直接返回 HTML 标签）
  // 支持：strong, b, em, i, br, a, ul, ol, li, span, div, p 等
  const htmlTags = []
  // 使用 [\s\S]*? 支持跨行匹配
  html = html.replace(/<([a-z][a-z0-9]*(?:\s+[^>]*)?)>([\s\S]*?)<\/\1>|<([a-z][a-z0-9]*(?:\s+[^>]*)?)\s*\/?>/gi, (match) => {
    htmlTags.push(match)
    return `%%HTMLTAG${htmlTags.length - 1}%%`
  })
  
  // 4. 先转义所有 HTML（在 Markdown 处理之前）
  html = escapeHtml(html)
  
  // 4. 标题（从大到小处理，避免匹配冲突）
  html = html.replace(/^###### (.*$)/gm, '<h6>$1</h6>')
  html = html.replace(/^##### (.*$)/gm, '<h5>$1</h5>')
  html = html.replace(/^#### (.*$)/gm, '<h4>$1</h4>')
  html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>')
  
  // 5. 加粗
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  
  // 6. 列表
  html = html.replace(/^[\-\*] (.*$)/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)+/g, (match) => '<ul>' + match + '</ul>')
  
  // 7. 引用
  html = html.replace(/^&gt; (.*$)/gm, '<blockquote>$1</blockquote>')
  
  // 8. 换行（必须在表格处理之前）
  html = html.replace(/\n/g, '<br>')
  
  // 9. 移除列表标签之间的 <br>（避免列表项之间出现空行）
  html = html.replace(/<\/li><br>/g, '</li>')
  html = html.replace(/<br><ul>/g, '<ul>')
  html = html.replace(/<\/ul><br>/g, '</ul>')
  
  // 10. 表格
  html = renderTable(html, htmlTags)
  
  // 10. 恢复代码块
  codeBlocks.forEach((block, i) => {
    html = html.replace(`%%CODEBLOCK${i}%%`, block)
  })
  
  // 11. 恢复行内代码
  inlineCodes.forEach((code, i) => {
    html = html.replace(`%%INLINECODE${i}%%`, code)
  })
  
  // 12. 恢复 HTML 标签
  htmlTags.forEach((tag, i) => {
    html = html.replace(`%%HTMLTAG${i}%%`, tag)
  })
  
  return html
}

export default {
  escapeHtml,
  renderMarkdown,
  renderTable
}
