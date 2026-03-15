FROM python:3-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY amqp_lib.py ./
COPY telegram.py ./
COPY emailService.py ./
ARG APP_MODULE=telegram.py
ENV APP_MODULE=${APP_MODULE}
CMD [ "sh", "-c", "python ./${APP_MODULE}" ]