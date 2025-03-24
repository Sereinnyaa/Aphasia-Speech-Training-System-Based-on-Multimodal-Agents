import time
import numpy as np
import soundfile
import audio2face_pb2
import audio2face_pb2_grpc
import grpc

def push_audio_stream_only(stub, audio_data, samplerate, instance_name):
    """
    Push audio data stream to an existing Audio2Face gRPC connection.
    """
    chunk_size = samplerate // 10  # 0.1 second per chunk
    sleep_between_chunks = 0.04  # Delay between chunks to simulate real-time playback

    def make_generator():
        # First message: Send metadata with start_marker
        start_marker = audio2face_pb2.PushAudioRequestStart(
            samplerate=samplerate,
            instance_name=instance_name,
            block_until_playback_is_finished=True
        )
        yield audio2face_pb2.PushAudioStreamRequest(start_marker=start_marker)

        # Subsequent messages: Send audio chunks
        for i in range(len(audio_data) // chunk_size + 1):
            time.sleep(sleep_between_chunks)
            chunk = audio_data[i * chunk_size: i * chunk_size + chunk_size]
            yield audio2face_pb2.PushAudioStreamRequest(audio_data=chunk.astype(np.float32).tobytes())

    try:
        print("Sending audio data stream...")
        response = stub.PushAudioStream(make_generator())
        if response.success:
            print("Audio stream successfully pushed to Audio2Face!")
        else:
            print(f"Error pushing audio stream: {response.message}")
    except grpc.RpcError as e:
        print(f"gRPC error during audio streaming: {e}")
    except Exception as e:
        print(f"Unexpected error during audio streaming: {e}")


def main():
    """
    Main function to send audio data stream via an existing gRPC connection.
    """
    # Audio file path and instance name should be passed as command-line arguments
    import sys
    if len(sys.argv) < 3:
        print("Usage: python script.py <PATH_TO_WAV> <INSTANCE_NAME>")
        return

    # Audio2Face gRPC connection URL
    url = "localhost:50051"  # Make sure this matches Audio2Face's gRPC server

    # Path to input WAV file
    audio_fpath = sys.argv[1]

    # Instance name of the Audio2Face Streaming Audio Player
    instance_name = sys.argv[2]

    # Load audio data
    try:
        data, samplerate = soundfile.read(audio_fpath, dtype="float32")
        if len(data.shape) > 1:  # Convert stereo to mono if necessary
            data = np.mean(data, axis=1)
    except Exception as e:
        print(f"Failed to read audio file: {e}")
        return

    # Use an existing gRPC connection and push audio stream
    try:
        channel = grpc.insecure_channel(url)
        stub = audio2face_pb2_grpc.Audio2FaceStub(channel)
        push_audio_stream_only(stub, data, samplerate, instance_name)
    except Exception as e:
        print(f"Failed to connect to Audio2Face server: {e}")
    # finally:
    #     print("Closing gRPC connection...")
    #     channel.close()


if __name__ == "__main__":
    main()
