FROM python:3.12-slim
WORKDIR /app
COPY server.py index.html ./
ENV PORT=8000
ENV DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "server.py"]
