document.getElementById('fileInput').addEventListener('change', uploadFile);

// 复制URL到剪贴板
function copyToClipboard() {
    const urlText = document.getElementById('previewUrl').textContent;
    navigator.clipboard.writeText(urlText)
        .then(() => {
            const copyBtn = document.getElementById('copyBtn');
            copyBtn.textContent = '已复制';
            setTimeout(() => {
                copyBtn.textContent = '复制';
            }, 2000);
        })
        .catch(err => {
            console.error('复制失败:', err);
        });
}

// 上传文件
function uploadFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('uploadInfo').innerHTML = `
            <div class="alert alert-success">
                文件 ${data.filename} 上传成功
            </div>`;
        loadRecentFiles();
        previewFile(data.filename, data.type);
    })
    .catch(error => {
        document.getElementById('uploadInfo').innerHTML = `
            <div class="alert alert-danger">
                上传失败: ${error}
            </div>`;
    });
}

// 加载最近文件列表
function loadRecentFiles() {
    fetch('/recent')
        .then(response => response.json())
        .then(files => {
            const recentFilesList = document.getElementById('recentFilesList');
            recentFilesList.innerHTML = files.map(file => {
                const fileUrl = window.location.origin + `/preview/${file.name}`;
                return `
                    <div class="file-item" onclick="previewFile('${file.name}', '${file.type}')">
                        <div class="mb-2">${file.name}</div>
                        <small class="text-muted d-block">
                            <strong>预览地址：</strong><br>
                            <code class="d-block mt-1">${fileUrl}</code>
                        </small>
                    </div>
                `;
            }).join('');
        });
}

// 预览文件
function previewFile(filename, type) {
    const fullUrl = window.location.origin + `/preview/${filename}`;
    document.getElementById('previewUrl').textContent = fullUrl;
    const container = document.getElementById('previewContainer');
    
    // 清空预览容器
    container.innerHTML = '';

    // 创建预览内容的容器
    const previewContent = document.createElement('div');
    previewContent.className = 'preview-content';
    container.appendChild(previewContent);

    if (type.startsWith('image/')) {
        // 图片预览
        const img = document.createElement('img');
        img.src = fullUrl;
        img.className = 'preview';
        previewContent.appendChild(img);
    } else if (type.startsWith('video/')) {
        // 视频预览
        const video = document.createElement('video');
        video.src = fullUrl;
        video.className = 'preview';
        video.controls = true;
        previewContent.appendChild(video);

        // 视频下方添加提取音频按钮
        const extractBtn = document.createElement('button');
        extractBtn.id = 'extractAudioBtn';
        extractBtn.className = 'btn btn-success';
        extractBtn.textContent = '提取音频';
        extractBtn.onclick = () => extractAudio(filename);
        container.appendChild(extractBtn);
    } else if (type.startsWith('audio/')) {
        // 音频预览
        const audio = document.createElement('audio');
        audio.src = fullUrl;
        audio.controls = true;
        audio.className = 'w-100';
        previewContent.appendChild(audio);

        // 音频下方添加转录按钮
        const transcribeBtn = document.createElement('button');
        transcribeBtn.id = 'transcribeAudioBtn';
        transcribeBtn.className = 'btn btn-primary mt-3';
        transcribeBtn.textContent = '音频转文本';
        transcribeBtn.onclick = () => transcribeAudio(filename);
        container.appendChild(transcribeBtn);
    } else if (type === 'application/pdf') {
        // PDF预览
        const iframe = document.createElement('iframe');
        iframe.src = fullUrl;
        iframe.style.width = '100%';
        iframe.style.height = '100%'; 
        previewContent.appendChild(iframe);
    } else if (type.startsWith('text/') || type === 'application/json') {
        // 文本预览
        fetch(fullUrl)
            .then(response => response.text())
            .then(text => {
                const pre = document.createElement('pre');
                pre.className = 'text-preview';
                pre.textContent = text;
                previewContent.appendChild(pre);
            });
    } else {
        previewContent.innerHTML = `
            <div class="alert alert-info">
                该文件类型（${type}）暂不支持预览，
                <a href="${fullUrl}" target="_blank">点击下载</a>
            </div>`;
    }
}

// 提取音频
function extractAudio(filename) {
    const extractBtn = document.getElementById('extractAudioBtn');
    extractBtn.disabled = true;
    extractBtn.textContent = '提取中...';
    
    console.log('开始提取音频:', filename);
    
    fetch(`/extract-audio/${filename}`)
        .then(response => {
            console.log('收到响应:', response.status);
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || '提取失败');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('提取成功:', data);
            const audioUrl = window.location.origin + data.audio_url;
            // 创建音频信息区域
            const container = document.getElementById('previewContainer');
            
            // 创建新的音频区域
            const audioSection = document.createElement('div');
            audioSection.className = 'audio-section';
            
            // 设置音频区域的内容
            audioSection.innerHTML = `
                <div class="alert alert-success">音频提取成功！</div>
                <div class="mt-3">
                    <strong>音频文件地址：</strong>
                    <div class="url-display">
                        ${audioUrl}
                    </div>
                </div>
                <audio src="${audioUrl}" controls class="w-100"></audio>
                <div class="btn-group mt-3">
                    <button class="btn btn-outline-secondary" onclick="navigator.clipboard.writeText('${audioUrl}')">
                        复制地址
                    </button>
                    <a href="${audioUrl}" class="btn btn-primary" download>
                        下载音频
                    </a>
                </div>
                <div class="mt-3">
                    <button class="btn btn-primary" onclick="transcribeAudio('${filename.replace('.mp4', '.wav')}')">
                        音频转文本
                    </button>
                </div>
            `;
            
            // 移除之前的音频区域（如果存在）
            const existingAudioSection = container.querySelector('.audio-section');
            if (existingAudioSection) {
                existingAudioSection.remove();
            }
            
            // 添加新的音频区域
            container.appendChild(audioSection);
        })
        .catch(error => {
            console.error('提取失败:', error);
            const container = document.getElementById('previewContainer');
            const errorMsg = document.createElement('div');
            errorMsg.className = 'mt-3 alert alert-danger';
            errorMsg.textContent = `音频提取失败: ${error.message}`;
            container.appendChild(errorMsg);
        })
        .finally(() => {
            extractBtn.disabled = false;
            extractBtn.textContent = '提取音频';
        });
}

