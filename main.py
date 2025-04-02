import os
import sys
import time
import contextlib
import azure.cognitiveservices.speech as speechsdk
import httpx
from openai import OpenAI
import grpc
import numpy as np
import soundfile
import unreal
import asyncio
from websocket_server import websocket_server

# 导入Audio2Face的gRPC协议
import audio2face_pb2
import audio2face_pb2_grpc

# 导入讯飞语音评测模块
from speech_assessment import SpeechAssessment
from record_audio import record_audio

# =================================
# 配置部分
# =================================
# Azure配置
AZURE_SPEECH_KEY = "AhQ99tqLmu33mma84zXt6IESBhvCEXYnlHPqGHM5Mb8D4Oyu9tygJQQJ99BDAC3pKaRXJ3w3AAAYACOGYEtN"
AZURE_SPEECH_REGION = "eastasia"  #
AZURE_SPEECH_RECOGNITION_LANGUAGE = "zh-CN"  # 中文识别
AZURE_SPEECH_SYNTHESIS_VOICE_NAME = "zh-CN-XiaochenNeural"  # 中文女声

# OpenAI配置
OPENAI_API_KEY = "sk-0CqjAjsI5q8XWY5I73C1E1F51bC94a3fB10eEdFc9e407e4c"
OPENAI_MODEL = "gpt-4"  # 或 "gpt-3.5-turbo" 等

# Audio2Face配置
A2F_URL = "localhost:50051"  # Audio2Face的地址和端口
A2F_INSTANCE = "/World/audio2face/PlayerStreaming"  # A2F实例路径

# 讯飞语音评测配置
# XUNFEI_APP_ID = "350af4ae"
# XUNFEI_API_KEY = "61ec2f65d29033319c1c6c3cd34fc25d"
# XUNFEI_API_SECRET = "N2JmM2JjMGFjNmRlNDA3ODU1ZWYwNmNl"
XUNFEI_APP_ID = "5e11538f"
XUNFEI_API_KEY = "91205afe0d17e38c61be35fca346503c"
XUNFEI_API_SECRET = "ff446b96b01252f80331ae6e4c64984a"

# 输出音频文件路径
OUTPUT_WAV = r"E:\Research\Aphasia\Conversation\LLMResponse.wav"
USER_WAV = r"E:\Research\Aphasia\Conversation\UserSpeech.wav"  

# =================================
# WebSocket配置
# =================================
WS_HOST = "localhost"
WS_PORT = 8765

