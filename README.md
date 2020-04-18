# fb-chat-stt

Uses [fbchat](https://github.com/carpedm20/fbchat/) and the [Google Cloud Platform](https://cloud.google.com/) to perform speech recognition on audio messages.

## Introduction

A few of my friends sometimes use Messenger voice messages in group threads, which annoys me to no end when I try to catch up to the conversation.

To remedy to that problem, I developed a bit of glue to sit between the wonderful [fbchat](https://github.com/carpedm20/fbchat/) and the power of the [Google Cloud Platform](https://cloud.google.com/).

My program grabs messages from Messenger, sends them to a GCS bucket, converts them to text using the [speech to text](https://cloud.google.com/speech-to-text/) capabilities of the GCP, and finally sends them back to the thread.
 
## Usage
 
The easiest way to use this is to grab the Docker image:
```
docker pull crispybaguette/fb-chat-stt:latest
```
 
There are a few parameters to pass using environment variables, so I recommend using a dedicated file (`.env`):
```
STT_BUCKET=<gcp bucket name>
STT_THREADS=<comma-separated list of messenger threads>
GOOGLE_APPLICATION_CREDENTIALS=/credentials/service-account.json
FB_USER=<your FB user name>
FB_PASSWORD=<your FB password>
```

You will need a GCP service account with read/write access to a bucket and access to the speech-to-text API. You can retrieve the thread ids as specified [somewhere in this page](https://fbchat.readthedocs.io/en/stable/intro.html).

Run the container with:
```
docker run --env-file .env -v <path to the service account credentials>:/credentials/service-account.json crispybaguette/fb-chat-stt
```

Send a voice message to one of the threads you specified in the `.env` file, and behold the magic.
