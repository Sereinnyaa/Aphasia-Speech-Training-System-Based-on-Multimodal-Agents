import os
import sys
import time
import json
import logging
import asyncio
import random
from datetime import datetime
from record_audio import record_audio
from main import LLMProcessor, TextToSpeech, Audio2FaceConnector, SpeechRecognizer, SpeechAssessmentModule

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 终端颜色样式
class Colors:
    SYSTEM = '\033[94m'     # 蓝色
    USER = '\033[92m'       # 绿色
    AGENT = '\033[95m'      # 紫色
    RESET = '\033[0m'

# 数据文件路径
PATIENT_DATA_FILE = r"E:\Research\Aphasia\UE_project\Demo_5_3\Content\Python\patient_data.json"
TRAINING_HISTORY_FILE = r"E:\Research\Aphasia\UE_project\Demo_5_3\Content\Python\training_history.json"

# 训练题库
TRAINING_QUESTIONS = {
    "read_syllable": [
        "ba", "ma", "fa", "da", "ta", "na", "la", "ga", "ka", "ha",
        "zha", "cha", "sha", "ra", "za", "ca", "sa", "ya", "wa"
    ],
    "read_word": [
        "爸爸", "妈妈", "吃饭", "睡觉", "工作", "学习", "医院", "医生", "护士",
        "朋友", "家庭", "生活", "快乐", "健康", "幸福", "美好", "温暖", "阳光"
    ],
    "read_sentence": [
        "今天天气真不错，阳光明媚。",
        "我喜欢吃苹果和香蕉。",
        "医生建议我每天多运动。",
        "我的家人很关心我的康复。",
        "和朋友聊天让我心情愉快。",
        "医院里的护士都很耐心。",
        "我希望早日恢复健康。",
        "生活中有很多美好的事情。"
    ]
    # ,
    # "read_chapter": [
    #     "春天来了，天气变暖了。小鸟在树上唱歌，花儿在风中跳舞。",
    #     "小明去医院做康复训练。医生和护士都很耐心地指导他。",
    #     "我的康复之路虽然漫长，但我每天都在进步。家人和朋友的支持让我充满信心。"
    # ]
}