// 转录音频
function transcribeAudio(filename) {
    const transcribeBtn = document.querySelector('#transcribeAudioBtn, .btn-primary[onclick*="transcribeAudio"]');
    if (transcribeBtn) {
        transcribeBtn.disabled = true;
        transcribeBtn.textContent = '转录中...';
    }
    
    console.log('开始转录音频:', filename);

    // 首先清除缓存
    fetch(`/clear-transcript-cache/${filename}`)
        .then(response => response.json())
        .then(data => {
            console.log('缓存清除结果:', data);
            // 继续进行转录
            return fetch(`/transcribe-audio/${filename}`);
        })
        .then(response => {
            console.log('收到响应:', response.status);
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || '转录失败');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('转录成功:', data);
            const container = document.getElementById('previewContainer');
            
            // 创建转录文本区域
            const transcriptionSection = document.createElement('div');
            transcriptionSection.className = 'transcription-section mt-4';
            
            // 设置转录文本区域的内容
            transcriptionSection.innerHTML = `
                <div class="alert alert-success">音频转录成功！</div>
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">转录文本</h5>
                    </div>
                    <div class="card-body">
                        <div class="text-content">
                            ${data.transcript || data.text || '无转录结果'}
                        </div>
                        <div class="copy-container">
                            <button class="btn btn-outline-secondary mt-3" onclick="copyTranscript('${data.transcript || data.text || ''}', this)">
                                复制文本
                            </button>
                            <span class="copy-feedback"></span>
                        </div>
                    </div>
                </div>
            `;
            
            // 移除之前的转录文本区域（如果存在）
            const existingTranscriptionSection = container.querySelector('.transcription-section');
            if (existingTranscriptionSection) {
                existingTranscriptionSection.remove();
            }
            
            // 添加新的转录文本区域
            container.appendChild(transcriptionSection);
        })
        .catch(error => {
            console.error('转录失败:', error);
            const container = document.getElementById('previewContainer');
            const errorMsg = document.createElement('div');
            errorMsg.className = 'mt-3 alert alert-danger';
            errorMsg.textContent = `音频转录失败: ${error.message}`;
            container.appendChild(errorMsg);
        })
        .finally(() => {
            if (transcribeBtn) {
                transcribeBtn.disabled = false;
                transcribeBtn.textContent = '音频转文本';
            }
        });
}

// 清空最近文件列表
function clearRecentFiles() {
    if (!confirm('确定要清空最近文件列表吗？')) {
        return;
    }
    
    fetch('/clear-recent', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        console.log('清空成功:', data);
        // 重新加载文件列表
        loadRecentFiles();
        // 清空预览区域
        document.getElementById('previewUrl').textContent = '';
        document.getElementById('previewContainer').innerHTML = '';
    })
    .catch(error => {
        console.error('清空失败:', error);
        alert('清空失败: ' + error);
    });
}

// 复制转录文本
function copyTranscript(text, button) {
    if (!text) {
        showCopyFeedback(button, '没有可复制的内容', 'error');
        return;
    }

    // 创建临时textarea元素
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
        // 尝试使用现代API
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    showCopyFeedback(button, '已复制', 'success');
                })
                .catch(() => {
                    // 如果现代API失败，回退到旧方法
                    document.execCommand('copy');
                    showCopyFeedback(button, '已复制', 'success');
                });
        } else {
            // 使用旧方法
            document.execCommand('copy');
            showCopyFeedback(button, '已复制', 'success');
        }
    } catch (err) {
        showCopyFeedback(button, '复制失败，请手动复制', 'error');
    } finally {
        // 移除临时元素
        document.body.removeChild(textarea);
    }
}

// 显示复制反馈
function showCopyFeedback(button, message, type) {
    const feedback = button.parentElement.querySelector('.copy-feedback');
    if (feedback) {
        feedback.textContent = message;
        feedback.classList.remove('success', 'error');
        feedback.classList.add(type);
        feedback.style.opacity = '1';
        
        // 3秒后淡出提示
        setTimeout(() => {
            feedback.style.opacity = '0';
        }, 3000);
    }
}

// 页面加载时获取最近文件列表
document.addEventListener('DOMContentLoaded', loadRecentFiles);
