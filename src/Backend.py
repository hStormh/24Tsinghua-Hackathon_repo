from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import json
import os
import logging
from zhipuai import ZhipuAI

app = Flask(__name__)
CORS(app, supports_credentials=True)

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# API配置
ZHIPU_API_KEY = "cbf04086856f4c44d07d5434454d5eeb.kZbVTb99QPLqbMuG"
client = ZhipuAI(api_key=ZHIPU_API_KEY)

# 提示词文件路径
PROMPTS_FILE_SHITOU = "../prompts/Prompt_button.txt"  # 石头的提示词
PROMPTS_FILE_EUREKA = "../prompts/Prompt_Eureca.txt"  # 尤里卡的提示词

# 存储两个智能体的对话历史
chat_histories_shitou = {}
chat_histories_eureka = {}

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
                "role": "system",
                "content": "你是石头，一个专业的生物教师助手，你需要引导学生思考和回答问题" if is_shitou 
                else "你是尤里卡，一个助教。你的任务是在学生回答石头老师的问题后，对学生的回答给出及时反馈。如果学生还没有回答问题，你应该保持沉默。"
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
                response_shitou, messages_shitou = generate_response_glm(session_id, combined_prompt_shitou, True)
                
                # 收集石头的完整响应
                for chunk in response_shitou:
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content is not None:
                            full_response_shitou += content
                            yield f"data: {json.dumps({'text': content, 'full_response': full_response_shitou, 'agent': '石头'})}\n\n"
                
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
