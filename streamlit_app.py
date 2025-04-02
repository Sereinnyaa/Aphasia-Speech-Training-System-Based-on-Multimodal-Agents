### Aphasia Demo System - Streamlit Demo App

import streamlit as st
import os
from main import SpeechRecognizer, LLMProcessor, TextToSpeech, Audio2FaceConnector, SpeechAssessmentModule, USER_WAV, OUTPUT_WAV, A2F_INSTANCE

# 初始化模块
speech_recognizer = SpeechRecognizer()
llm_processor = LLMProcessor()
text_to_speech = TextToSpeech()
a2f_connector = Audio2FaceConnector()
speech_assessment = SpeechAssessmentModule()

# 页面设置
st.set_page_config(page_title="失语症康复训练 Demo", layout="centered")
st.title("🧠 基于多模态智能体的失语症言语训练系统")

st.sidebar.title("📋 功能选择")
mode = st.sidebar.radio("请选择功能模式：", ["正常对话", "语音评测"])

if mode == "正常对话":
    st.header("🎙️ 语音对话")
    if st.button("点击开始对话"):
        with st.spinner("正在识别您的语音..."):
            success, recognized_text = speech_recognizer.recognize_from_microphone()

        if success:
            st.success("识别结果：" + recognized_text)
            with st.spinner("AI正在生成回应..."):
                reply = llm_processor.process_text(recognized_text)
                st.info("AI 回答：" + reply)
                st.audio(OUTPUT_WAV, format="audio/wav")

                text_to_speech.synthesize_speech(reply, OUTPUT_WAV)
                a2f_connector.push_audio_file(OUTPUT_WAV, A2F_INSTANCE)
        else:
            st.error("识别失败，请重试。")

elif mode == "语音评测":
    st.header("🗣️ 发音评测")
    standard_text = st.text_input("请输入你要朗读的标准文本：")
    if st.button("点击开始朗读并评测") and standard_text:
        with st.spinner("请朗读文本中..."):
            success, recognized_text = speech_recognizer.recognize_and_save()

        if success:
            st.success("识别结果：" + recognized_text)
            with st.spinner("正在进行语音评测..."):
                xml_result = speech_assessment.assess_speech(standard_text, USER_WAV)

            if xml_result:
                scores = speech_assessment.assessor.extract_scores(xml_result)
                feedback = llm_processor.process_assessment_result(standard_text, xml_result)

                st.subheader("📊 评测结果")
                st.write(f"总分: {scores.get('total_score', 0):.2f}")
                st.write(f"流畅度: {scores.get('fluency_score', 0):.2f}")
                st.write(f"完整度: {scores.get('integrity_score', 0):.2f}")
                st.write(f"发音分: {scores.get('phone_score', 0):.2f}")
                st.write(f"声调分: {scores.get('tone_score', 0):.2f}")

                st.subheader("🧾 改进建议")
                st.info(feedback)

                text_to_speech.synthesize_speech(feedback, OUTPUT_WAV)
                st.audio(OUTPUT_WAV, format="audio/wav")
                a2f_connector.push_audio_file(OUTPUT_WAV, A2F_INSTANCE)
            else:
                st.error("评测失败。请确保您朗读了正确的内容并重新尝试。")