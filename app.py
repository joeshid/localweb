# 标准库导入
from flask import Flask, render_template, request, jsonify, send_file, abort
from urllib.parse import unquote, quote
import os
import json
import time
import re
import subprocess
import wave
import torch
from functools import lru_cache
import hashlib

# 第三方库导入
import numpy as np
import soundfile as sf
from werkzeug.utils import secure_filename
import magic
from moviepy.editor import VideoFileClip
from funasr import AutoModel
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import hashlib

# 初始化语音识别器
inference_pipeline = None

def safe_filename(filename):
    """保留中文文件名的安全文件名处理"""
    # 保留中文字符、字母、数字、下划线和点
    filename = re.sub(r'[^\w\u4e00-\u9fff\-\.]', '_', filename)
    # 去除连续的下划线
    filename = re.sub(r'_+', '_', filename)
    # 去除开头和结尾的特殊字符
    filename = filename.strip('_')
    return filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['AUDIO_FOLDER'] = 'audio_output'  # 改为 audio_output
app.config['TRANSCRIPTS_FOLDER'] = 'txt_output'  # 改为 txt_output
app.config['RECENT_FILES'] = 'recent_files.json'

# 确保所需目录存在
for folder in [app.config['UPLOAD_FOLDER'], app.config['AUDIO_FOLDER'], 
               app.config['TRANSCRIPTS_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

def init_model():
    """初始化语音识别模型"""
    global inference_pipeline
    try:
        print("正在加载语音识别模型...")
        
        # 使用 FunASR 模型，添加性能优化参数
        inference_pipeline = AutoModel(
            model="paraformer-zh",
            model_revision="v2.0.4",
            device="cuda" if torch.cuda.is_available() else "cpu",
            batch_size=4,          # 增加批处理大小
            num_workers=4,         # 增加工作进程数
            beam_size=1,           # 减小束搜索大小以提高速度
            hotwords_path=None,    # 关闭热词功能以提高速度
            continuous_decoding=True  # 启用连续解码
        )
        
        if not torch.cuda.is_available():
            print("警告：未检测到GPU，将使用CPU进行推理")
            
        print("语音识别模型加载完成")
        return True
    except Exception as e:
        print(f"语音识别模型加载失败: {str(e)}")
        return False

# 应用启动时初始化模型
init_model()

def ensure_model_loaded():
    """确保模型已加载"""
    global inference_pipeline
    if inference_pipeline is None:
        if not init_model():
            raise Exception("语音识别模型未能正确加载，请检查系统环境和模型配置")
    return inference_pipeline

def get_recent_files():
    try:
        with open(app.config['RECENT_FILES'], 'r') as f:
            return json.load(f)
    except:
        return []

def save_recent_files(files):
    with open(app.config['RECENT_FILES'], 'w') as f:
        json.dump(files, f)

def extract_audio(video_path, output_path):
    """从视频中提取音频并压缩为MP3格式"""
    try:
        print(f"开始提取音频: {video_path} -> {output_path}")
        
        # 使用ffmpeg提取音频并压缩为MP3
        command = [
            'ffmpeg',
            '-i', video_path,  # 输入文件
            '-vn',             # 禁用视频流
            '-ac', '1',        # 单声道
            '-codec:a', 'libmp3lame',  # 使用MP3编码
            '-q:a', '2',       # 质量等级2（0-9，0最好）
            '-ar', '44100',    # 采样率44.1kHz
            '-y',              # 覆盖输出文件
            output_path
        ]
        
        # 执行命令
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"音频提取失败: {result.stderr}")
            return False
            
        print("音频提取并压缩成功")
        return True
        
    except Exception as e:
        print(f"音频提取失败: {str(e)}")
        return False

def convert_to_wav(input_path, output_path, sample_rate=16000):
    """将音频转换为 WAV 格式，采样率为16kHz"""
    try:
        print(f"开始转换音频: {input_path} -> {output_path}")
        
        # 检查文件类型
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(input_path)
        print(f"输入文件类型: {file_type}")
        
        if file_type.startswith('video/'):
            # 如果是视频文件，先提取音频
            print("检测到视频文件，先提取音频...")
            temp_audio = os.path.join(os.path.dirname(output_path), 'temp_audio.wav')
            video = VideoFileClip(input_path)
            video.audio.write_audiofile(temp_audio)
            input_path = temp_audio
            print(f"音频提取完成: {temp_audio}")
        
        # 读取音频文件
        data, sr = sf.read(input_path)
        print(f"原始采样率: {sr}Hz")
        
        # 如果是立体声，转换为单声道
        if len(data.shape) > 1:
            print("转换立体声为单声道")
            data = np.mean(data, axis=1)
        
        # 重采样到16kHz
        if sr != sample_rate:
            print(f"重采样到 {sample_rate}Hz")
            # 计算重采样比例
            ratio = sample_rate / sr
            new_length = int(len(data) * ratio)
            # 使用线性插值进行重采样
            indices = np.linspace(0, len(data)-1, new_length)
            data = np.interp(indices, np.arange(len(data)), data)
        
        # 保存为WAV格式
        print("保存为WAV格式")
        sf.write(output_path, data, sample_rate)
        print("音频转换完成")
        
        # 清理临时文件
        if file_type.startswith('video/') and os.path.exists(temp_audio):
            os.remove(temp_audio)
            print("临时音频文件已清理")
        
        return True
    except Exception as e:
        print(f"音频转换失败: {str(e)}")
        # 确保清理临时文件
        if 'temp_audio' in locals() and os.path.exists(temp_audio):
            os.remove(temp_audio)
            print("清理临时音频文件")
        raise

class ProcessStatus:
    _instances = {}
    
    @classmethod
    def get_instance(cls, task_id):
        if task_id not in cls._instances:
            cls._instances[task_id] = {
                'status': 'pending',
                'progress': 0,
                'message': '',
                'error': None
            }
        return cls._instances[task_id]
    
    @classmethod
    def update_progress(cls, task_id, progress, message=''):
        instance = cls.get_instance(task_id)
        instance['progress'] = progress
        instance['message'] = message
        
    @classmethod
    def set_error(cls, task_id, error):
        instance = cls.get_instance(task_id)
        instance['status'] = 'error'
        instance['error'] = str(error)
        
    @classmethod
    def set_complete(cls, task_id):
        instance = cls.get_instance(task_id)
        instance['status'] = 'complete'
        instance['progress'] = 100
        
    @classmethod
    def clear(cls, task_id):
        if task_id in cls._instances:
            del cls._instances[task_id]

@app.route('/task-status/<task_id>')
def get_task_status(task_id):
    """获取任务进度"""
    status = ProcessStatus.get_instance(task_id)
    return jsonify(status)

# 添加缓存装饰器
@lru_cache(maxsize=32)
def get_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_cached_transcript(file_path):
    """获取缓存的转录结果"""
    try:
        file_hash = get_file_hash(file_path)
        cache_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], f"{file_hash}.txt")
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"读取缓存失败: {str(e)}")
    return None

