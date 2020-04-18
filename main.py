import datetime
import io
import os
import signal
import sys
import tempfile
import threading
import time
import urllib
import uuid

from fbchat import Client
from fbchat.models import *
from google.cloud import speech_v1, storage
from google.cloud.speech_v1 import enums
from pydub import AudioSegment

bucket_name = "audio_messages"
group_chat_id = "1689913587737241"

threads = []


class STTClient(Client):

    __userCacheTTL = 7200
    __userCache = dict()
    __userCacheFetchTimes = dict()

    def __getUser(self, user_id):
        """
        Returns user info with cache management
        """

        ts = time.time()
        # Check for non-stale user in cache
        if user_id in self.__userCache and self.__userCacheFetchTimes[user_id] + self.__userCacheTTL > ts:
            return self.__userCache[user_id]
        # If user not present in cache, fetch
        else:
            try:
                user = self.fetchUserInfo(user_id)
                self.__userCache[user_id] = user
                self.__userCacheFetchTimes[user_id] = ts
                return user
            except:
                return None

    def __buildAuthorName(self, user_id):
        """
        Build the author name from the user info
        """
        user = self.__getUser(user_id)

        if user.nickname is not None:
            author_name = user.nickname
        else:
            author_name = user.first_name
            if user.last_name is not None:
                author_name += " " + user.last_name

    def __sttConvert(self, attachment):
        """
        Convert a voice message to text
        """
        # Read the message (.mp4) into a segment
        # A buffer is required because urlopen does not support seek operations
        segment = None
        with urllib.request.urlopen(attachment.url) as f:
            segment = AudioSegment.from_file(io.BytesIO(f.read()))

        # Convert it to a 16 kbit/s, mono, 16 bit .wav
        segment = segment.set_sample_width(2)
        segment = segment.set_frame_rate(1600)
        segment = segment.set_channels(1)

        wav_file = segment.export(format="wav")

        # Upload to the GCP bucket
        # Not strictly necessary, but I have a data hoarding problem
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobName = str(uuid.uuid4())+".wav"
        blob = bucket.blob(blobName)
        blob.upload_from_file(wav_file)

        # Perform the STT
        client = speech_v1.SpeechClient()
        config = {"language_code": "fr-FR"}
        audio = {"uri": f"gs://{bucket_name}/{blobName}"}
        response = client.recognize(config, audio)

        # Return the most probable result
        return response.results[0].alternatives[0]

    def __formatMessage(self, author_id, timestamp, text):
        """
        Format a given text with the date and author name
        """
        # The timestamp is in ms, so divide by 1e3 to get seconds
        date = datetime.datetime.fromtimestamp(
            timestamp / 1e3).strftime("%H:%M:%S")

        return f"{self.__buildAuthorName(author_id)} ({date}): {text}"

    def onMessage(self, author_id, message_object, thread_id, thread_type, ts, **kwargs):
        for attachment in message_object.attachments:
            if (thread_id in threads
                    and isinstance(attachment, AudioAttachment)
                    and attachment.audio_type == "VOICE_MESSAGE"):
                # Perform STT on the attachment
                trans_text = self.__sttConvert(attachment)

                # Format the message
                formatted_message = self.__formatMessage(
                    author_id,
                    message_object.timestamp,
                    trans_text
                )

                # Send it back whence it came
                self.send(
                    Message(text=formatted_message),
                    thread_id=thread_id,
                    thread_type=thread_type
                )


def sampleRecognize(file_name):
    """
    Transcribe a short audio file using synchronous speech recognition
    """

    client = speech_v1.SpeechClient()
    config = {
        "language_code": "fr-FR"
    }
    audio = {"uri": f"gs://{bucket_name}/{file_name}"}

    response = client.recognize(config, audio)
    text = []

    for result in response.results:
        # First alternative is the most probable result
        alternative = result.alternatives[0]
        text.append(alternative.transcript)

    return text


def signal_handler(sig, frame):
    client.stopListening()
    listening_thread.join()
    sys.exit(0)


if __name__ == "__main__":
    # Add the threads we want to listen to
    threads = os.environ['STT_THREADS'].split(",")

    client = STTClient(os.environ['FB_USER'], os.environ['FB_PASSWORD'])

    listening_thread = threading.Thread(target=client.listen, args=(False,))
    listening_thread.start()

    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl+C')
    signal.pause()
