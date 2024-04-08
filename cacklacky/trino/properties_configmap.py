import os


def coordinator_config_map(namespace_name: str, ):
    return {
        "jvm.config": """
        -server
        -agentpath:/usr/lib/trino/bin/libjvmkill.so
        -Xmx8G
        -XX:+UseG1GC
        -XX:G1HeapRegionSize=32M
        -XX:+ExplicitGCInvokesConcurrent
        -XX:+HeapDumpOnOutOfMemoryError
        -XX:+ExitOnOutOfMemoryError
        -XX:-OmitStackTraceInFastThrow
        -XX:ReservedCodeCacheSize=512M
        -XX:PerMethodRecompilationCutoff=10000
        -XX:PerBytecodeRecompilationCutoff=10000
        -Djdk.attach.allowAttachSelf=true
        -Djdk.nio.maxCachedBufferSize=2000000
        -XX:+UnlockDiagnosticVMOptions
        # Reduce starvation of threads by GClocker, recommend to set about the number of cpu cores (JDK-8192647)
        -XX:GCLockerRetryAllocationCount=32
        """,
        "config.properties": """
        coordinator=true
        node-scheduler.include-coordinator=false
        http-server.http.port=8080
        query.max-memory=4GB
        query.max-memory-per-node=1GB
        discovery.uri=http://localhost:8080
        internal-communication.shared-secret=asdofiuqwyeroiquwehflsafkj8d88gggggggggn875q3p49t75g0gjf;axslknq4950q4950q4950q40
        """,
        "node.properties": """
        node.environment=production
        spiller-spill-path=/tmp
        max-spill-per-node=1TB
        query-max-spill-per-node=250GB
        """,
        "hive.properties": f"""
        connector.name=hive
        hive.metastore.uri=thrift://cackalacky-hive.{namespace_name}:9083
        hive.s3.endpoint=s3.amazonaws.com
        hive.s3.aws-access-key={os.getenv("HIVE_S3_IAM_ACCESS_KEY")}
        hive.s3.aws-secret-key={os.getenv("HIVE_S3_IAM_SECRET_KEY")}
        """,
        "postgresql.properties": f"""
        connector.name=postgresql
        connection-url=jdbc:postgresql://{os.getenv("PG_DB_HOST")}:{os.getenv("PG_DB_PORT")}
        connection-user={os.getenv("PG_DB_USER")}
        connection-password={os.getenv("PG_DB_PASSWORD")}
        """
    }


def worker_config_map(namespace_name: str, ):
    return {
        "jvm.config": """
        -server
        -agentpath:/usr/lib/trino/bin/libjvmkill.so
        -Xmx8G
        -XX:+UseG1GC
        -XX:G1HeapRegionSize=32M
        -XX:+ExplicitGCInvokesConcurrent
        -XX:+HeapDumpOnOutOfMemoryError
        -XX:+ExitOnOutOfMemoryError
        -XX:-OmitStackTraceInFastThrow
        -XX:ReservedCodeCacheSize=512M
        -XX:PerMethodRecompilationCutoff=10000
        -XX:PerBytecodeRecompilationCutoff=10000
        -Djdk.attach.allowAttachSelf=true
        -Djdk.nio.maxCachedBufferSize=2000000
        -XX:+UnlockDiagnosticVMOptions
        # Reduce starvation of threads by GClocker, recommend to set about the number of cpu cores (JDK-8192647)
        -XX:GCLockerRetryAllocationCount=32
        """,
        "config.properties": """
        coordinator=false
        http-server.http.port=8080
        query.max-memory=4GB
        query.max-memory-per-node=1GB
        discovery.uri=http://trino:8080
        internal-communication.shared-secret=asdofiuqwyeroiquwehflsafkj8d88gggggggggn875q3p49t75g0gjf;axslknq4950q4950q4950q40
        """,
        "node.properties": """
        node.environment=production
        spiller-spill-path=/tmp
        max-spill-per-node=1TB
        query-max-spill-per-node=250GB
        """,
        "hive.properties": f"""
        connector.name=hive
        hive.metastore.uri=thrift://cackalacky-hive.{namespace_name}:9083
        hive.s3.endpoint=s3.amazonaws.com
        hive.s3.aws-access-key={os.getenv("HIVE_S3_IAM_ACCESS_KEY")}
        hive.s3.aws-secret-key={os.getenv("HIVE_S3_IAM_SECRET_KEY")}
        """,
        "postgresql.properties": f"""
        connector.name=postgresql
        connection-url=jdbc:postgresql://{os.getenv("PG_DB_HOST")}:{os.getenv("PG_DB_PORT")}
        connection-user={os.getenv("PG_DB_USER")}
        connection-password={os.getenv("PG_DB_PASSWORD")}
        """
    }
