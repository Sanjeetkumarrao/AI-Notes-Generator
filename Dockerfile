FROM python:3.10
WORKDIR /app
copy . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit","run","app.py","--server.port=8501","server.address=0.0.0.0"]