# fb-chat-stt

Uses [fbchat](https://github.com/carpedm20/fbchat/) and the [Google Cloud Platform](https://cloud.google.com/) to perform speech recognition on audio messages.

## Introduction

A few of my friends sometimes use Messenger voice messages in group threads, which annoys me to no end when I try to catch up to the conversation.

To remedy to that problem, I developed a bit of glue to sit between the wonderful [fbchat](https://github.com/carpedm20/fbchat/) and the power of the [Google Cloud Platform](https://cloud.google.com/).

My program grabs messages from Messenger, sends them to a GCS bucket, converts them to text using the [speech to text](https://cloud.google.com/speech-to-text/) capabilities of the GCP, and finally sends them back to the thread.
