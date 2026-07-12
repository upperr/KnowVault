        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                const tab = this.dataset.tab;
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
                document.getElementById('panel-' + tab).classList.add('active');
                if (tab === 'documents' || tab === 'memory') refreshStatus();
            });
        });

        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast ' + type;
            toast.innerHTML = '<span>' + (type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️') + '</span><span>' + message + '</span>';
            container.appendChild(toast);
            setTimeout(() => { toast.remove(); }, 3000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 发送问题（流式）
        function sendQuestion() {
            sendQuestionStream();
        }

        function addChatMessage(content, type, sources = []) {
            const container = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message message-' + type;
            
            let bubbleClass = type === 'user' ? 'message-bubble-user' : 'message-bubble-assistant';
            
            // 用户消息直接转义，助手消息使用 Markdown 渲染
            let bubbleContent = type === 'user' 
                ? escapeHtml(content) 
                : renderMarkdown(content);
            
            let html = '<div class="' + bubbleClass + '">' + bubbleContent + '</div>';
            
            if (sources && sources.length > 0) {
                html += '<div class="message-sources"><div class="message-sources-title">📚 参考来源</div><ul class="message-sources-list">' + 
                    sources.map(s => '<li>📄 ' + escapeHtml(s) + '</li>').join('') + '</ul></div>';
            }
            
            messageDiv.innerHTML = html;
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }

        function browseFolder() {
            const input = document.createElement('input');
            input.type = 'file';
            input.webkitdirectory = true;
            input.onchange = function(e) {
                if (e.target.files && e.target.files.length > 0) {
                    const fullPath = e.target.files[0].webkitRelativePath;
                    if (fullPath) {
                        const rootFolder = fullPath.split('/')[0];
                        document.getElementById('doc-dir-input').value = 'data/documents/' + rootFolder;
                        showToast('已选择文件夹：' + rootFolder, 'success');
                    }
                }
            };
            input.click();
        }

        async function syncDocuments() {
            const btn = document.getElementById('sync-btn');
            const loading = document.getElementById('sync-loading');
            const resultDiv = document.getElementById('sync-result');
            const docDir = document.getElementById('doc-dir-input').value.trim() || 'data/documents';
            btn.disabled = true;
            loading.classList.add('show');
            resultDiv.style.display = 'none';
            try {
                const resp = await fetch('/api/files/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ doc_dir: docDir }),
                });
                const data = await resp.json();
                resultDiv.style.display = 'block';
                if (data.status === 'ok') {
                    const processed = data.sync_result.added + data.sync_result.updated + data.sync_result.unchanged;
                    resultDiv.innerHTML = '<div style="color:var(--success);font-weight:600;margin-bottom:8px;">✅ 同步成功！</div><div style="font-size:13px;color:var(--text-secondary);">处理文件数：' + processed + ' | 新增：' + data.sync_result.added + ' | 更新：' + data.sync_result.updated + '</div>';
                    showToast('文档同步成功', 'success');
                    refreshStatus();
                } else {
                    resultDiv.innerHTML = '<span style="color:var(--warning);">' + data.message + '</span>';
                    showToast(data.message, 'warning');
                }
            } catch (err) {
                showToast('同步失败：' + err.message, 'error');
            }
            btn.disabled = false;
            loading.classList.remove('show');
        }

        async function refreshStatus() {
            try {
                const resp = await fetch('/api/files/status');
                const data = await resp.json();
                document.getElementById('header-files').textContent = (data.knowledge_base.total_files || 0) + ' 文件';
                document.getElementById('header-chunks').textContent = (data.knowledge_base.total_chunks || 0) + ' 片段';
                document.getElementById('stat-files').textContent = data.knowledge_base.total_files || 0;
                document.getElementById('stat-chunks').textContent = data.knowledge_base.total_chunks || 0;
                const memTotal = (data.memory?.short_term?.size || 0) + (data.memory?.long_term?.total_entries || 0);
                document.getElementById('stat-memory').textContent = memTotal;
                const docResp = await fetch('/api/files/documents');
                const docData = await docResp.json();
                const listDiv = document.getElementById('doc-list');
                if (docData.file_list && docData.file_list.length > 0) {
                    listDiv.innerHTML = docData.file_list.map(f => {
                        const fileName = typeof f === 'object' ? f.file_name : f.split('/').pop();
                        const ext = fileName.split('.').pop().toLowerCase();
                        let icon = '📄';
                        if (ext === 'pdf') icon = '📕';
                        else if (['doc', 'docx'].includes(ext)) icon = '📘';
                        else if (['txt', 'md', 'csv'].includes(ext)) icon = '📝';
                        return '<div class="doc-item"><span class="doc-icon">' + icon + '</span><span class="doc-name">' + escapeHtml(fileName) + '</span><button class="btn btn-danger btn-sm" onclick="deleteDocument(\'' + fileName.replace(/'/g, "\\'") + '\')" style="margin-left:auto;padding:6px 12px;font-size:12px;">🗑️ 删除</button></div>';
                    }).join('');
                } else {
                    listDiv.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-secondary);font-size:14px;">暂无文档</div>';
                }
                if (document.getElementById('panel-memory').classList.contains('active')) {
                    updateMemoryStats(data.memory);
                }
            } catch (err) {
                console.error('Failed to refresh status:', err);
            }
        }

        async function refreshMemoryStats() {
            try {
                const resp = await fetch('/api/memory/stats');
                const data = await resp.json();
                updateMemoryStats(data.memory);
                showToast('记忆统计已更新', 'success');
            } catch (err) {
                showToast('刷新失败：' + err.message, 'error');
            }
        }

        function updateMemoryStats(memory) {
            if (!memory) return;
            document.getElementById('mem-short-size').textContent = memory.short_term?.size || 0;
            document.getElementById('mem-short-hits').textContent = memory.short_term?.total_hits || 0;
            document.getElementById('mem-long-entries').textContent = memory.long_term?.total_entries || 0;
            document.getElementById('mem-long-keywords').textContent = memory.long_term?.keyword_count || 0;
        }

        async function clearMemory(type) {
            if (!confirm('确定要清空' + (type === 'all' ? '全部' : type === 'short' ? '短期' : '长期') + '记忆吗？')) return;
            try {
                const resp = await fetch('/api/memory/clear', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ short_term: type === 'short' || type === 'all', long_term: type === 'long' || type === 'all' }),
                });
                const data = await resp.json();
                showToast(data.message, 'success');
                refreshMemoryStats();
            } catch (err) {
                showToast('操作失败：' + err.message, 'error');
            }
        }

        async function startCreationStream() {
            const requirement = document.getElementById('creation-requirement').value.trim();
            const title = document.getElementById('creation-title').value.trim();
            if (!requirement) { showToast('请输入创作要求', 'warning'); return; }
            const resultDiv = document.getElementById('creation-result');
            resultDiv.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;gap:12px;padding:40px;color:var(--text-secondary);"><div class="spinner"></div><span>正在创作中...</span></div>';
            
            lastRawContent = '';
            let exportBtn = document.getElementById('export-docx-btn');
            if (exportBtn) exportBtn.disabled = true;
            
            try {
                const resp = await fetch('/api/create/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ requirement: requirement, title: title }),
                });
                
                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                resultDiv.innerHTML = '';
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'content') {
                                lastRawContent += data.content;
                                resultDiv.innerHTML = renderMarkdown(lastRawContent);
                                resultDiv.scrollTop = resultDiv.scrollHeight;
                            } else if (data.type === 'done') {
                                document.getElementById('copy-btn').disabled = false;
                                if (exportBtn) exportBtn.disabled = false;
                                showToast('创作完成', 'success');
                            } else if (data.type === 'error') {
                                showToast('创作失败：' + data.message, 'error');
                            }
                        }
                    }
                }
            } catch (err) {
                resultDiv.innerHTML = '<div style="color:var(--error);text-align:center;padding:40px;">请求失败</div>';
                showToast('请求失败', 'error');
            }
        }

        let lastRawContent = '';

