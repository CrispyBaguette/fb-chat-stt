FROM python:3.8-alpine

RUN apk add linux-headers ffmpeg build-base

RUN pip install fbchat pydub google-cloud-storage google-cloud-speech

WORKDIR /usr/src/app

COPY main.py .

CMD [ "python", "./main.py" ]