import datetime
import io
import os
import uuid
import signal
import sys
import threading
import time
import tempfile
import urllib

from fbchat import Client
from fbchat.models import Message, Thread, AudioAttachment
from google.cloud import speech_v1, storage
from google.cloud.speech_v1 import enums
from pydub import AudioSegment


class STTClient(Client):

    __userCacheTTL = 7200
    __userCache = dict()
    __userCacheFetchTimes = dict()

    _threads = []
    _bucket_name = None

    def __init__(self, user, password, threads, bucket):
        super().__init__(user, password)
        self._threads = threads
        self._bucket = bucket

    def __getUser(self, user_id):
        """
        Returns user info with cache management
        """

        ts = time.time()
        # Check for non-stale user in cache
        if user_id in self.__userCache and self.__userCacheFetchTimes[user_id] + \
                self.__userCacheTTL > ts:
            return self.__userCache[user_id]
        # If user not present in cache, fetch
        else:
            try:
                user_info = self.fetchUserInfo(user_id)
                self.__userCache[user_id] = user_info[user_id]
                self.__userCacheFetchTimes[user_id] = ts
                return user_info[user_id]
            except BaseException:
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

        return author_name

    def __sttConvert(self, attachment):
        """
        Convert a voice message to text
        """
        # Read the message (.mp4) into a segment
        # An intermediary temp file is required because
        # pydub refuses to load directy from a mp4 file-like obj
        # TODO: figure ou what's wrong with loading mp4 files
        segment = None
        with urllib.request.urlopen(attachment.url) as f:
            with tempfile.NamedTemporaryFile() as tmp:
                tmp.write(f.read())
                segment = AudioSegment.from_file(tmp.name, "mp4")

        # Convert it to a 16 kbit/s, mono, 16 bit .wav
        segment = segment.set_sample_width(2)
        segment = segment.set_frame_rate(16000)
        segment = segment.set_channels(1)

        export = segment.export(format="wav")
        export.seek(0)

        # Upload to the GCP bucket
        # Not strictly necessary, but I have a data hoarding problem
        storage_client = storage.Client()
        bucket = storage_client.bucket(self._bucket)
        # TODO: nicer file names
        blobName = str(uuid.uuid4()) + ".wav"
        blob = bucket.blob(blobName)
        blob.upload_from_file(export)

        # Perform the STT
        client = speech_v1.SpeechClient()
        config = {"language_code": "fr-FR"}
        audio = {"uri": f"gs://{self._bucket}/{blobName}"}
        response = client.recognize(config, audio)

        # Return the most probable result
        return response.results[0].alternatives[0].transcript

    def __formatMessage(self, author_id, timestamp, text):
        """
        Format a given text with the date and author name
        """
        # The timestamp is in ms, so divide by 1e3 to get seconds
        date = datetime.datetime.fromtimestamp(
            timestamp / 1e3).strftime("%H:%M:%S")

        return f"{self.__buildAuthorName(author_id)} ({date}): {text}"

    def onMessage(
            self,
            author_id,
            message_object,
            thread_id,
            thread_type,
            ts,
            **kwargs):
        for attachment in message_object.attachments:
            if (thread_id in self._threads
                    and isinstance(attachment, AudioAttachment)
                    and attachment.audio_type == "VOICE_MESSAGE"):

                try:
                    # Perform STT on the attachment
                    trans_text = self.__sttConvert(attachment)

                    # Format the message
                    formatted_message = self.__formatMessage(
                        author_id,
                        message_object.timestamp,
                        trans_text
                    )

                    print(f"Transcribed message: \"{formatted_message}\"")

                    # Send it back whence it came
                    self.send(
                        Message(text=formatted_message),
                        thread_id=thread_id,
                        thread_type=thread_type
                    )
                except BaseException:
                    print(
                        f"Error while transcribing message: {sys.exc_info()[0]}")


def signal_handler(sig, frame):
    client.stopListening()
    listening_thread.join()
    sys.exit(0)


if __name__ == "__main__":
    # Load the configuration
    threads = os.environ['STT_THREADS'].split(",")
    bucket = os.environ['STT_BUCKET']
    user = os.environ['FB_USER']
    password = os.environ['FB_PASSWORD']

    # Set up the FB chat client
    client = STTClient(user, password, threads, bucket)

    # Run in a thread to avoid blocking everything
    listening_thread = threading.Thread(target=client.listen, args=(False,))
    listening_thread.start()

    # Stop on SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl+C')
    signal.pause()
