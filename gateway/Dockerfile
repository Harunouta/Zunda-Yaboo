FROM python:3.12-slim

WORKDIR /app
COPY split.py server.py ./

ENV PYTHONUNBUFFERED=1
ENV GW_LISTEN_HOST=0.0.0.0
ENV GW_LISTEN_PORT=4000
ENV GW_LMSTUDIO_HOST=host.docker.internal
ENV GW_LMSTUDIO_PORT=1234

EXPOSE 4000
CMD ["python", "server.py"]
