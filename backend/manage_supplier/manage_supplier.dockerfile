FROM python:3-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY manage_supplier/manage_supplier.py ./manage_supplier.py
COPY manage_supplier/invokes.py ./invokes.py
CMD [ "python", "./manage_supplier.py" ]