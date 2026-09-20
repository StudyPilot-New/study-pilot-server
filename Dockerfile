FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ACCESS_DB=/data/access.sqlite3
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && mkdir /data && chown 10001:10001 /data
COPY gateway.py access_store.py accounts.py account_routes.py plans.py manual_payments.py payment_routes.py manage_access.py portal.py account.html account.js account.css landing.html marketing_routes.py guide_visuals.py guide.html site.css site.js ./
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "gateway:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--limit-concurrency", "32"]