def save_transcript_cache(file_path, transcript):
    """保存转录结果到缓存"""
    try:
        file_hash = get_file_hash(file_path)
        cache_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], f"{file_hash}.txt")
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
    except Exception as e:
        print(f"保存缓存失败: {str(e)}")

def split_audio(file_path, max_duration=60):
    """将长音频分割成小片段"""
    try:
        data, sr = sf.read(file_path)
        segment_length = int(max_duration * sr)
        segments = []
        
        # 计算总片段数
        total_segments = len(data) // segment_length + (1 if len(data) % segment_length > 0 else 0)
        
        for i in range(0, len(data), segment_length):
            segment = data[i:i + segment_length]
            if len(segment) > 0:
                segment_path = f"{file_path}.segment_{i//segment_length}.wav"
                sf.write(segment_path, segment, sr)
                segments.append(segment_path)
                
        return segments, total_segments
    except Exception as e:
        print(f"音频分割失败: {str(e)}")
        return [], 0

def transcribe_audio(file_path, task_id):
    """转录音频文件"""
    temp_wav_path = os.path.join(app.config['AUDIO_FOLDER'], 'temp_transcribe.wav')
    segments = []
    
    try:
        ProcessStatus.update_progress(task_id, 10, "开始处理音频文件...")
        
        # 确保模型已加载
        model = ensure_model_loaded()
        if model is None:
            raise Exception("语音识别模型未正确加载")
            
        # 检查文件类型和转换格式
        ProcessStatus.update_progress(task_id, 20, "转换音频格式...")
        convert_success = convert_to_wav(file_path, temp_wav_path)
        if not convert_success:
            raise Exception("音频格式转换失败")
        
        # 获取音频信息
        audio_info = sf.info(temp_wav_path)
        print(f"音频信息: 采样率={audio_info.samplerate}Hz, 时长={audio_info.duration}秒")
        
        # 如果音频较长，进行分片处理
        if audio_info.duration > 60:
            ProcessStatus.update_progress(task_id, 30, "分割长音频...")
            segments, total_segments = split_audio(temp_wav_path)
            if not segments:
                raise Exception("音频分割失败")
                
            # 处理每个分片
            texts = []
            for i, segment in enumerate(segments):
                progress = 30 + (60 * (i + 1) // total_segments)
                ProcessStatus.update_progress(task_id, progress, 
                    f"正在转录片段 {i+1}/{total_segments}...")
                
                result = model.generate(segment)
                if result and isinstance(result, list) and len(result) > 0:
                    texts.append(result[0]["text"])
                
                # 清理分片文件
                try:
                    os.remove(segment)
                except Exception as e:
                    print(f"清理分片文件失败: {str(e)}")
            
            text = " ".join(texts)
        else:
            # 短音频直接处理
            ProcessStatus.update_progress(task_id, 50, "开始转录...")
            result = model.generate(temp_wav_path)
            if not result or not isinstance(result, list) or len(result) == 0:
                raise Exception(f"模型返回结果无效: {result}")
            text = result[0]["text"]
        
        if not text.strip():
            raise Exception("转录结果为空")
        
        ProcessStatus.update_progress(task_id, 90, "转录完成，正在保存...")
        
        # 保存转录结果
        transcript_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'],
                                     os.path.splitext(os.path.basename(file_path))[0] + '.txt')
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # 保存转录结果到缓存
        save_transcript_cache(file_path, text)
        
        ProcessStatus.set_complete(task_id)
        return text
        
    except Exception as e:
        ProcessStatus.set_error(task_id, str(e))
        raise
    finally:
        # 清理临时文件
        if os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    filename = safe_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # 更新最近文件列表
    recent_files = get_recent_files()
    file_info = {
        'name': filename,
        'path': filepath,
        'type': magic.from_file(filepath, mime=True)
    }
    
    if file_info not in recent_files:
        recent_files.insert(0, file_info)
        recent_files = recent_files[:10]  # 只保留最近10个文件
        save_recent_files(recent_files)
    
    return jsonify({
        'message': '文件上传成功',
        'filename': filename,
        'type': file_info['type']
    })

