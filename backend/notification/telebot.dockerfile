FROM python:3-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY notification/amqp_lib.py ./
COPY notification/telebot.py ./
CMD ["python", "-u", "telebot.py"]