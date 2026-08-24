FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    pandas \
    numpy \
    matplotlib

RUN useradd --create-home --shell /usr/sbin/nologin sandbox

WORKDIR /workspace

USER sandbox
