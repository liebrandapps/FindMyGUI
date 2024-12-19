FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p findmy
RUN mkdir -p imap
RUN mkdir -p www

COPY main.py .
COPY airTag.py .
COPY api.py .
COPY config.py .
COPY context.py .
COPY daemon.py .
COPY mqtt.py .
COPY imap/* imap/
COPY findmy/* findmy/
COPY www/* www/

EXPOSE 8008
CMD [ "python", "./main.py" ]
