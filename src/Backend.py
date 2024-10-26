from flask import Flask, request, jsonify, render_template, Response, url_for
from flask_cors import CORS
import json
import os
import logging
from zhipuai import ZhipuAI
import subprocess
import requests
from typing import Iterator
import time

app = Flask(__name__, static_folder='static')  # 指定静态文件夹
CORS(app, supports_credentials=True)

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 清空聊天历史的函数
def clear_chat_histories():
    global chat_histories_shitou, chat_histories_eureka
    chat_histories_shitou = {}
    chat_histories_eureka = {}
    logging.info("聊天历史已清空")

# API配置
ZHIPU_API_KEY_SHITOU = "cbf04086856f4c44d07d5434454d5eeb.kZbVTb99QPLqbMuG"  # 石头的API key
ZHIPU_API_KEY_EUREKA = "55e327303e8428d6f46554724fc1df77.ALeARAozmimW6IyL"  # 尤里卡的API key
client_shitou = ZhipuAI(api_key=ZHIPU_API_KEY_SHITOU)
client_eureka = ZhipuAI(api_key=ZHIPU_API_KEY_EUREKA)

# 提示词文件路径
PROMPTS_FILE_SHITOU = "../prompts/Prompt_button.txt"  # 石头的提示词
PROMPTS_FILE_EUREKA = "../prompts/Prompt_Eureca.txt"  # 尤里卡的提示词

# ���储两个智能体的对话历史
chat_histories_shitou = {}
chat_histories_eureka = {}

# 在文件开头添加必要的导入
import subprocess
import requests
from typing import Iterator
import time

# 添加 MiniMax API 配置
MINIMAX_GROUP_ID_SHITOU = '1849807468884922383'  # 石头的 group_id
MINIMAX_GROUP_ID_EUREKA = '1849807468884922383'  # 尤里卡的 group_id
MINIMAX_API_KEY_SHITOU = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLliJjmtbfpvpkiLCJVc2VyTmFtZSI6IuWImOa1t-m-mSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxODQ5ODA3NDY4ODkzMzEwOTkxIiwiUGhvbmUiOiIxNzgzODUzNzg1MiIsIkdyb3VwSUQiOiIxODQ5ODA3NDY4ODg0OTIyMzgzIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjQtMTAtMjcgMDk6MDI6MDUiLCJpc3MiOiJtaW5pbWF4In0.PNjGniDRsKVViDWonmBfswTK67mw2uZKzv46C4aQSqu2YqoWatVb9VdvwzdRIIi3gpNulYiYsj65k-qclf1YZyyy5-mVVk_YWzAqbVpETNeWEGwo7LAP2onJlKDOaeDksMBN3gDxJS2GB28MYiitTNfzySfIDzOBRW3RgXgVqAnX_SKO0A3pO15xHTpQhMAz5QM69qAbz_R0biKxGkuvZcCul2uZlvhin91MXPrqRrJNxcQ6NYrwdnUxC23E2JKeqWiTlNF3z6U-Nvnud20s9N1v_434ne21YIfuL2h0_bhGoKUHloSUiK1VMptPnvPLzy32dpZ3CiX3EA-bSiB2uw'   # 石头的 api_key
MINIMAX_API_KEY_EUREKA = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLliJjmtbfpvpkiLCJVc2VyTmFtZSI6IuWImOa1t-m-mSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxODQ5ODA3NDY4ODkzMzEwOTkxIiwiUGhvbmUiOiIxNzgzODUzNzg1MiIsIkdyb3VwSUQiOiIxODQ5ODA3NDY4ODg0OTIyMzgzIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjQtMTAtMjcgMTE6MDk6MDkiLCJpc3MiOiJtaW5pbWF4In0.WkokdRhNNAW4ZC1TJWLB4D5bdiky6m0ygDv_zIeprBkcI4diyrwlYj6P33F03udH7DaenWDNlXqnLVEPdiGuhr_bKwQoGubMeWd4vc75HsvH0cZ2UGIvOiUQUjwTBuwfXnvx-2DF7cPWo0mBMbwuLdc33zfHeCaF4N2ol795IrfgTm6eO40DsHFE0jOD7Aam_E6Dyc5HHlHYEP-WcyLEyjbVe3m9_zDyUV7nL2CGqFof0AKxCrG9OD95SlxS2ZsRVBnkmV2M639EvuxBrjFK-EVk29M3w9_X6uBq5Fv65qsJvMRnj-nMFUt4ExUIoqeMQM6IGIzb9ewwLwQ6EMbSKA'   # 尤里卡的 api_key

# 更新 TTS 相关函数
def build_tts_stream_headers(is_shitou=True):
    api_key = MINIMAX_API_KEY_SHITOU if is_shitou else MINIMAX_API_KEY_EUREKA
    return {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'authorization': f"Bearer {api_key}",
    }

