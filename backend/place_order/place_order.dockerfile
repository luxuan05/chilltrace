FROM python:3-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY place_order/place_order.py ./place_order.py
COPY place_order/amqp_lib.py ./amqp_lib.py
COPY place_order/invokes.py ./invokes.py
CMD [ "python", "./place_order.py" ]