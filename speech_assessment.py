import os
import json
import time
import base64
import datetime
import hashlib
import hmac
import urllib.parse
import threading
import websocket
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime


class SpeechAssessment:
    """讯飞语音评测API接口封装"""

    def __init__(self, app_id, api_key, api_secret, ise_type="cn"):
        """
        初始化讯飞语音评测

        参数:
            app_id (str): 讯飞开放平台申请的APPID
            api_key (str): 接口密钥APIKey
            api_secret (str): 接口密钥APISecret
            ise_type (str): 评测语言类型，可选值：'cn'(中文),'en'(英文)
        """
        self.APPID = app_id
        self.APIKey = api_key
        self.APISecret = api_secret
        self.Host = "ise-api.xfyun.cn"
        self.RequestLine = "GET /v2/open-ise HTTP/1.1"

        # 根据语言类型设置默认参数
        self.ise_type = ise_type
        if ise_type == "cn":
            self.ent = "cn_vip"  # 中文评测
            self.category = "read_sentence"  # 默认中文句子朗读
        else:
            self.ent = "en_vip"  # 英文评测
            self.category = "read_sentence"  # 默认英文句子朗读

        # WebSocket连接和结果存储
        self.ws = None
        self.assessment_results = []
        self.is_finished = False
        self.final_result = None

    def create_url(self):
        """
        生成鉴权URL

        返回:
            str: 完整的WebSocket连接URL
        """
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接signature原始字段
        signature_origin = f"host: {self.Host}\ndate: {date}\n{self.RequestLine}"

        # 使用hmac-sha256算法结合APISecret对signature_origin签名
        signature_sha = hmac.new(
            self.APISecret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        # Base64编码获得signature
        signature = base64.b64encode(signature_sha).decode('utf-8')

        # 拼接authorization_origin
        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'

        # Base64编码获得authorization
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

        # 构建完整的url
        url = f"wss://{self.Host}/v2/open-ise"
        url = f"{url}?authorization={authorization}&date={urllib.parse.quote(date)}&host={self.Host}"

        return url

    def prepare_text(self, text, text_format="text"):
        """
        准备评测文本

        参数:
            text (str): 要评测的文本内容
            text_format (str): 文本格式，'text'为纯文本，'phoneme'为带音素标注文本

        返回:
            str: 处理后的文本
        """
        # 添加UTF-8 BOM头
        text_with_bom = '\uFEFF' + text

        # 如果是英文且为句子或篇章，需要添加特定格式
        if self.ise_type == "en" and self.category in ["read_sentence", "read_chapter"]:
            if text_format == "text":
                return text_with_bom
            else:
                return text_with_bom

        # 如果是英文单词，需要添加特定格式
        elif self.ise_type == "en" and self.category == "read_word":
            if text_format == "text":
                words = text.split()
                return text_with_bom
            else:
                return text_with_bom

        # 中文评测
        else:
            return text_with_bom

    def on_message(self, ws, message):
        """
        处理WebSocket接收到的消息

        参数:
            ws: WebSocket对象
            message (str): 接收到的消息
        """
        message = json.loads(message)
        code = message["code"]

        if code != 0:
            print(f"评测失败，错误码：{code}，错误信息：{message['message']}")
            ws.close()
            return

        data = message["data"]
        status = data["status"]

        if status == 2:  # 最终结果
            self.is_finished = True
            result_data = data["data"]
            # Base64解码评测结果
            xml_result = base64.b64decode(result_data).decode('utf-8')
            self.final_result = xml_result
            print("评测完成")

        self.assessment_results.append(message)

    def on_error(self, ws, error):
        """处理WebSocket错误"""
        print(f"WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket关闭"""
        print(f"WebSocket关闭: {close_status_code} - {close_msg}")

    def on_open(self, ws):
        """处理WebSocket连接打开后的操作"""
        # print("WebSocket连接已建立，正在发送评测参数...")

        def send_data():
            """发送数据的线程函数"""
            # 准备第一帧参数
            first_frame = {
                "common": {
                    "app_id": self.APPID
                },
                "business": {
                    "category": self.category,
                    "rstcd": "utf8",
                    "aue": "raw",
                    "auf": "audio/L16;rate=16000",
                    "sub": "ise",
                    "ent": self.ent,
                    "cmd": "ssb",
                    "text": self.assessment_text,
                    "tte": "utf-8",
                    "ttp_skip": True,
                    "extra_ability": "multi_dimension"
                },
                "data": {
                    "status": 0
                }
            }
            ws.send(json.dumps(first_frame))

            # 读取音频文件并分帧发送
            try:
                with open(self.audio_file, 'rb') as f:
                    audio_data = f.read()

                # 分帧处理
                frame_size = 1280  # 每帧音频大小，建议每40ms发送1280B
                frames = [audio_data[i:i + frame_size] for i in range(0, len(audio_data), frame_size)]

                # 发送第一帧音频
                first_audio_frame = {
                    "business": {
                        "cmd": "auw",
                        "aus": 1,
                    },
                    "data": {
                        "status": 1,
                        "data": base64.b64encode(frames[0]).decode('utf-8')
                    }
                }
                ws.send(json.dumps(first_audio_frame))
                time.sleep(0.04)  # 40ms间隔

                # 发送中间帧
                for i in range(1, len(frames) - 1):
                    mid_frame = {
                        "business": {
                            "cmd": "auw",
                            "aus": 2,
                        },
                        "data": {
                            "status": 1,
                            "data": base64.b64encode(frames[i]).decode('utf-8')
                        }
                    }
                    ws.send(json.dumps(mid_frame))
                    time.sleep(0.04)  # 40ms间隔

                # 发送最后一帧
                last_frame = {
                    "business": {
                        "cmd": "auw",
                        "aus": 4,
                    },
                    "data": {
                        "status": 2,
                        "data": base64.b64encode(frames[-1]).decode('utf-8')
                    }
                }
                ws.send(json.dumps(last_frame))

                print("音频数据发送完成，等待评测结果...")

            except Exception as e:
                print(f"发送音频数据时出错: {e}")
                ws.close()

        # 启动发送线程
        threading.Thread(target=send_data).start()

    def assess(self, text, audio_file, category=None, timeout=30):
        """
        进行语音评测

        参数:
            text (str): 评测文本内容
            audio_file (str): 音频文件路径
            category (str, optional): 评测题型，如果不指定则使用默认值
            timeout (int): 评测超时时间（秒）

        返回:
            dict: 评测结果
        """
        if category:
            self.category = category

        self.assessment_text = self.prepare_text(text)
        self.audio_file = audio_file

        # 重置结果
        self.assessment_results = []
        self.is_finished = False
        self.final_result = None

        # 创建URL
        url = self.create_url()

        # 建立WebSocket连接
        websocket.enableTrace(False)  # 启用跟踪以便调试
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        # 启动WebSocket连接线程
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        # 等待评测完成或超时
        start_time = time.time()
        while not self.is_finished and time.time() - start_time < timeout:
            time.sleep(0.1)

        # 关闭连接
        if self.ws.sock and self.ws.sock.connected:
            self.ws.close()

        if not self.is_finished:
            print(f"评测超时（{timeout}秒）")
            return None

        return self.final_result

    def extract_scores(self, xml_result):
        """
        从XML结果中提取主要评分
        
        参数:
            xml_result (str): XML格式的评测结果
            
        返回:
            dict: 包含主要评分的字典
        """
        if not xml_result:
            print("警告: 无评测结果可供解析")
            return {
                "total_score": 0,
                "fluency_score": 0,
                "integrity_score": 0,
                "phone_score": 0,
                "tone_score": 0,
                "error_info": "评测失败，无结果"
            }
            
        try:
            import xml.etree.ElementTree as ET
            
            # 使用XML库进行解析
            root = ET.fromstring(xml_result)
            scores = {}
            
            # 查找以下标签体系，在不同版本可能标签略有不同：
            # <xml_result>
            #  <read_sentence>
            #    <rec_paper>
            #     <read_sentence total_score="87.315392" ...>
            #       <sentence content="标准文本" total_score="87.315392" ...>
            #         <word>...</word>
            #       </sentence>
            #     </read_sentence>
            #   </rec_paper>
            # </read_sentence>
            # </xml_result>
            
            # 可能的总分位置
            total_score_xpath = [
                ".//read_sentence",
                ".//read_sentence/rec_paper/read_sentence",
                ".//sentence",
                ".//rec_paper/read_sentence"
            ]
            
            # 尝试从可能位置获取总分
            for xpath in total_score_xpath:
                element = root.find(xpath)
                if element is not None and "total_score" in element.attrib:
                    scores["total_score"] = float(element.attrib["total_score"])
                    # print(f"从 {xpath} 找到总分: {scores['total_score']}")
                    
                    # 可能同时包含其他分数
                    if "fluency_score" in element.attrib:
                        scores["fluency_score"] = float(element.attrib["fluency_score"])
                    if "integrity_score" in element.attrib:
                        scores["integrity_score"] = float(element.attrib["integrity_score"])
                    if "phone_score" in element.attrib:
                        scores["phone_score"] = float(element.attrib["phone_score"])
                    if "tone_score" in element.attrib:
                        scores["tone_score"] = float(element.attrib["tone_score"])
                    break
            
            # 如果没找到总分，尝试查找具体的分数项
            if "total_score" not in scores:
                # 查找分项评分
                fluency = root.find(".//fluency") or root.find(".//fluency_score")
                if fluency is not None:
                    if fluency.text:
                        scores["fluency_score"] = float(fluency.text)
                    elif "value" in fluency.attrib:
                        scores["fluency_score"] = float(fluency.attrib["value"])
                
                integrity = root.find(".//integrity") or root.find(".//integrity_score")
                if integrity is not None:
                    if integrity.text:
                        scores["integrity_score"] = float(integrity.text)
                    elif "value" in integrity.attrib:
                        scores["integrity_score"] = float(integrity.attrib["value"])
                
                phone = root.find(".//phone") or root.find(".//phone_score")
                if phone is not None:
                    if phone.text:
                        scores["phone_score"] = float(phone.text)
                    elif "value" in phone.attrib:
                        scores["phone_score"] = float(phone.attrib["value"])
                
                tone = root.find(".//tone") or root.find(".//tone_score")
                if tone is not None:
                    if tone.text:
                        scores["tone_score"] = float(tone.text)
                    elif "value" in tone.attrib:
                        scores["tone_score"] = float(tone.attrib["value"])
                
                # 如果找到了分项但没有总分，可以计算平均分作为总分
                if any(key in scores for key in ["fluency_score", "integrity_score", "phone_score", "tone_score"]):
                    count = 0
                    sum_score = 0
                    for key in ["fluency_score", "integrity_score", "phone_score", "tone_score"]:
                        if key in scores:
                            sum_score += scores[key]
                            count += 1
                    if count > 0:
                        scores["total_score"] = sum_score / count
                        print(f"从分项平均值计算总分: {scores['total_score']}")
            
            # 如果以上方法都没找到评分，尝试直接解析XML字符串
            if not scores:
                print("尝试直接解析XML字符串...")
                # 提取总分
                if 'total_score="' in xml_result:
                    try:
                        total_score = xml_result.split('total_score="')[1].split('"')[0]
                        scores["total_score"] = float(total_score)
                        print(f"从原始XML提取总分: {scores['total_score']}")
                    except:
                        pass
                
                # 提取流畅度分
                if 'fluency_score="' in xml_result:
                    try:
                        fluency_score = xml_result.split('fluency_score="')[1].split('"')[0]
                        scores["fluency_score"] = float(fluency_score)
                    except:
                        pass
                
                # 提取完整度分
                if 'integrity_score="' in xml_result:
                    try:
                        integrity_score = xml_result.split('integrity_score="')[1].split('"')[0]
                        scores["integrity_score"] = float(integrity_score)
                    except:
                        pass
                
                # 提取发音分
                if 'phone_score="' in xml_result:
                    try:
                        phone_score = xml_result.split('phone_score="')[1].split('"')[0]
                        scores["phone_score"] = float(phone_score)
                    except:
                        pass
                
                # 提取声调分
                if 'tone_score="' in xml_result:
                    try:
                        tone_score = xml_result.split('tone_score="')[1].split('"')[0]
                        scores["tone_score"] = float(tone_score)
                    except:
                        pass
            
            # 确保所有分数都有默认值
            for key in ["total_score", "fluency_score", "integrity_score", "phone_score", "tone_score"]:
                if key not in scores:
                    scores[key] = 0.0
            
            return scores
            
        except Exception as e:
            print(f"解析评测结果出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "total_score": 0,
                "fluency_score": 0,
                "integrity_score": 0,
                "phone_score": 0,
                "tone_score": 0,
                "error_info": f"解析失败: {str(e)}"
            }

    def parse_assessment_result(self, xml_result):
        """
        解析XML格式的评测结果

        参数:
            xml_result (str): XML格式的评测结果

        返回:
            dict: 解析后的评测结果
        """
        # 这里简单返回，实际应用中可以使用XML解析库进行解析
        # 如果需要更详细的解析，可以使用xml.etree.ElementTree等库
        return {"raw_xml": xml_result}

    def set_category(self, category):
        """
        设置评测题型

        参数:
            category (str): 评测题型
        """
        valid_cn_categories = ["read_syllable", "read_word", "read_sentence", "read_chapter"]
        valid_en_categories = ["read_word", "read_sentence", "read_chapter", "simple_expression",
                               "read_choice", "topic", "retell", "picture_talk", "oral_translation"]

        if self.ise_type == "cn" and category in valid_cn_categories:
            self.category = category
        elif self.ise_type == "en" and category in valid_en_categories:
            self.category = category
        else:
            print(f"无效的评测题型: {category}")


# 使用示例
if __name__ == "__main__":
    app_id = "YOUR_APP_ID"
    api_key = "YOUR_API_KEY"
    api_secret = "YOUR_API_SECRET"

    # 创建评测实例
    assessor = SpeechAssessment(app_id, api_key, api_secret, ise_type="cn")

    # 设置评测题型（可选，默认为read_sentence）
    assessor.set_category("read_sentence")



    # 进行评测
    text = "今天天气真不错"
    audio_file = "test.wav"  # 16K采样率、16bit位深、单声道

    result = assessor.assess(text, audio_file)

    if result:
        # 解析评测结果
        parsed_result = assessor.extract_scores(result)
        print(parsed_result)