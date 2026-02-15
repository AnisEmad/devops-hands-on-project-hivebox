FROM python:slim

WORKDIR /app

COPY print_version.py /app/print_version.py

CMD [ "python", "print_version.py" ]

