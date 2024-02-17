import os
import sys
import json
from dotenv import load_dotenv
import pulumi
from pulumi import Output
from pulumi_kubernetes import Provider
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.yaml import ConfigFile
import pulumi_aws as aws

sys.path.insert(0, 'C:\PyCharmProjects\homelab')

from utilities._yaml import replace_placeholders

# load env vars
load_dotenv()
kube_conf_path = os.getenv('kube_conf_path')
fernet_key = os.getenv('fernet_key')
db_host = os.getenv('host')
db_port = os.getenv('port')
db_database = os.getenv('database')
db_user = os.getenv('user')
db_password = os.getenv('password')
aws_account_id = os.getenv('aws_account_id')
bucket_name_prefix = os.getenv('bucket_name')
aws_region = os.getenv('aws_region')
airflow_web_domain = os.getenv('airflow_web_domain')

# just forcing single AZ right now. Can expand later.
region_az_map = {
    "us-east-1": "use1-az4",
    "default": "use1-az4"
}

# Create S3 Objects
# Assuming the bucket name is known and the bucket exists already in AWS
express_bucket_name = f"{bucket_name_prefix}--{region_az_map.get(aws_region, 'default')}--x-s3"

# Create S3 Objects
# Assuming the bucket name is known and the bucket exists already in AWS
bucket_name = bucket_name_prefix

# Reference an existing S3 bucket
s3_bucket = aws.s3.Bucket("augmented-ninja", bucket=bucket_name)

# Create an IAM user
iam_user = aws.iam.User("airflow-s3-user")

# Combine outputs using Output.all() and formulate the policy
policy_document = Output.all(s3_bucket.arn).apply(lambda args: json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject*",
                "s3:ListBucket*",
                "s3:PutObject*",
                "s3:DeleteObject*"
            ],
            "Resource": [
                f"{args[0]}",
                f"{args[0]}/*"
            ]
        }
    ]
}))

s3_crud_policy = aws.iam.Policy(
    "augmented-ninja-s3-crud",
    policy=policy_document
)


# Attach the policy to the user
policy_attachment = aws.iam.PolicyAttachment(
    "augmented-ninja-s3",
    users=[iam_user.name],
    policy_arn=s3_crud_policy.arn
)

# Create access key for the IAM user
iam_access_key = aws.iam.AccessKey("airflow-s3-access-key", user=iam_user.name)
iam_access_key.secret.apply(lambda secret: print(secret))
# Export the access key id and secret
pulumi.export('access_key_id', iam_access_key.id)
pulumi.export('secret_access_key', pulumi.Output.secret(iam_access_key.secret))

# Read the kubeconfig file
with open(kube_conf_path, 'r') as kubeconfig_file:
    kubeconfig = kubeconfig_file.read()

# set up provider
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconfig)

namespace_apache_airflow_name = 'apache-airflow'

# Create the namespaces
namespace_airflow = Namespace(
    namespace_apache_airflow_name,
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_apache_airflow_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_apache_airflow_name,
            "app.kubernetes.io/name": namespace_apache_airflow_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)
namespace_statsd_exporter_name = "statsd-exporter"
namespace_statsd_exporter = Namespace(
    namespace_statsd_exporter_name,
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_statsd_exporter_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_statsd_exporter_name,
            "app.kubernetes.io/name": namespace_statsd_exporter_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Statsd ConfigMap deployment
with open('manifest_yamls/statsd-configmap-exporter-mappings.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'namespace': namespace_statsd_exporter_name
    }
)

statsd_configmap_injected_yaml_file_name = 'formatted_yamls/statsd-configmap-exporter-mappings.yaml'
with open(statsd_configmap_injected_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)


# Apply the templated YAML content as a configfile
statsd_configmap_manifest = ConfigFile(
    'statsd-configmap-manifest',
    file=statsd_configmap_injected_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_statsd_exporter]
    )
)


# Statsd Exporter
statsd_exporter = Chart(
    "statsd-exporter",
    ChartOpts(
        chart="prometheus-statsd-exporter",
        fetch_opts=FetchOpts(
            repo="https://prometheus-community.github.io/helm-charts"
        ),
        namespace=namespace_statsd_exporter_name,
        values={
            'namespace': namespace_statsd_exporter_name,
            'statsd': {
                'mappingConfigMapName': 'statsd-airflow-configmap',
                'mappingConfigMapKey': 'statsd-config'
            },
            "extraArgs": [
                "--log.level=info"  # info|debug ... debug is REALLY verbose
            ],
            'serviceMonitor': {
                'enabled': True,
                'namespace': namespace_statsd_exporter_name
            }
        }
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[
            namespace_statsd_exporter, statsd_configmap_manifest
        ]
    )
)

# Mountpoint deployment
with open('manifest_yamls/non-root-s3-mp-pvc.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content_mp = replace_placeholders(
    templated_yaml_content,
    {
        'bucket_name': express_bucket_name,
        'namespace': namespace_apache_airflow_name
    }
)

