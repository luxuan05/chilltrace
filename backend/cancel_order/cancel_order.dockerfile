FROM python:3-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY cancel_order/cancel_order.py ./cancel_order.py
COPY cancel_order/invokes.py ./invokes.py
CMD [ "python", "./cancel_order.py" ]