# =================================
# 1. 语音识别模块 (STT) - 使用Azure API
# =================================
class SpeechRecognizer:
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION
        )
        self.speech_config.speech_recognition_language = AZURE_SPEECH_RECOGNITION_LANGUAGE
        self.audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        
    def recognize_from_microphone(self, save_audio=False):
        """从麦克风获取语音并识别为文本，可选择保存音频"""
        
        # 创建语音识别器
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=self.audio_config
        )
        
        # 如果需要保存音频，设置音频保存配置
        if save_audio:
            audio_output_config = speechsdk.audio.AudioOutputConfig(filename=USER_WAV)
            audio_input_stream = speechsdk.AudioInputStream()
            pull_input_stream = speechsdk.audio.PullAudioInputStream(
                callback=audio_input_stream.read,
                stream_format=speechsdk.audio.AudioStreamFormat(
                    samples_per_second=16000,
                    bits_per_sample=16,
                    channels=1
                )
            )
            # 创建录音器
            audio_input_config = speechsdk.audio.AudioConfig(stream=pull_input_stream)
            
        print("请说话...")
        result = recognizer.recognize_once_async().get()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return True, result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print(f"未能识别语音: {result.no_match_details}")
            return False, "无法识别您的语音，请重试。"
        elif result.reason == speechsdk.ResultReason.Canceled:
            print(f"语音识别已取消: {result.cancellation_details.reason}")
            if result.cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"错误详情: {result.cancellation_details.error_details}")
            return False, "语音识别被取消，请重试。"
        
        return False, "识别失败，请重试。"
    
    # def recognize_and_save(self):
    #     """识别语音并保存音频文件用于后续评测"""
    #     # 使用Azure的AudioConfig录制音频同时进行识别
    #     audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    #     speech_recognizer = speechsdk.SpeechRecognizer(
    #         speech_config=self.speech_config, 
    #         audio_config=audio_config
    #     )
        
    #     # 使用单独的录音配置来保存用户语音
    #     audio_output_config = speechsdk.audio.AudioOutputConfig(filename=USER_WAV)
    #     audio_recorder = speechsdk.audio.AudioConfig(filename=USER_WAV)
        
    #     print("请说话...(录音将保存用于评测)")
    #     result = speech_recognizer.recognize_once_async().get()
        
    #     if result.reason == speechsdk.ResultReason.RecognizedSpeech:
    #         print(f"识别到: {result.text}")
    #         return True, result.text
    #     else:
    #         # 处理识别失败情况
    #         return False, "语音识别失败，无法进行评测。"

    def recognize_and_save(self, duration=5.0):
        """使用直接录音模块识别语音并保存音频文件用于评测"""
        print(f"请准备朗读文本...")

        # 文件路径
        output_file = USER_WAV

        # 1. 直接使用record_audio模块录音
        success = record_audio(output_file, duration=duration)

        if not success:
            print("录音失败，无法进行评测")
            return False, "录音失败，请检查麦克风设置"

        # 2. 使用Azure进行语音识别
        try:
            # 从文件中识别文本
            audio_config = speechsdk.audio.AudioConfig(filename=output_file)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            print("正在识别录制的语音...")
            result = speech_recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text
                # print(f"识别到: {recognized_text}")
                return True, recognized_text
            else:
                print("语音已录制，但未能识别文本")
                # 录音成功但识别失败，仍然可以进行评测
                return True, "语音已录制，但未识别到文本"
        except Exception as e:
            print(f"识别过程出错: {e}")
            # 录音成功但识别过程出错，仍然可以进行评测
            return True, "语音已录制，但识别过程出错"


