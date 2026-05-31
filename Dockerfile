# E:\PythonProject\quantdo_image\Dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

COPY . .

EXPOSE 7777

CMD ["python", "-m", "app.utils.web_ui"]
