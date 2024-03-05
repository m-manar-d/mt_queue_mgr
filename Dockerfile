# syntax=docker/dockerfile:1
FROM python:latest
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG DIRPATH
WORKDIR $DIRPATH
COPY requirements.txt $DIRPATH
RUN  pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
CMD ["gunicorn", "--config", "gunicorn.conf.py", "mt_queue_mgr.wsgi"]