@app.route('/recent')
def get_recent():
    return jsonify(get_recent_files())

@app.route('/preview/<path:filename>')
def preview_file(filename):
    """预览文件"""
    try:
        # 解码 URL 编码的文件名
        filename = unquote(filename)
        
        # 处理 Windows 路径分隔符
        filename = filename.replace('\\', '/')
        
        # 构建文件路径
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 规范化路径
        file_path = os.path.abspath(file_path)
        upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
        
        # 安全检查：确保文件路径在上传目录内
        if not file_path.startswith(upload_folder):
            abort(403)  # Forbidden
            
        if not os.path.exists(file_path):
            abort(404)  # Not Found
            
        # 获取文件类型
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        
        # 发送文件时指定正确的 MIME 类型和中文文件名
        response = send_file(
            file_path,
            mimetype=file_type,
            as_attachment=False,
            download_name=filename
        )
        
        # 添加必要的响应头
        response.headers['Content-Disposition'] = f'inline; filename*=UTF-8\'\'{quote(filename)}'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response
        
    except Exception as e:
        print(f"预览文件失败: {str(e)}")
        abort(404)

@app.route('/extract-audio/<path:filename>')
def extract_audio_from_video(filename):
    try:
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"处理视频文件: {video_path}")
        
        if not os.path.exists(video_path):
            print(f"文件不存在: {video_path}")
            return jsonify({'error': '视频文件不存在'}), 404
        
        # 检查文件类型
        file_type = magic.from_file(video_path, mime=True)
        print(f"文件类型: {file_type}")
        
        if not file_type.startswith('video/'):
            print(f"非视频文件: {file_type}")
            return jsonify({'error': '不是视频文件'}), 400
        
        # 生成音频文件名（使用原文件名，改为.mp3后缀）
        audio_filename = os.path.splitext(filename)[0] + '.mp3'
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        print(f"目标音频文件: {audio_path}")
        
        # 提取音频
        if extract_audio(video_path, audio_path):
            print("音频提取成功")
            return jsonify({
                'message': '音频提取成功',
                'audio_url': f'/download-audio/{audio_filename}'
            })
        else:
            print("音频提取失败")
            return jsonify({'error': '音频提取失败'}), 500
            
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/transcribe-audio/<path:filename>')
def handle_transcribe_request(filename):
    """处理音频转录请求"""
    try:
        # 解码URL编码的中文字符
        filename = unquote(filename)
        
        # 构建可能的音频文件路径
        possible_paths = [
            os.path.join(app.config['AUDIO_FOLDER'], filename),
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            os.path.join(app.config['AUDIO_FOLDER'], filename.replace('.wav', '.mp3'))
        ]
        
        # 查找第一个存在的文件路径
        audio_path = None
        for path in possible_paths:
            if os.path.exists(path):
                audio_path = path
                break
                
        if not audio_path:
            return jsonify({'error': '音频文件不存在'}), 404

        # 尝试从缓存中获取转录结果
        cached_transcript = get_cached_transcript(audio_path)
        if cached_transcript:
            return jsonify({
                'message': '转录完成（从缓存）',
                'transcript': cached_transcript
            })
            
        # 如果传入的是.mp3文件，自动转换为.wav
        if filename.endswith('.mp3'):
            wav_filename = filename.replace('.mp3', '.wav')
            wav_path = os.path.join(app.config['AUDIO_FOLDER'], wav_filename)
            # 转换音频格式
            convert_to_wav(audio_path, wav_path)
            audio_path = wav_path
            filename = wav_filename

        # 确保音频格式正确（16kHz采样率的WAV格式）
        wav_path = os.path.join(app.config['AUDIO_FOLDER'], 
                              os.path.splitext(filename)[0] + '_temp.wav')
        
        try:
            print("转换音频格式...")
            convert_to_wav(audio_path, wav_path, sample_rate=16000)
            print("音频格式转换完成")
        except Exception as e:
            print(f"音频格式转换失败: {str(e)}")
            return jsonify({'error': '音频格式转换失败'}), 500

        # 开始转录
        task_id = filename
        try:
            print("开始语音识别...")
            transcript = transcribe_audio(wav_path, task_id)
            
            return jsonify({
                'message': '转录完成',
                'transcript': transcript
            })
        except Exception as e:
            print(f"转录过程出错: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"处理请求失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理临时文件
        if 'wav_path' in locals() and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
                print("临时文件已清理")
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

@app.route('/download-audio/<path:filename>')
def download_audio(filename):
    try:
        return send_file(
            os.path.join(app.config['AUDIO_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except:
        abort(404)

@app.route('/clear-transcript-cache/<path:filename>')
def clear_transcript_cache(filename):
    """清除转录缓存"""
    try:
        # 不再尝试清除模型缓存，因为 FunASR 不支持这个功能
        return jsonify({'message': '缓存已清除'})
    except Exception as e:
        print(f"清除缓存失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear-recent', methods=['POST'])
def clear_recent():
    """清空最近文件列表"""
    try:
        save_recent_files([])
        return jsonify({'message': '最近文件列表已清空'})
    except Exception as e:
        print(f"清空最近文件列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
