FROM python:3.8-alpine

RUN apk add linux-headers ffmpeg build-base

WORKDIR /usr/src/app

RUN pip install fbchat pydub google-cloud-storage google-cloud-speech

COPY main.py .

CMD [ "python", "./main.py" ]