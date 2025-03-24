import wave
import pyaudio
import time
import os


def record_audio(filename, duration=5, sample_rate=16000, channels=1, chunk=1024, format=pyaudio.paInt16):
    """
    使用PyAudio直接录制音频到WAV文件

    参数:
        filename (str): 输出文件名
        duration (int): 录音时长（秒）
        sample_rate (int): 采样率
        channels (int): 通道数
        chunk (int): 块大小
        format: 音频格式

    返回:
        bool: 是否成功
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.abspath(filename)) if os.path.dirname(filename) else '.', exist_ok=True)

    # 初始化PyAudio
    p = pyaudio.PyAudio()

    # 打开音频流
    stream = p.open(format=format,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=chunk)

    print(f"开始录音，持续{duration}秒...")

    # 收集音频数据
    frames = []
    for i in range(0, int(sample_rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)
        # 显示进度
        if i % 10 == 0:
            progress = i / int(sample_rate / chunk * duration) * 100
            print(f"录音进度: {progress:.1f}%", end="\r")

    print("\n录音完成!")

    # 停止并关闭流
    stream.stop_stream()
    stream.close()
    p.terminate()

    # 保存为WAV文件
    try:
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"音频已保存至: {filename}")
        return True
    except Exception as e:
        print(f"保存音频文件失败: {e}")
        return False


# 使用示例
if __name__ == "__main__":
    record_audio("test_recording.wav")