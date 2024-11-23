
FROM python:3.9-slim


WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .


EXPOSE 5000


ENV FLASK_APP app.py

# Run app.py when the container launches.
CMD ["flask", "run", "--host=0.0.0.0"]