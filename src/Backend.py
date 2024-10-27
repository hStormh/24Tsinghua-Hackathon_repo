from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import json
import os
import logging
from zhipuai import ZhipuAI
import subprocess
import requests
from typing import Iterator
import time

app = Flask(__name__)
CORS(app, supports_credentials=True)

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# API配置
ZHIPU_API_KEY_SHITOU = "cbf04086856f4c44d07d5434454d5eeb.kZbVTb99QPLqbMuG"  # 石头的API key
ZHIPU_API_KEY_EUREKA = "55e327303e8428d6f46554724fc1df77.ALeARAozmimW6IyL"  # 尤里卡的API key
client_shitou = ZhipuAI(api_key=ZHIPU_API_KEY_SHITOU)
client_eureka = ZhipuAI(api_key=ZHIPU_API_KEY_EUREKA)

# 提示词文件路径
PROMPTS_FILE_SHITOU = "../prompts/Prompt_button.txt"  # 石头的提示词
PROMPTS_FILE_EUREKA = "../prompts/Prompt_Eureca.txt"  # 尤里卡的提示词

# 存储两个智能体的对话历史
chat_histories_shitou = {}
chat_histories_eureka = {}

# 在文件开头添加必要的导入
import subprocess
import requests
from typing import Iterator
import time

# 添加 MiniMax API 配置
MINIMAX_GROUP_ID = '1849807468884922383'  # 请填入你的 group_id
MINIMAX_API_KEY = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLliJjmtbfpvpkiLCJVc2VyTmFtZSI6IuWImOa1t-m-mSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxODQ5ODA3NDY4ODkzMzEwOTkxIiwiUGhvbmUiOiIxNzgzODUzNzg1MiIsIkdyb3VwSUQiOiIxODQ5ODA3NDY4ODg0OTIyMzgzIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjQtMTAtMjcgMDk6MDI6MDUiLCJpc3MiOiJtaW5pbWF4In0.PNjGniDRsKVViDWonmBfswTK67mw2uZKzv46C4aQSqu2YqoWatVb9VdvwzdRIIi3gpNulYiYsj65k-qclf1YZyyy5-mVVk_YWzAqbVpETNeWEGwo7LAP2onJlKDOaeDksMBN3gDxJS2GB28MYiitTNfzySfIDzOBRW3RgXgVqAnX_SKO0A3pO15xHTpQhMAz5QM69qAbz_R0biKxGkuvZcCul2uZlvhin91MXPrqRrJNxcQ6NYrwdnUxC23E2JKeqWiTlNF3z6U-Nvnud20s9N1v_434ne21YIfuL2h0_bhGoKUHloSUiK1VMptPnvPLzy32dpZ3CiX3EA-bSiB2uw'   # 请填入你的 api_key
MINIMAX_URL = f"https://api.minimax.chat/v1/t2a_v2?GroupId={MINIMAX_GROUP_ID}"

# 添加 MiniMax TTS 相关函数
def build_tts_stream_headers():
    return {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'authorization': f"Bearer {MINIMAX_API_KEY}",
    }

def build_tts_stream_body(text: str) -> dict:
    return {
        "model": "speech-01-turbo",
        "text": text,
        "stream": True,
        "voice_setting": {
            "voice_id": "male-qn-qingse",
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0
        },
        "audio_setting": {
            "audio_sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1
        }
    }

def call_tts_stream(text: str) -> Iterator[bytes]:
    tts_headers = build_tts_stream_headers()
    tts_body = json.dumps(build_tts_stream_body(text))
    
    response = requests.post(MINIMAX_URL, stream=True, headers=tts_headers, data=tts_body)
    for chunk in response.raw:
        if chunk and chunk[:5] == b'data:':
            try:
                data = json.loads(chunk[5:])
                if "data" in data and "extra_info" not in data:
                    if "audio" in data["data"]:
                        yield data["data"]['audio']
            except json.JSONDecodeError:
                continue

def load_prompts(file_path):
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            return file.read().splitlines()
    except Exception as e:
        logging.error(f"加载提示词文件错误: {str(e)}")
        return []

def get_chat_history(session_id, is_shitou=True):
    histories = chat_histories_shitou if is_shitou else chat_histories_eureka
    if session_id not in histories:
        histories[session_id] = [
            {
                "role": "system"
            }
        ]
    return histories[session_id]

def update_chat_history(session_id, role, content, is_shitou=True):
    histories = chat_histories_shitou if is_shitou else chat_histories_eureka
    chat_history = get_chat_history(session_id, is_shitou)
    chat_history.append({"role": role, "content": content})
    if len(chat_history) > 10:
        histories[session_id] = [chat_history[0]] + chat_history[-9:]

def generate_response_glm(session_id, prompt, is_shitou=True):
    try:
        messages = get_chat_history(session_id, is_shitou)
        messages.append({"role": "user", "content": prompt})
        
        # 根据不同的智能体使用不同的客户端
        client = client_shitou if is_shitou else client_eureka
        
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=messages,
            stream=True,
        )
        return response, messages
    except Exception as e:
        logging.error(f"生成回复错误: {str(e)}")
        raise

