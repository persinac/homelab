# MySQL to PG Migration

This directory hosts a dockerfile to build an image based on the official pgloader image: dimitri/pgloader:latest.

# Pre-reqs

Your MySQL instance _must_ be 5.7. If you're running anything > 5.X, you'll need to migrate your MySQL
database to an instance that is running 5.7. This is because of this:

``Condition QMYND:MYSQL-UNSUPPORTED-AUTHENTICATION was signalled.``

https://github.com/dimitri/pgloader/issues/782

So, if you're in this camp, either find another app or run a migration from MySQL 8 to MySQL 5.7

## MySQL 8 -> MySQL 5.7

All I did was install MySQL 5.7 locally, run the MySQL Workbench Migration wizard, and migrated everything
to my local instance.

# Usage

1. Modify the environment variables in the Dockerfile to your needs:

```bash
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
```

2. Build the image: ``docker build -t my-pgloader-app .``
3. Run the container: ``docker run --rm -it my-pgloader-app``

## Multiple Databases
If you have multiple databases, I think you have to run this 1-by-1. I was only migrating a small number of DBs, so that wasn't an issue for me.