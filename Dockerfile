FROM python:3.8-alpine

RUN apk add ffmpeg

WORKDIR /usr/src/app

COPY main.py .

RUN pip install fbchat pydub google-cloud-storage google-cloud speech

CMD [ "python", "./main.py" ]