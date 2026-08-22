FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN printf '#!/bin/sh\nexec python3 /app/app/main.py "$@"\n' > /usr/local/bin/oraculo \
    && chmod +x /usr/local/bin/oraculo

# Idle by default; interact via:  docker compose exec -it oraculo oraculo [question]
CMD ["/bin/sh", "-c", "while sleep 3600; do :; done"]
