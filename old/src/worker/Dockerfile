# Dockerfile for the Atlas worker container
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# The build context is the project root
COPY src/worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code into the container
COPY src/ /app/src/

# Set the python path to allow for imports from the src root
ENV PYTHONPATH="/app/src"

# Default command (can be overridden)
CMD ["python3"]
