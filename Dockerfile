# استخدام Python 3.9 slim image
FROM python:3.9-slim

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملفات المتطلبات
COPY requirements.txt .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كامل الكود
COPY . .

# تعيين متغير البيئة للبورت
ENV PORT=5000

# فتح البورت
EXPOSE $PORT

# تشغيل التطبيق باستخدام gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app
