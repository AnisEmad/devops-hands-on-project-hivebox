FROM python:3.13-slim

# Create a system user and group named 'appuser' with no login privileges
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --only-binary :all: --no-cache-dir -r requirements.txt

# Copy source code and explicitly change ownership to the appuser
COPY --chown=appuser:appuser main.py print_version.py ./

EXPOSE 8000

# Tell Docker to drop root privileges and execute everything below this line as appuser
USER appuser

CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]