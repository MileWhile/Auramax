# Use an official, slim Python runtime as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies from your requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the special emergentintegrations package
RUN pip install --no-cache-dir emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Copy the rest of your application's source code into the container
COPY . .

# Tell the container what port to listen on. Cloud Run expects 8080 by default.
EXPOSE 8080

# The command to run your application in production
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "180", "--bind", "0.0.0.0:8080", "server:app"]