@app.route("/", methods=["GET"])
def index():
    return render_template('index.html')

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return jsonify({"message": "请使用POST方法发送聊天请求"})
    
    try:
        user_input = request.json.get("text")
        if not user_input:
            return jsonify({"error": "请提供text参数"}), 400
            
        session_id = f"{request.remote_addr}_{request.user_agent.string}"
        logging.info(f"收到用户输入: {user_input}, Session ID: {session_id}")
        
        prompts_shitou = load_prompts(PROMPTS_FILE_SHITOU)
        prompts_eureka = load_prompts(PROMPTS_FILE_EUREKA)
        
        shitou_history = get_chat_history(session_id, True)
        is_first_message = len(shitou_history) == 1
        
        # 为石头和尤里卡准备不同的输入
        combined_prompt_shitou = "\n".join(prompts_shitou) + "\n" + user_input
        
        def generate():
            try:
                # 生成石头的回复
                full_response_shitou = ""
                text_buffer = ""  # 用于累积文本
                response_shitou, messages_shitou = generate_response_glm(session_id, combined_prompt_shitou, True)
                
                # 收集石头的完整响应并同时处理语音
                for chunk in response_shitou:
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content is not None:
                            full_response_shitou += content
                            text_buffer += content
                            
                            # 发送文本更新
                            yield f"data: {json.dumps({'text': content, 'full_response': full_response_shitou, 'agent': '石头'})}\n\n"
                            
                            # 检查是否需要处理语音
                            if any(p in content for p in '。！？，.!?,') or len(text_buffer) >= 20:
                                try:
                                    audio_chunks = call_tts_stream(text_buffer)
                                    audio_data = b""
                                    for audio_chunk in audio_chunks:
                                        if audio_chunk:
                                            audio_hex = bytes.fromhex(audio_chunk)
                                            audio_data += audio_hex
                                    
                                    # 将音频数据作为 base64 编码发送到前端
                                    if audio_data:
                                        import base64
                                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                                        yield f"data: {json.dumps({'audio': audio_base64, 'agent': '石头'})}\n\n"
                                    
                                    # 清空文本缓冲区
                                    text_buffer = ""
                                except Exception as e:
                                    logging.error(f"处理语音时发生错误: {str(e)}")
                
                # 处理最后剩余的文本
                if text_buffer:
                    try:
                        audio_chunks = call_tts_stream(text_buffer)
                        audio_data = b""
                        for audio_chunk in audio_chunks:
                            if audio_chunk:
                                audio_hex = bytes.fromhex(audio_chunk)
                                audio_data += audio_hex
                    
                        if audio_data:
                            import base64
                            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                            yield f"data: {json.dumps({'audio': audio_base64, 'agent': '石头'})}\n\n"
                    except Exception as e:
                        logging.error(f"处理最后的语音时发生错误: {str(e)}")
                
                # 更新石头的历史记录
                update_chat_history(session_id, "user", user_input, True)
                update_chat_history(session_id, "assistant", full_response_shitou, True)
                
                # 处理尤里卡的响应
                if not is_first_message:
                    full_response_eureka = ""
                    
                    # 获取石头的历史对话，但不包括最近一次的对话
                    shitou_history = get_chat_history(session_id, True)[:-2]  # 排除最近的用户输入和石头回复
                    
                    # 构建尤里卡的输入，包含历史对话但不包括最近一次石头的回复
                    history_context = "\n".join([
                        f"{'用户' if msg['role'] == 'user' else '石头'}：{msg['content']}"
                        for msg in shitou_history[1:]  # 跳过system message
                    ])
                    
                    combined_prompt_eureka = (
                        "\n".join(prompts_eureka) + 
                        ("\n历史对话：\n" + history_context if history_context else "") +
                        "\n用户说：" + user_input
                    )
                    
                    # 更新尤里卡的历史记录
                    update_chat_history(session_id, "user", user_input, False)
                    
                    # 生成尤里卡的响应
                    response_eureka, messages_eureka = generate_response_glm(session_id, combined_prompt_eureka, False)
                    
                    # 收集尤里卡的完整响应
                    for chunk in response_eureka:
                        if hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content is not None:
                                full_response_eureka += content
                                yield f"data: {json.dumps({'text': content, 'full_response': full_response_eureka, 'agent': '尤里卡'})}\n\n"
                    
                    # 更新尤里卡的响应到历史记录
                    update_chat_history(session_id, "assistant", full_response_eureka, False)
                else:
                    # 第一次对话只更新用户输入到尤里卡的历史记录
                    update_chat_history(session_id, "user", user_input, False)
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                logging.error(f"生成响应时发生错误: {str(e)}")
                logging.error("错误详情:", exc_info=True)
                raise
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        logging.error(f"处理请求时发生错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/debug/history/<session_id>", methods=["GET"])
def debug_history(session_id):
    return jsonify({
        "石头的历史": chat_histories_shitou.get(session_id, []),
        "尤里卡的历史": chat_histories_eureka.get(session_id, [])
    })

if __name__ == "__main__":
    app.run(debug=True)
