"""A Python Pulumi program"""

import os
import sys
import json
from dotenv import load_dotenv
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as kubernetes
from pulumi_kubernetes.yaml import ConfigFile


sys.path.insert(0, 'C:\PyCharmProjects\homelab')

from utilities._yaml import replace_placeholders

"""
CSI Order of ops:
 - Load AWS Account ID from .env
 - set bucket name
 - get bucket
 - Create IAM User
 - Create policy document
 - Attach policy to user
 - Create kube secret
 - Deploy CSI helm chart

"""

# load env vars
load_dotenv()
aws_account_id = os.getenv('aws_account_id')
bucket_name_prefix = os.getenv('bucket_name')
aws_region = os.getenv('aws_region')

# just forcing single AZ right now. Can expand later.
region_az_map = {
    "us-east-1": "use1-az4",
    "default": "use1-az4"
}

# Create S3 Objects
# Assuming the bucket name is known and the bucket exists already in AWS
bucket_name = f"{bucket_name_prefix}--{region_az_map.get(aws_region, 'default')}--x-s3"

# Reference an existing S3 bucket
s3_bucket = aws.s3.DirectoryBucket.get(f"{bucket_name_prefix}-s3-express", bucket_name)
# Create an IAM user
iam_user = aws.iam.User("s3-csi-user")

# Combine outputs using Output.all() and formulate the policy
policy_document = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "s3expressStatement",
            "Effect": "Allow",
            "Action": "s3express:*",
            "Resource": [f"arn:aws:s3express:{aws_region}:{aws_account_id}:bucket/{bucket_name}"]
        }
    ]
})

s3_crud_policy = aws.iam.Policy(
    f"{bucket_name_prefix}-s3-csi-express-policy",
    policy=policy_document
)


# Attach the policy to the user
policy_attachment = aws.iam.PolicyAttachment(
    f"{bucket_name_prefix}-s3-csi-express-policy-attachment",
    users=[iam_user.name],
    policy_arn=s3_crud_policy.arn
)

# Create access key for the IAM user
iam_access_key = aws.iam.AccessKey(f"{bucket_name_prefix}-s3-csi-express-access-key", user=iam_user.name)
iam_access_key.secret.apply(lambda secret: print(secret))
# Export the access key id and secret
pulumi.export('access_key_id', iam_access_key.id)
pulumi.export('secret_access_key', pulumi.Output.secret(iam_access_key.secret))
pulumi.export('bucket_arn2', s3_bucket)

# Define k8s stack reference
stack_ref = pulumi.StackReference("persinac/k8s-provision/dev")
kubeconfig = stack_ref.get_output("kubeconfig")

# set up provider
k8s_provider = kubernetes.Provider("k8s-provider", kubeconfig=kubeconfig)

csi_namespace_name = "apache-airflow"

# Create a Kubernetes Secret
aws_secret = kubernetes.core.v1.Secret(
    "aws-secret",
    metadata=kubernetes.meta.v1.ObjectMetaArgs(
        name="aws-secret",
        namespace=csi_namespace_name,
    ),
    string_data={
        "key_id": iam_access_key.id,
        "access_key": iam_access_key.secret,
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[iam_access_key]
    )
)

# Define the Helm Release for aws-mountpoint-s3-csi-driver
aws_mp_s3_csi_driver_release = kubernetes.helm.v3.Release(
    "aws-mountpoint-s3-csi-driver",
    args=kubernetes.helm.v3.ReleaseArgs(
        chart="aws-mountpoint-s3-csi-driver",
        version="1.2.0",
        repository_opts=kubernetes.helm.v3.RepositoryOptsArgs(
            repo="https://awslabs.github.io/mountpoint-s3-csi-driver"
        ),
        namespace=csi_namespace_name,
        values={
            "logLevel": 9  # idk about this, but defaults to 4. Typically the higher, the more verbose.
        }
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[aws_secret]
    )
)

namespace_for_mp_pv_pvc = "apache-airflow"

# Mountpoint deployment
with open('manifest_yamls/non-root-s3-mp-pvc.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'bucket_name': bucket_name,
        'namespace': namespace_for_mp_pv_pvc
    }
)

injected_yaml_file_name = 'formatted_yamls/non-root-s3-mp-pvc.yaml'
with open(injected_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)


# Apply the templated YAML content as a configfile
mountpoint_deployment_s3 = ConfigFile(
    'mountpoint-deployment-s3',
    file=injected_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[aws_mp_s3_csi_driver_release]
    )
)

# Export the name of the Helm Release
pulumi.export("release_name", aws_mp_s3_csi_driver_release.name)
# Export the name of the secret
pulumi.export('secret_name', aws_secret.metadata.name)

# Load an example file to the s3 bucket
aws.s3.BucketObjectv2(
    'dag_s3_mountpoint_example.py',
    bucket=s3_bucket.id,
    source=pulumi.asset.FileAsset("test_dag/example_dag.py"),
)