def build_tts_stream_body(text: str, is_shitou=True) -> dict:
    return {
        "model": "speech-01-turbo",
        "text": text,
        "stream": True,
        "voice_setting": {
            "voice_id": "male-qn-qingse" if is_shitou else "Cute_Elf",  # 石头用男声，尤里卡用女声
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

def call_tts_stream(text: str, is_shitou=True) -> Iterator[bytes]:
    try:
        group_id = MINIMAX_GROUP_ID_SHITOU if is_shitou else MINIMAX_GROUP_ID_EUREKA
        url = f"https://api.minimax.chat/v1/t2a_v2?GroupId={group_id}"
        tts_headers = build_tts_stream_headers(is_shitou)
        tts_body = json.dumps(build_tts_stream_body(text, is_shitou))
        
        response = requests.post(url, stream=True, headers=tts_headers, data=tts_body)
        if response.status_code != 200:
            logging.error(f"TTS API请求失败: {response.status_code}")
            return
            
        for chunk in response.iter_lines():
            if chunk and chunk.startswith(b'data:'):
                try:
                    data = json.loads(chunk[5:])
                    if "data" in data and "extra_info" not in data:
                        if "audio" in data["data"]:
                            yield data["data"]['audio']
                except json.JSONDecodeError as e:
                    logging.error(f"解析TTS响应时出错: {e}")
                    continue
    except Exception as e:
        logging.error(f"TTS流处理时出错: {e}")
        raise

def load_prompts(file_path):
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            return file.read().splitlines()
    except Exception as e:
        logging.error(f"加载提词文件错误: {str(e)}")
        return []

def get_chat_history(session_id, is_shitou=True):
    histories = chat_histories_shitou if is_shitou else chat_histories_eureka
    if session_id not in histories:
        histories[session_id] = [
            {
                "role": "system",
                "content": "你是石头，一个热爱生物学的高中生。你总是喜欢向同学提出生物学相关的问题，引导他们一起思考和讨论。你的语气要活泼、友好，像一个真实的同龄人。记住你是同学而不是老师。" if is_shitou 
                else "你是尤里卡，一个AI学习助手。你的职责是在用户回答完石头同学的问题后，对用户的回答进行专业的点评和补充。注意：\n1. 你必须在用户回答了石头的问题后才能发言\n2. 在前两次对话中必须保持沉默\n3. 你是AI助手，不是学生，要用专业、客观的语气给出反馈\n4. 不要模仿石头的语气和身份，保持你作为AI助手的独特身份"
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
        # 修改判断条件：前两次对话时尤里卡保持沉默
        is_early_message = len(shitou_history) <= 5  # system + 2次对话(每次2条消息) = 5条消息
        
        # 为石头和尤里卡准备不同的输入
        combined_prompt_shitou = "\n".join(prompts_shitou) + "\n" + user_input
        
        def generate():
            try:
                # 生成石头的回复
                full_response_shitou = ""
                response_shitou, messages_shitou = generate_response_glm(session_id, combined_prompt_shitou, True)
                
                # 收集石头的完整响应
                for chunk in response_shitou:
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content is not None:
                            full_response_shitou += content
                            # 发送文本更新
                            yield f"data: {json.dumps({'text': content, 'full_response': full_response_shitou, 'agent': '石头'})}\n\n"
                
                # 石头的回复完成后，将完整文本转换为语音
                try:
                    audio_data = b""
                    for audio_chunk in call_tts_stream(full_response_shitou, True):
                        if audio_chunk:
                            try:
                                audio_hex = bytes.fromhex(audio_chunk)
                                audio_data += audio_hex
                            except ValueError as e:
                                logging.error(f"处理音频数据时出错: {e}")
                                continue
                    
                    # 如果成功获取到音频数据发送到前端
                    if audio_data:
                        import base64
                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                        yield f"data: {json.dumps({'audio': audio_base64, 'agent': '石头'})}\n\n"
                except Exception as e:
                    logging.error(f"处理语音时发生错误: {str(e)}")
                    logging.error("错误详情:", exc_info=True)
                
                # 更新石头的历史记录
                update_chat_history(session_id, "user", user_input, True)
                update_chat_history(session_id, "assistant", full_response_shitou, True)
                
                # 处理尤里卡的响应
                if not is_early_message:  # 只有在不是前两次对话时才生成尤里卡的响应
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
                    
                    # 尤里卡的回复完成后，将完整文本转换为语音
                    if full_response_eureka.strip():  # 确保有实际内容再转换
                        try:
                            audio_data = b""
                            for audio_chunk in call_tts_stream(full_response_eureka, False):  # False 表示使用尤里卡的配置
                                if audio_chunk:
                                    try:
                                        audio_hex = bytes.fromhex(audio_chunk)
                                        audio_data += audio_hex
                                    except ValueError as e:
                                        logging.error(f"处理尤里卡音频数据时出错: {e}")
                                        continue
                            
                            # 如果成功获取到音频数据，发送到前端
                            if audio_data:
                                import base64
                                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                                yield f"data: {json.dumps({'audio': audio_base64, 'agent': '尤里卡'})}\n\n"
                        except Exception as e:
                            logging.error(f"处理尤里卡语音时发生错误: {str(e)}")
                            logging.error("错误详情:", exc_info=True)
                    
                    # 更新尤里卡的响应到历史记录
                    update_chat_history(session_id, "assistant", full_response_eureka, False)
                else:
                    # 前两次对话只更新用户输入到尤里卡的历史记录
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
    clear_chat_histories()  # 在程序启动时清空聊天历史
    app.run(debug=True)