# =================================
# 2. LLM文本处理模块 - 使用OpenAI API
# =================================
class LLMProcessor:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.xty.app/v1",
            api_key=OPENAI_API_KEY,
            http_client=httpx.Client(
                base_url="https://api.xty.app/v1",
                follow_redirects=True,
            ),
        )
        # 设置人物角色和背景提示
        self.system_prompt = """
            你是一个数字言语治疗师，具备失语症康复训练的专业知识，擅长与语言障碍患者沟通。
            你的回答要温和、简洁，使用患者容易理解的词汇，避免专业术语和复杂表达。
            请在语义上给予积极鼓励，每次回复控制在50字以内，以便语音合成。
        """
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试延迟（秒）
        
    def _make_api_call(self, messages, max_tokens=150):
        """执行API调用，包含重试机制"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens
                )
                return response
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"API调用失败，{self.retry_delay}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    print(f"错误信息: {str(e)}")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"API调用最终失败: {str(e)}")
                    raise
        
    async def send_ws_message(self, message_type, content):
        """发送WebSocket消息"""
        message = {
            'type': message_type,
            'content': content
        }
        await websocket_server.broadcast(message)
        
    def process_text(self, text):
        """处理用户输入文本，返回AI回答"""
        # 添加用户消息
        self.messages.append({"role": "user", "content": text})
        
        try:
            # 发送用户输入到UE
            asyncio.create_task(self.send_ws_message('user_input', text))
            
            # 调用OpenAI API获取回复
            response = self._make_api_call(self.messages)
            
            # 获取回复内容
            reply = response.choices[0].message.content
            
            # 发送AI回复到UE
            asyncio.create_task(self.send_ws_message('ai_response', reply))
            
            # 将回复添加到消息历史
            self.messages.append({"role": "assistant", "content": reply})
            
            # 如果消息历史过长，移除最早的用户和助手消息以节省Token
            if len(self.messages) > 10:  # 保留系统提示和最近的对话
                self.messages = self.messages[:1] + self.messages[-9:]
                
            return reply
            
        except Exception as e:
            print(f"OpenAI API调用失败: {e}")
            return "抱歉，我暂时无法回答您的问题，请稍后再试。"
            
    def process_assessment_result(self, text, assessment_result):
        """处理评测结果，生成反馈意见"""
        # 添加专门的评测结果处理提示
        assessment_prompt = f"""
            你是一位数字言语治疗师，正在帮助一位患有失语症的患者进行发音训练。
            患者刚刚朗读了："{text}"。
            以下是语音评测系统的结果（XML格式）：
            {assessment_result}

            请根据这个评测结果，用亲切、自然的语言给出反馈。
            可以从"发音是否准确"、"语速流畅度"、"音调和节奏"等角度出发。
            请尽量使用口语化、生活化的表达，比如：
            "你刚才那个'喝'字有点轻了，下次可以更用力一点。"

            避免列出1、2、3点，不要使用"发音问题"、"改进建议"等标签，而是像一位真正的语言康复专家一样温柔地鼓励患者。
            回答尽量控制在80字以内，便于语音合成。
        """
        
        # 添加用户消息
        self.messages.append({"role": "user", "content": assessment_prompt})
        
        try:
            # 调用OpenAI API获取回复
            # response = self.client.chat.completions.create(
            #     model=OPENAI_MODEL,
            #     messages=self.messages,
            #     temperature=0.7,
            #     max_tokens=150
            # )
            response = self._make_api_call(self.messages, max_tokens=250)
            
            # 获取回复内容
            reply = response.choices[0].message.content
            
            # 将回复添加到消息历史
            self.messages.append({"role": "assistant", "content": reply})
            
            # 如果消息历史过长，移除最早的消息以节省Token
            if len(self.messages) > 12:
                self.messages = self.messages[:1] + self.messages[-11:]
                
            return reply
            
        except Exception as e:
            print(f"OpenAI API调用失败: {e}")
            # 返回一个友好的错误提示
            return "抱歉，我现在无法分析评测结果，请稍后再试。"


# =================================
# 3. 文本转语音模块 (TTS) - 使用Azure API
# =================================
class TextToSpeech:
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION
        )
        self.speech_config.speech_synthesis_voice_name = AZURE_SPEECH_SYNTHESIS_VOICE_NAME
        
    def synthesize_speech(self, text, output_file):
        """将文本转换为语音并保存为WAV文件"""
        try:
            # 创建音频配置
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
            
            # 创建语音合成器
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            # 合成语音
            result = speech_synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"语音合成完成, 保存至 {output_file}")
                return True
            elif result.reason == speechsdk.ResultReason.Canceled:
                print(f"语音合成取消: {result.cancellation_details.reason}")
                if result.cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"错误详情: {result.cancellation_details.error_details}")
                return False
            return False
        except Exception as e:
            print(f"语音合成出错: {str(e)}")
            return False


# =================================
# 4. Audio2Face连接模块
# =================================
class Audio2FaceConnector:
    def __init__(self, url="localhost:50051"):
        self.url = url
        
    def push_audio_file(self, audio_file_path, instance_name):
        """将音频文件推送到Audio2Face"""
        try:
            # 读取WAV文件
            data, samplerate = soundfile.read(audio_file_path, dtype="float32")
            
            # 确保为单声道
            if len(data.shape) > 1:
                data = np.average(data, axis=1)
                
            # 创建gRPC通道
            with grpc.insecure_channel(self.url) as channel:
                stub = audio2face_pb2_grpc.Audio2FaceStub(channel)
                
                # 创建请求
                request = audio2face_pb2.PushAudioRequest()
                request.audio_data = data.astype(np.float32).tobytes()
                request.samplerate = samplerate
                request.instance_name = instance_name
                request.block_until_playback_is_finished = True
                
                print(f"正在发送音频到Audio2Face: {instance_name}")
                # 发送请求
                response = stub.PushAudio(request)
                
                if response.success:
                    print("音频发送成功")
                    return True
                else:
                    print(f"音频发送失败: {response.message}")
                    return False
                    
        except Exception as e:
            print(f"与Audio2Face连接错误: {str(e)}")
            return False
            
    def push_audio_stream(self, audio_file_path, instance_name):
        """将音频文件以流的方式推送到Audio2Face"""
        try:
            # 读取WAV文件
            data, samplerate = soundfile.read(audio_file_path, dtype="float32")
            
            # 确保为单声道
            if len(data.shape) > 1:
                data = np.average(data, axis=1)
                
            # 设置流块大小
            chunk_size = samplerate // 10  # 每块约100ms的音频
            sleep_between_chunks = 0.04  # 每块之间的延迟
                
            # 创建gRPC通道
            with grpc.insecure_channel(self.url) as channel:
                stub = audio2face_pb2_grpc.Audio2FaceStub(channel)
                
                # 创建生成器函数
                def make_generator():
                    # 首先发送开始标记
                    start_marker = audio2face_pb2.PushAudioRequestStart(
                        samplerate=samplerate,
                        instance_name=instance_name,
                        block_until_playback_is_finished=True
                    )
                    yield audio2face_pb2.PushAudioStreamRequest(start_marker=start_marker)
                    
                    # 然后发送音频数据块
                    for i in range(len(data) // chunk_size + 1):
                        time.sleep(sleep_between_chunks)
                        chunk = data[i * chunk_size : i * chunk_size + chunk_size]
                        yield audio2face_pb2.PushAudioStreamRequest(
                            audio_data=chunk.astype(np.float32).tobytes()
                        )
                
                # 创建生成器并发送请求
                request_generator = make_generator()
                print(f"正在流式发送音频到Audio2Face: {instance_name}")
                response = stub.PushAudioStream(request_generator)
                
                if response.success:
                    print("音频流发送成功")
                    return True
                else:
                    print(f"音频流发送失败: {response.message}")
                    return False
                    
        except Exception as e:
            print(f"与Audio2Face流连接错误: {str(e)}")
            return False


# =================================
# 5. 语音评测模块 - 使用讯飞API
# =================================
class SpeechAssessmentModule:
    def __init__(self):
        self.assessor = SpeechAssessment(
            app_id=XUNFEI_APP_ID,
            api_key=XUNFEI_API_KEY, 
            api_secret=XUNFEI_API_SECRET,
            ise_type="cn"  # 中文评测
        )
        self.llm_processor = LLMProcessor()  # 添加LLM处理器
        
    async def send_assessment_result(self, scores, feedback):
        """发送评测结果到UE"""
        message = {
            'type': 'assessment_result',
            'scores': scores,
            'feedback': feedback
        }
        await websocket_server.broadcast(message)
        
    def assess_speech(self, text, audio_file, category=None):
        """
        评测用户语音
        
        参数:
            text (str): 标准文本
            audio_file (str): 用户语音文件路径
            category (str, optional): 评测题型，如果不指定则使用默认值
            
        返回:
            str: 评测结果XML
        """
        try:
            print(f"开始评测用户语音: {text}")
            
            # 设置评测题型
            if category:
                self.assessor.set_category(category)
            else:
                # 默认使用句子朗读题型
                self.assessor.set_category("read_sentence")
            
            # 检查音频文件是否存在且非空
            if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
                print(f"错误: 音频文件 {audio_file} 不存在或为空")
                return None
            
            # 开始评测，设置超时时间为15秒
            result = self.assessor.assess(text, audio_file, timeout=15)
            
            if result:
                # 提取评分
                scores = self.assessor.extract_scores(result)
                
                # 获取LLM反馈
                feedback = self.llm_processor.process_assessment_result(text, result)  
                
                # 发送评测结果到UE
                asyncio.create_task(self.send_assessment_result(scores, feedback))
                
                return result
            else:
                print("评测失败或超时")
                return None
                
        except Exception as e:
            print(f"语音评测出错: {str(e)}")
            return None
    
# =================================
# 辅助函数
# =================================
@contextlib.contextmanager
def ignore_stderr():
    """临时忽略标准错误输出的上下文管理器"""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# =================================
# 主程序
# =================================
async def main_async():
    """异步主程序函数"""
    # 启动WebSocket服务器
    await websocket_server.start()
    
    try:
        # 检查是否提供了退出命令
        def check_exit(text):
            exit_words = ["退出", "再见", "结束", "拜拜", "关闭", "停止"]
            return any(word in text for word in exit_words)

        # 初始化各个模块
        print("正在初始化AI数字人...")
        
        # 初始化语音识别
        speech_recognizer = SpeechRecognizer()
        
        # 初始化LLM处理器
        llm_processor = LLMProcessor()
        
        # 初始化文本转语音
        text_to_speech = TextToSpeech()
        
        # 初始化Audio2Face连接器
        a2f_connector = Audio2FaceConnector(url=A2F_URL)
        
        # 初始化语音评测模块
        speech_assessment = SpeechAssessmentModule()
        
        print("AI数字人已准备就绪，请开始对话...")

        # 主循环
        while True:
            try:
                # 默认模式 - 正常对话
                print("\n请选择: 1.正常对话 2.语音评测 3.退出")
                choice = input("请输入选项编号: ")
                
                if choice == "3":
                    print("感谢使用，再见！")
                    break
                    
                elif choice == "2":
                    # 语音评测模式
                    print("\n进入语音评测模式")
                    print("请输入标准文本，按回车确认:")
                    standard_text = input()
                    
                    if not standard_text:
                        print("未输入标准文本，返回主菜单。")
                        continue
                    
                    print(f"请朗读: \"{standard_text}\"")
                    # 识别并保存语音
                    success, recognized_text = speech_recognizer.recognize_and_save()
                    
                    if not success:
                        print("语音识别失败，返回主菜单。")
                        continue
                        
                    print(f"识别结果: {recognized_text}")
                    
                    # 进行语音评测
                    xml_result = speech_assessment.assess_speech(standard_text, USER_WAV)
                    
                    if xml_result:
                        # 提取评分
                        scores = speech_assessment.assessor.extract_scores(xml_result)
                        
                        # 显示评测结果
                        print("\n===== 语音评测结果 =====")
                        print(f"总分: {scores.get('total_score', 0):.2f}")
                        print(f"流畅度: {scores.get('fluency_score', 0):.2f}")
                        print(f"完整度: {scores.get('integrity_score', 0):.2f}")
                        print(f"发音分: {scores.get('phone_score', 0):.2f}")
                        print(f"声调分: {scores.get('tone_score', 0):.2f}")
                        
                        # LLM分析评测结果，给出改进建议
                        feedback = llm_processor.process_assessment_result(standard_text, xml_result)
                        
                        # 输出改进建议
                        print("\n===== 改进建议 =====")
                        print(feedback)
                        
                        # 语音合成并播放改进建议
                        tts_success = text_to_speech.synthesize_speech(
                            text=feedback,
                            output_file=OUTPUT_WAV
                        )
                        
                        if tts_success:
                            # 推送到Audio2Face
                            a2f_connector.push_audio_file(
                                audio_file_path=OUTPUT_WAV,
                                instance_name=A2F_INSTANCE
                            )
                    else:
                        print("评测失败，无结果返回。")
                    
                else:  # 默认为正常对话模式
                    # 1. 语音识别
                    with ignore_stderr():
                        success, recognized_text = speech_recognizer.recognize_from_microphone()
                    
                    if not success or not recognized_text:
                        print("语音识别失败，请重试...")
                        continue
                        
                    # 检查是否要退出
                    if check_exit(recognized_text):
                        print("感谢使用，再见！")
                        break
                        
                    # 2. LLM处理
                    response_text = llm_processor.process_text(recognized_text)
                    print(f"AI回答: {response_text}")
                    
                    # 3. 文本转语音
                    tts_success = text_to_speech.synthesize_speech(
                        text=response_text,
                        output_file=OUTPUT_WAV
                    )
                    
                    if not tts_success:
                        print("语音合成失败，跳过...")
                        continue
                        
                    # 4. 推送到Audio2Face
                    a2f_connector.push_audio_file(
                        audio_file_path=OUTPUT_WAV,
                        instance_name=A2F_INSTANCE
                    )
                    
                    # 短暂等待，准备下一轮对话
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n程序被用户中断")
                break
            except Exception as e:
                print(f"发生错误: {str(e)}")
                continue
                
    finally:
        # 停止WebSocket服务器
        await websocket_server.stop()
        
    print("AI数字人程序已结束")

def main():
    """主程序入口"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()