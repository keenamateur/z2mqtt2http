FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    iputils-ping \
    curl \
    netcat-openbsd \
    telnet \
    net-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./app /app

CMD ["python", "main.py"]