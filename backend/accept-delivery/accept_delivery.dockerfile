FROM python:3-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY accept-delivery/accept_delivery.py ./accept_delivery.py
COPY clients ./clients
CMD [ "python", "./accept_delivery.py" ]