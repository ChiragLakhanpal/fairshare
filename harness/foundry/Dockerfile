FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir --pre agent-framework-foundry-hosting
COPY . .
ENV FAIRSHARE_BACKEND=databricks FAIRSHARE_MODEL=azure PORT=8088
EXPOSE 8088
CMD ["python", "-m", "harness.foundry.host"]
