FROM node:20-slim

# Install Python and pip for FastAPI
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir fastapi uvicorn

WORKDIR /usr/src/app

# Copy the entrypoint script and wrapper
COPY entrypoint.sh .
COPY wrapper.py .
RUN chmod +x entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# The command to run the wrapper, which will then manage the npx process
CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "8080"]