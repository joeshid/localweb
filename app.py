from flask import Flask, render_template, request, jsonify, send_file, abort
import os
import json
import time
import soundfile as sf
import numpy as np
from werkzeug.utils import secure_filename
import numpy as np
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import magic
from moviepy.editor import VideoFileClip
import wave

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

# 初始化语音识别器
print("正在加载语音识别模型...")
try:
    inference_pipeline = pipeline(
        task=Tasks.auto_speech_recognition,
        model='damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
        model_revision='v2.0.5',
        preprocessor=None,
        punc=True  # 启用 FunASR 的标点符号功能
    )
    print("语音识别模型加载完成（包含标点符号功能）")
except Exception as e:
    print(f"语音识别模型加载失败: {str(e)}")
    inference_pipeline = None

# 移除独立的标点符号模型
punc_pipeline = None

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
    """从视频中提取音频"""
    try:
        print(f"开始提取音频: {video_path} -> {output_path}")
        video = VideoFileClip(video_path)
        audio = video.audio
        if audio is not None:
            print("开始写入音频文件...")
            audio.write_audiofile(output_path)
            audio.close()
            print("音频文件写入完成")
        else:
            print("视频没有音轨")
            return False
        video.close()
        return True
    except Exception as e:
        print(f"音频提取失败: {str(e)}")
        return False

def convert_to_wav(input_path, output_path, sample_rate=16000):
    """将音频转换为 WAV 格式，采样率为16kHz"""
    try:
        print(f"开始转换音频: {input_path} -> {output_path}")
        
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
        return True
    except Exception as e:
        print(f"音频转换失败: {str(e)}")
        raise

def transcribe_audio(file_path):
    """转录音频文件"""
    try:
        print(f"开始处理音频文件: {file_path}")
        
        # 准备临时WAV文件路径
        temp_wav_path = os.path.join(app.config['AUDIO_FOLDER'], 'temp.wav')
        
        # 转换音频格式
        print("转换音频格式...")
        convert_success = convert_to_wav(file_path, temp_wav_path)
        if not convert_success:
            raise Exception("音频格式转换失败")
            
        # 使用模型进行转录（包含标点符号）
        print("开始转录（包含标点符号）...")
        if inference_pipeline is None:
            raise Exception("语音识别模型未正确加载")
            
        result = inference_pipeline(temp_wav_path)
        text = result.get('text', '')
        
        print(f"转录完成: {text[:100]}...")  # 只打印前100个字符
        
        # 清理临时文件
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print("临时文件已清理")
            
        return text
        
    except Exception as e:
        print(f"转录过程出错: {str(e)}")
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print("清理临时文件")
        raise

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
    
    filename = secure_filename(file.filename)
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
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except:
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
        
        # 生成音频文件名（使用原文件名，改为.wav后缀）
        audio_filename = os.path.splitext(filename)[0] + '.wav'
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

@app.route('/transcribe-audio/<filename>')
def transcribe_audio(filename):
    """转录音频文件"""
    try:
        # 构建音频文件路径
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], filename)
        if not os.path.exists(audio_path):
            # 如果在音频提取目录中找不到，则查找上传目录
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(audio_path):
            return jsonify({'error': '音频文件不存在'}), 404

        # 构建转录文本文件路径
        transcript_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], 
                                     os.path.splitext(filename)[0] + '.txt')
        
        print(f"处理音频文件: {audio_path}")
        print(f"转录文本路径: {transcript_path}")

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

        if inference_pipeline is None:
            return jsonify({'error': '语音识别模型未正确加载'}), 500

        try:
            print("开始语音识别...")
            # 使用 ModelScope 进行语音识别
            rec_result = inference_pipeline(wav_path)
            print(f"识别结果: {rec_result}")  # 打印完整的识别结果
            
            # 从结果中提取文本
            if isinstance(rec_result, list) and len(rec_result) > 0:
                # 如果结果是列表，获取第一个元素
                first_result = rec_result[0]
                if isinstance(first_result, dict):
                    transcript = first_result.get('text', '')
                else:
                    transcript = str(first_result)
            elif isinstance(rec_result, dict):
                # 如果结果是字典
                transcript = rec_result.get('text', '')
            else:
                # 如果是其他类型，转换为字符串
                transcript = str(rec_result)
            
            if transcript:
                # 保存转录文本
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                print(f"语音识别完成，转录文本: {transcript}")
                return jsonify({
                    'message': '转录完成',
                    'transcript': transcript
                })
            else:
                print("语音识别结果无效")
                return jsonify({'error': '语音识别结果无效'}), 500

        except Exception as e:
            print(f"语音识别失败: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            # 清理临时文件
            if os.path.exists(wav_path):
                os.remove(wav_path)
                
    except Exception as e:
        print(f"处理失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/clear-transcript-cache/<filename>')
def clear_transcript_cache(filename):
    """清除转录缓存"""
    try:
        # 构建转录文本文件路径
        transcript_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], 
                                     os.path.splitext(filename)[0] + '.txt')
        
        # 如果文件存在则删除
        if os.path.exists(transcript_path):
            os.remove(transcript_path)
            print(f"已删除缓存文件: {transcript_path}")
        
        # 清除模型缓存
        if inference_pipeline is not None:
            inference_pipeline.clear_memory_cache()
            
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