function copyResult() {
            // 复制原始内容（纯文本格式）
            if (lastRawContent) {
                navigator.clipboard.writeText(lastRawContent).then(() => showToast('已复制纯文本到剪贴板', 'success'));
            } else {
                const text = document.getElementById('creation-result').innerText;
                navigator.clipboard.writeText(text).then(() => showToast('已复制到剪贴板', 'success'));
            }
        }

        // 导出创作结果为 DOCX
        async function exportCreationToDocx() {
            if (!lastRawContent) {
                showToast('没有可导出的内容', 'warning');
                return;
            }
            
            const btn = document.getElementById('export-docx-btn');
            btn.disabled = true;
            btn.textContent = '⏳ 导出中...';
            
            try {
                const title = document.getElementById('creation-title').value.trim() || '创作文档';
                
                const resp = await fetch('/api/files/export/docx', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: lastRawContent,
                        title: title,
                        filename: title.replace(/[\\/:*?"<>|]/g, '_')
                    }),
                });
                
                if (!resp.ok) {
                    const error = await resp.json();
                    throw new Error(error.detail || '导出失败');
                }
                
                // 下载文件
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = title.replace(/[\\/:*?"<>|]/g, '_') + '.docx';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                showToast('导出成功', 'success');
            } catch (err) {
                showToast('导出失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '📄 导出 DOCX';
            }
        }

        // 导出优化结果为 DOCX
        async function exportOptimizeToDocx() {
            if (!optimizeResult) {
                showToast('没有可导出的内容', 'warning');
                return;
            }
            
            const btn = document.getElementById('export-opt-docx-btn');
            btn.disabled = true;
            btn.textContent = '⏳ 导出中...';
            
            try {
                const filename = currentFileName ? currentFileName.replace(/\.[^.]+$/, '') + '_optimized' : 'optimized_doc';
                
                const resp = await fetch('/api/files/export/docx', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: optimizeResult,
                        title: filename,
                        filename: filename.replace(/[\\/:*?"<>|]/g, '_')
                    }),
                });
                
                if (!resp.ok) {
                    const error = await resp.json();
                    throw new Error(error.detail || '导出失败');
                }
                
                // 下载文件
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename.replace(/[\\/:*?"<>|]/g, '_') + '.docx';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                showToast('导出成功', 'success');
            } catch (err) {
                showToast('导出失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '📄 导出 DOCX';
            }
        }


        async function deleteDocument(fileName) {
            if (!confirm('确定要从知识库中删除 "' + fileName + '" 吗？')) return;
            try {
                const encodedFileName = encodeURIComponent(fileName);
                const resp = await fetch('/api/files/' + encodedFileName, {
                    method: 'DELETE',
                });
                const data = await resp.json();
                if (data.status === 'success') {
                    showToast('删除成功', 'success');
                    refreshStatus();
                } else {
                    showToast('删除失败：' + (data.message || '未知错误'), 'error');
                }
            } catch (err) {
                showToast('删除失败：' + err.message, 'error');
            }
        }

        async function clearKB() {
            if (!confirm('确定要清空知识库吗？此操作不可撤销。')) return;
            try {
                const resp = await fetch('/api/files/clear', { method: 'POST' });
                const data = await resp.json();
                showToast('清空成功', 'success');
                refreshStatus();
            } catch (err) {
                showToast('清空失败：' + err.message, 'error');
            }
        }

        refreshStatus();
    
        // Markdown 渲染器
        function renderMarkdown(text) {
            if (!text) return '';
            
            let html = text;
            
            // 1. 保护代码块不被转义
            const codeBlocks = [];
            html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
                codeBlocks.push('<pre><code>' + escapeHtml(code) + '</code></pre>');
                return `%%CODEBLOCK${codeBlocks.length - 1}%%`;
            });
            
            // 2. 保护行内代码
            const inlineCodes = [];
            html = html.replace(/`([^`]+)`/g, (match, code) => {
                inlineCodes.push('<code>' + escapeHtml(code) + '</code>');
                return `%%INLINECODE${inlineCodes.length - 1}%%`;
            });
            
            // 3. 转义 HTML
            html = escapeHtml(html);
            
            // 4. 标题
            html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
            html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
            html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');
            
            // 5. 加粗
            html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            
            // 6. 列表
            html = html.replace(/^[\-\*] (.*$)/gm, '<li>$1</li>');
            html = html.replace(/(\n<li>.*<\/li>)+/g, (match) => '<ul>' + match + '</ul>');
            
            // 7. 引用
            html = html.replace(/^&gt; (.*$)/gm, '<blockquote>$1</blockquote>');
            
            // 8. 表格
            html = renderTable(html);
            
            // 9. 换行
            html = html.replace(/\n/g, '<br>');
            
            // 10. 恢复代码块
            codeBlocks.forEach((block, i) => {
                html = html.replace(`%%CODEBLOCK${i}%%`, block);
            });
            
            // 11. 恢复行内代码
            inlineCodes.forEach((code, i) => {
                html = html.replace(`%%INLINECODE${i}%%`, code);
            });
            
            return html;
        }
        
        // 表格渲染
        function renderTable(html) {
            const lines = html.split('<br>');
            let inTable = false;
            let tableHtml = '';
            let rows = [];
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                
                // 检测表格行 (包含 | 的行)
                if (line.startsWith('|') && line.endsWith('|')) {
                    if (!inTable) {
                        inTable = true;
                        rows = [];
                    }
                    
                    // 跳过分隔行 (|---|---|)
                    if (line.match(/^\|[\s\-:|]+\|$/)) {
                        continue;
                    }
                    
                    // 解析单元格
                    const cells = line.split('|').slice(1, -1).map(c => c.trim());
                    rows.push(cells);
                } else {
                    // 输出表格并重置
                    if (inTable && rows.length > 0) {
                        tableHtml += renderTableHTML(rows);
                        inTable = false;
                        rows = [];
                    }
                    tableHtml += lines[i] + '<br>';
                }
            }
            
            // 处理末尾的表格
            if (inTable && rows.length > 0) {
                tableHtml += renderTableHTML(rows);
            }
            
            return tableHtml;
        }
        
        function renderTableHTML(rows) {
            if (rows.length === 0) return '';
            
            let html = '<table><thead><tr>';
            
            // 第一行作为表头
            rows[0].forEach(cell => {
                html += '<th>' + cell + '</th>';
            });
            
            html += '</tr></thead><tbody>';
            
            // 其余行作为数据行
            for (let i = 1; i < rows.length; i++) {
                html += '<tr>';
                rows[i].forEach(cell => {
                    html += '<td>' + cell + '</td>';
                });
                html += '</tr>';
            }
            
            html += '</tbody></table>';
            return html;
        }

    
        // 流式问答
        async function sendQuestionStream() {
            const input = document.getElementById('question-input');
            const btn = document.getElementById('send-btn');
            const useHistory = document.getElementById('use-history').checked;
            const question = input.value.trim();
            
            if (!question) { showToast('请输入问题', 'warning'); return; }
            
            // 添加用户消息
            addChatMessage(question, 'user');
            input.value = '';
            btn.disabled = true;
            
            // 创建助手消息容器
            const container = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message message-assistant';
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble-assistant';
            bubbleDiv.id = 'streaming-answer';
            bubbleDiv.innerHTML = '<span class="typing-indicator">正在思考</span>';
            messageDiv.appendChild(bubbleDiv);
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
            
            let fullAnswer = '';
            let sources = [];
            
            try {
                const response = await fetch('/api/qa/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question, use_history: useHistory }),
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                
                                if (data.type === 'start') {
                                    // 开始生成，清空"正在思考"提示
                                    bubbleDiv.innerHTML = '';
                                } else if (data.type === 'answer') {
                                    fullAnswer += data.content;
                                    bubbleDiv.innerHTML = renderMarkdown(fullAnswer);
                                    container.scrollTop = container.scrollHeight;
                                } else if (data.type === 'sources') {
                                    sources = data.sources;
                                } else if (data.type === 'error') {
                                    bubbleDiv.innerHTML = '⚠️ ' + data.message;
                                    showToast(data.message, 'warning');
                                    input.disabled = false;
                                    btn.disabled = false;
                                    return;
                                } else if (data.type === 'done') {
                                    // 添加来源
                                    if (sources.length > 0) {
                                        const sourcesDiv = document.createElement('div');
                                        sourcesDiv.className = 'message-sources';
                                        sourcesDiv.innerHTML = '<div class="message-sources-title">📚 参考来源</div><ul class="message-sources-list">' + 
                                            sources.map(s => '<li>📄 ' + escapeHtml(s) + '</li>').join('') + '</ul>';
                                        messageDiv.appendChild(sourcesDiv);
                                    }
                                    container.scrollTop = container.scrollHeight;
                                    input.disabled = false;
                                    btn.disabled = false;
                                }
                            } catch (e) {
                                console.error('Parse error:', e);
                            }
                        }
                    }
                }
                
                showToast('回答完成', 'success');
            } catch (err) {
                bubbleDiv.innerHTML = '请求失败：' + err.message;
                showToast('请求失败', 'error');
                input.disabled = false;
                btn.disabled = false;
            } finally {
                // 确保按钮恢复
                if (!btn.disabled) {
                    input.disabled = false;
                    btn.disabled = false;
                }
            }
        }

        // 文档优化相关变量
        let currentFileContent = '';
        let currentFileName = '';
        let optimizeResult = '';
        
        // 文件拖拽处理
        function handleDrop(event) {
            event.preventDefault();
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                processFile(files[0]);
            }
        }
        
        // 文件选择处理
        function handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                processFile(files[0]);
            }
        }
        
        // 处理文件
        let isParsing = false;  // 标记是否正在解析
        
        async function processFile(file) {
            const allowedTypes = ['application/pdf', 'application/msword', 
                                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                                  'text/plain'];
            
            const allowedExts = ['.pdf', '.doc', '.docx', '.txt'];
            const ext = file.name.split('.').pop().toLowerCase();
            
            if (!allowedExts.includes('.' + ext)) {
                showToast('不支持的文件格式', 'error');
                return;
            }
            
            currentFileName = file.name;
            
            // 显示文件信息
            document.getElementById('file-name').textContent = file.name;
            document.getElementById('file-size').textContent = (file.size / 1024).toFixed(1) + ' KB';
            document.getElementById('file-info').style.display = 'block';
            
            // 上传文件
            const formData = new FormData();
            formData.append('file', file);
            
            showToast('正在上传文件...', 'info');
            isParsing = true;  // 标记开始解析
            updateOptimizeButton();  // 更新按钮状态
            
            try {
                const resp = await fetch('/api/files/upload', {
                    method: 'POST',
                    body: formData,
                });
                const data = await resp.json();
                
                if (data.status === 'success' || data.status === 'ok') {
                    currentFileContent = data.content;
                    showToast('文件上传成功', 'success');
                } else {
                    showToast('文件解析失败：' + (data.detail || data.message || '未知错误'), 'error');
                    currentFileContent = '';
                }
            } catch (err) {
                showToast('上传失败：' + err.message, 'error');
                currentFileContent = '';
            } finally {
                isParsing = false;  // 解析完成
                updateOptimizeButton();  // 更新按钮状态
            }
        }
        
        // 更新优化按钮状态
        function updateOptimizeButton() {
            const optimizeBtn = document.getElementById('optimize-btn');
            if (!optimizeBtn) return;
            
            if (isParsing) {
                optimizeBtn.disabled = true;
                optimizeBtn.textContent = '⏳ 文档解析中，请稍后...';
                optimizeBtn.style.opacity = '0.6';
                optimizeBtn.style.cursor = 'not-allowed';
            } else {
                optimizeBtn.disabled = false;
                optimizeBtn.textContent = '✨ 开始优化';
                optimizeBtn.style.opacity = '1';
                optimizeBtn.style.cursor = 'pointer';
            }
        }
        
        // 清除文件
        function clearFile() {
            currentFileContent = '';
            currentFileName = '';
            isParsing = false;  // 重置解析状态
            document.getElementById('file-input').value = '';
            document.getElementById('file-info').style.display = 'none';
            document.getElementById('optimize-result').innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 40px;">请上传文档并选择优化类型后点击「开始优化」</div>';
            updateOptimizeButton();  // 更新按钮状态
        }
        
        // 开始优化
        async function startOptimize() {
            // 检查是否正在解析
            if (isParsing) {
                showToast('文档解析中，请稍后...', 'warning');
                return;
            }
            
            if (!currentFileContent) {
                showToast('请先上传文档', 'warning');
                return;
            }
            
            const instruction = document.getElementById('optimize-instruction').value.trim();
            
            if (!instruction) {
                showToast('请输入修改要求', 'warning');
                return;
            }
            
            const resultDiv = document.getElementById('optimize-result');
            const copyBtn = document.getElementById('copy-opt-btn');
            const downloadBtn = document.getElementById('export-opt-docx-btn');
            
            resultDiv.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;gap:12px;padding:40px;color:var(--text-secondary);"><div class="spinner"></div><span>正在优化中...</span></div>';
            copyBtn.disabled = true;
            downloadBtn.disabled = true;
            
            optimizeResult = '';
            
            try {
                const resp = await fetch('/api/optimize/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: currentFileContent,
                        instruction: instruction,
                    }),
                });
                
                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                
                                if (data.type === 'content') {
                                    optimizeResult += data.content;
                                    resultDiv.innerHTML = renderMarkdown(optimizeResult);
                                    resultDiv.scrollTop = resultDiv.scrollHeight;
                                } else if (data.type === 'error') {
                                    resultDiv.innerHTML = '<div style="color:var(--error);text-align:center;padding:40px;">优化失败：' + data.message + '</div>';
                                    showToast('优化失败', 'error');
                                    return;
                                } else if (data.type === 'done') {
                                    if (copyBtn) copyBtn.disabled = false;
                                    if (downloadBtn) downloadBtn.disabled = false;
                                    showToast('优化完成', 'success');
                                }
                            } catch (e) {
                                console.error('Parse error:', e);
                            }
                        }
                    }
                }
            } catch (err) {
                resultDiv.innerHTML = '<div style="color:var(--error);text-align:center;padding:40px;">请求失败：' + err.message + '</div>';
                showToast('请求失败', 'error');
            }
        }
        
        // 复制优化结果
        function copyOptimizeResult() {
            if (optimizeResult) {
                navigator.clipboard.writeText(optimizeResult).then(() => {
                    showToast('已复制纯文本到剪贴板', 'success');
                });
            }
        }
        

