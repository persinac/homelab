FROM dimitri/pgloader:latest

WORKDIR /usr/src/app

# Install ca-certificates
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy certs
COPY ./*.crt /usr/local/share/ca-certificates/

# Update certs
RUN update-ca-certificates

# Set up source environment variables
ENV SOURCE_HOST=source-remote-address.com
ENV SOURCE_PORT=source-port
ENV SOURCE_USER=source-user
ENV SOURCE_PASSWORD=source-user-password
ENV SOURCE_DB_NAME=practice

# Set up target environment variables
ENV TARGET_HOST=target-remote-address.com
ENV TARGET_PORT=target-port
ENV TARGET_USER=target-user
ENV TARGET_PASSWORD=target-password
ENV TARGET_DB_NAME=practice

# Run
CMD sh -c "pgloader --no-ssl-cert-verification mysql://${SOURCE_USER}:${SOURCE_PASSWORD}@${SOURCE_HOST}:${SOURCE_PORT}/${SOURCE_DB_NAME}?useSSL=true pgsql://${TARGET_USER}:${TARGET_PASSWORD}@${TARGET_HOST}:${TARGET_PORT}/${TARGET_DB_NAME}?sslmode=require"
