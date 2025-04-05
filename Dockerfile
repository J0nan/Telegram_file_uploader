FROM python:3.12

# Install dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg p7zip-full && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
COPY uploader.py .
COPY configs/* ./configs/
COPY utils/* ./utils/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

VOLUME [ "/sendFiles"]

# Run the bot
CMD ["python", "uploader.py"]