class DemoSystem:
    def __init__(self):
        self.patient_data = self.load_patient_data()
        self.training_history = self.load_training_history()
        self.llm_processor = LLMProcessor()
        self.text_to_speech = TextToSpeech()
        self.audio2face = Audio2FaceConnector()
        self.speech_recognizer = SpeechRecognizer()
        self.speech_assessment = SpeechAssessmentModule()
        self.is_first_session = True

    def load_patient_data(self):
        try:
            with open(PATIENT_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("未找到患者数据文件，使用默认信息")
            return {
                "name": "张先生",
                "age": 45,
                "diagnosis": "运动性失语症",
                "severity": "中度",
                "symptoms": ["发音不清晰", "语速较慢", "词汇量减少"]
            }

    def load_training_history(self):
        try:
            with open(TRAINING_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("未找到训练历史文件，使用默认信息")
            return {
                "sessions": [
                    {
                        "date": "2024-03-24",
                        "exercises": [
                            {
                                "type": "句子朗读",
                                "sentence": "我喜欢吃苹果",
                                "score": 90,
                                "feedback": "语速适中，语调自然"
                            }
                        ]
                    }
                ]
            }

    def get_random_exercise(self):
        """随机选择训练题型和题目"""
        exercise_type = random.choice(list(TRAINING_QUESTIONS.keys()))
        question = random.choice(TRAINING_QUESTIONS[exercise_type])
        
        # 根据题型设置不同的提示语
        prompts = {
            "read_syllable": "请朗读以下音节",
            "read_word": "请朗读以下词语",
            "read_sentence": "请朗读以下句子",
            "read_chapter": "请朗读以下短文"
        }
        
        return {
            "type": exercise_type,
            "question": question,
            "prompt": prompts[exercise_type]
        }

    async def play_audio(self, text, output_file="response.wav"):
        """合成语音并发送到Audio2Face"""
        if self.text_to_speech.synthesize_speech(text, output_file):
            self.audio2face.push_audio_file(output_file, "/World/audio2face/PlayerStreaming")

    async def say_as_agent(self, text):
        """打印并播报数字治疗师的语音"""
        print(f"{Colors.AGENT}数字言语治疗师：{text}{Colors.RESET}")
        await self.play_audio(text)

    async def say_as_system(self, text):
        print(f"{Colors.SYSTEM}系统提示：{text}{Colors.RESET}")
        await self.play_audio(text)

    async def get_user_input(self):
        """录音并语音识别"""
        logger.info("等待用户语音输入...")
        success, recognized_text = self.speech_recognizer.recognize_from_microphone()
        if not success:
            logger.error("语音识别失败")
            return None
        print(f"{Colors.USER}用户：{recognized_text}{Colors.RESET}")
        return recognized_text

    async def run_training_session(self):
        """运行一次训练会话"""
        try:
            # 获取随机训练题目
            exercise = self.get_random_exercise()
            await self.say_as_agent(f"{exercise['prompt']}：{exercise['question']}")
            await self.say_as_agent('请说"开始"来确认开始训练，或说"退出"结束训练。')

            user_input = await self.get_user_input()
            if not user_input or "退出" in user_input:
                # await self.say_as_agent("好的，我们下次再见！")
                return False
            if "开始" not in user_input:
                await self.say_as_agent('抱歉，我没有听清楚，请说"开始"或"退出"。')
                return True

            await self.say_as_agent("请准备朗读...")
            # time.sleep(2)

            success = record_audio("user_speech.wav", duration=5.0)
            if not success:
                await self.say_as_agent("录音失败，请检查麦克风或稍后重试。")
                return True

            await self.say_as_agent("正在评估您的发音，请稍候...")

            # 设置评测题型
            self.speech_assessment.assessor.set_category(exercise['type'])
            
            xml_result = self.speech_assessment.assess_speech(exercise['question'], "user_speech.wav")
            if xml_result:
                scores = self.speech_assessment.assessor.extract_scores(xml_result)
                feedback = self.llm_processor.process_assessment_result(exercise['question'], xml_result)

                result_msg = (
                    f"评估结果：\n"
                    f"总分：{scores['total_score']:.2f}  "
                    f"流畅度：{scores['fluency_score']:.2f}  "
                    f"完整度：{scores['integrity_score']:.2f}  "
                    f"发音：{scores['phone_score']:.2f}  "
                    f"声调：{scores['tone_score']:.2f}\n"
                )
                print(f"{Colors.SYSTEM}{result_msg}{Colors.RESET}")

                await self.say_as_agent(feedback)
                await self.say_as_agent("您想继续训练吗？请说“是”或“否”。")
                user_input = await self.get_user_input()

                return user_input and "是" in user_input
            else:
                await self.say_as_agent("评估失败，请稍后重试。")
                return True

        except Exception as e:
            logger.error(f"训练过程出错: {e}")
            await self.say_as_agent("系统发生错误，请重试。")
            return False

    async def run_demo(self):
        """运行完整的演示流程"""
        try:
            print(f"{Colors.SYSTEM}=== 系统启动 ==={Colors.RESET}")
            
            if self.is_first_session:
                last_session = self.training_history["sessions"][-1]
                last_exercise = last_session["exercises"][0]

                greeting = (
                    f"{self.patient_data['name']}您好！根据您的病历和上次训练情况，"
                    f"今天我们将进行语音训练。"
                    f"上次训练您的得分是{last_exercise['score']}分，"
                    f"评语是：{last_exercise['feedback']}。"
                    f"让我们开始今天的训练吧！"
                )
                await self.say_as_agent(greeting)
                self.is_first_session = False

            while True:
                should_continue = await self.run_training_session()
                if not should_continue:
                    await self.say_as_agent("好的，今天的训练到此结束，再见！")
                    break

        except Exception as e:
            logger.error(f"演示过程出错: {e}")
            await self.say_as_agent("系统发生错误，请重试。")

async def main():
    demo = DemoSystem()
    await demo.run_demo()
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
