FROM python:3.13-slim

# 1. Setup the unprivileged execution account
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --only-binary :all: --no-cache-dir -r requirements.txt

# 2. Secure code layers (Owned by root, immutable to appuser)
COPY --chown=root:root --chmod=0555 main.py print_version.py ./

EXPOSE 8000

# 3. Drop privileges for runtime security
USER appuser

CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]
