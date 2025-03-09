FROM python:3.12

RUN apt-get -y update

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
COPY uploader.py .
COPY configs/* ./configs/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install 7zip
RUN apt-get update && apt-get install -y p7zip-full && rm -rf /var/lib/apt/lists/*

VOLUME [ "/sendFiles"]

# Run the bot
CMD ["python", "uploader.py"]
