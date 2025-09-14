# Use official Python image
FROM python:3.11-slim

# Set working directory to /app
WORKDIR /app

# Copy all files to /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure bot is a package
RUN touch bot/__init__.py

# Start the bot using the package/module syntax
CMD ["python", "-m", "bot.main"]
