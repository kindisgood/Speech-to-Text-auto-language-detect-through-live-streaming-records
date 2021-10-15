from __future__ import division

import re
import sys

from google.cloud import speech_v1p1beta1 as speech

import pyaudio
from six.moves import queue

RATE = 16000
CHUNK = int(RATE / 10)  

client = speech.SpeechClient()

first_lang = "ko-KR"
second_lang = "en-US"
third_lang = "ja-JP"
fourth_lang = "de-DE"


metadata = speech.RecognitionMetadata()
metadata.interaction_type = speech.RecognitionMetadata.InteractionType.PHONE_CALL
metadata.microphone_distance = (
    speech.RecognitionMetadata.MicrophoneDistance.FARFIELD
)
metadata.recording_device_type = (
    speech.RecognitionMetadata.RecordingDeviceType.OTHER_OUTDOOR_DEVICE
)
metadata.original_media_type = (speech.RecognitionMetadata.OriginalMediaType.AUDIO)
metadata.recording_device_name = "Pixel 2 XL"
metadata.industry_naics_code_of_audio = 519190


class MicrophoneStream(object):

    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,

            channels=1,
            rate=self._rate,
            input=True,
  
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
    
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
    
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
          
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]


            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


def listen_print_loop(responses):
   
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

  
        overwrite_chars = " " * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + "\r")
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)

            if re.search(r"\b(exit|quit)\b", transcript, re.I):
                print("Exiting..")
                break

            num_chars_printed = 0


def main():
    
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
    language_code= first_lang,
    alternative_language_codes=[second_lang, third_lang, fourth_lang],
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        responses = client.streaming_recognize(streaming_config, requests)


        listen_print_loop(responses)


if __name__ == "__main__":
    main()