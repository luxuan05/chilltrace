FROM python:3-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY update-delivery-status/update_delivery_status.py ./update_delivery_status.py
CMD [ "python", "./update_delivery_status.py" ]