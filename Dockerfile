FROM python:3.8

RUN mkdir /app

WORKDIR /app

COPY main.py .
COPY settings.py .
COPY target.py .
COPY client.py .

CMD [ "python", "./main.py"]