injected_yaml_file_name_mp = 'formatted_yamls/non-root-s3-mp-pvc.yaml'
with open(injected_yaml_file_name_mp, 'w') as file:
    file.write(injected_yaml_content_mp)


# Apply the templated YAML content as a configfile
mountpoint_deployment_s3 = ConfigFile(
    'mountpoint-deployment-s3',
    file=injected_yaml_file_name_mp,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_airflow]
    )
)

# Export the name of the Helm Release
pulumi.export("mountpoint_deployment_s3", mountpoint_deployment_s3)

# Load an example file to the s3 bucket
aws.s3.BucketObjectv2(
    'dag_s3_mountpoint_example.py',
    bucket=express_bucket_name,
    source=pulumi.asset.FileAsset("test_dag/example_dag.py"),
)


# define the helm chart
# helm show chart airflow-stable/airflow
airflow_chart = Chart(
    "airflow",
    ChartOpts(
        chart="airflow",
        fetch_opts=FetchOpts(
            repo="https://airflow-helm.github.io/charts"
        ),
        namespace=namespace_apache_airflow_name,
        values={
            'namespace': namespace_apache_airflow_name,
            'airflow': {
                'image': {
                    'repository': 'persinac/airflow-requirements',
                    'tag': '0.0.1'
                },
                'config': {
                    'AIRFLOW__CORE__LOAD_EXAMPLES': 'False',
                    'AIRFLOW__CORE__TEST_CONNECTION': 'True',
                    'AIRFLOW__WEBSERVER__BASE_URL': f'http://{airflow_web_domain}',
                    'AIRFLOW__WEBSERVER__NAVBAR_COLOR': '#ff8200',
                    'AIRFLOW__WEBSERVER__WEB_SERVER_MASTER_TIMEOUT': '300',
                    'AIRFLOW__WEBSERVER__WEB_SERVER_WORKER_TIMEOUT': '300',
                    'AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE': 'America/New_York',
                    # https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html#logging
                    # https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/logging/s3-task-handler.html
                    'AIRFLOW__LOGGING__COLORED_CONSOLE_LOG': True,
                    'AIRFLOW__LOGGING__DELETE_LOCAL_LOGS': False,
                    'AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER': 's3://augmented-ninja/airflow/logs',
                    'AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID': 's3-logger',
                    'AIRFLOW__LOGGING__REMOTE_LOGGING': True,
                    'AIRFLOW__METRICS__STATSD_ON': True,
                    'AIRFLOW__METRICS__STATSD_HOST': "statsd-exporter-prometheus-statsd-exporter.statsd-exporter",
                    'AIRFLOW__METRICS__STATSD_PORT': '9125',
                    # 'AIRFLOW__METRICS__METRICS_ALLOW_LIST': 'scheduler,worker,web', # allow all
                },
                'connections': [
                    {
                        # works
                        "id": 's3-logger',
                        'type': 'aws',
                        'description': 'aws connection from pulumi',
                        "login": iam_access_key.id,
                        "password": iam_access_key.secret,
                        'extra': {
                            'region_name': aws_region,
                        }
                    }
                ],
                'executor': 'KubernetesExecutor',
                'fernetKey': fernet_key,
                'securityContext': {'fsGroup': 65534}
            },
            'web': {
                'securityContext': {'fsGroup': 65534},
                'resources': {
                    'requests': {
                        'memory': '2Gi',
                        'cpu': '2000m'
                    }
                }
            },
            'scheduler': {
                'replicas': 2,
                'podDisruptionBudget': {
                    'enabled': True,
                    'apiVersion': 'policy/v1',
                    'minAvailable': 1
                },
                'resources': {},
                'labels': {},
                'podLabels': {},
                'securityContext': {'fsGroup': 2000}
            },
            'workers': {
                'enabled': False,
            },
            'flower': {
                'enabled': False
            },
            'dags': {
                # https://github.com/airflow-helm/charts/blob/main/charts/airflow/values.yaml#L1328
                'path': '/opt/airflow/dags',
                'persistence': {
                    'enabled': True,
                    'existingClaim': 's3-claim',
                    'accessMode': 'ReadOnlyMany'
                }
            },
            'ingress': {
                # https://github.com/airflow-helm/charts/blob/main/charts/airflow/docs/faq/kubernetes/ingress.md
                'enabled': False,
            },
            'postgresql': {
                'enabled': False
                # embedded pgsql: https://github.com/airflow-helm/charts/blob/main/charts/airflow/values.yaml#L1480
            },
            'externalDatabase': {
                'type': 'postgres',
                'host': db_host,
                'port': db_port,
                'database': db_database,
                'user': db_user,
                'password': db_password,
                'properties': "?sslmode=require"
            },
            'redis': {
                'enabled': False
            }
        }
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[
            namespace_airflow,
            mountpoint_deployment_s3
        ]
    )
)

# Apply the templated YAML content as a configfile
ingress_manifest = ConfigFile(
    'airflow-ingress-manifest',
    file='manifest_yamls/apache-airflow-ngrok-ingress.yaml',
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[airflow_chart]
    )
)
