from typing import Dict
from dotenv import load_dotenv
import os
import pulumi
from pulumi_kubernetes import Provider
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.yaml import ConfigFile

stack_ref = pulumi.StackReference("persinac/k8s-provision/dev-k8s-stack")
kubeconfig = stack_ref.get_output("kubeconfig")
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconfig)

# Create namespace
namespace_tailscale_name = 'tailscale'
namespace_tailscale = Namespace(
    f"{namespace_tailscale_name}-ns",
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_tailscale_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_tailscale_name,
            "app.kubernetes.io/name": namespace_tailscale_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)


# Function to replace placeholders in the YAML
def replace_placeholders(yaml_content: str, replacements: Dict):
    for key, value in replacements.items():
        yaml_content = yaml_content.replace(f'#{key}#', value)
    return yaml_content


# Read the YAML file
with open('tailscale-operator.yaml', 'r') as file:
    yaml_content = file.read()

load_dotenv()
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')

# Replace placeholders
yaml_content = replace_placeholders(yaml_content, {'client_id_in': client_id, 'client_secret_in': client_secret})

templated_yaml_file = 'templated-tailscale-operator.yaml'
with open(templated_yaml_file, 'w') as file:
    file.write(yaml_content)

# Apply the templated YAML content
tailscale_operator = ConfigFile(
    'tailscale-operator',
    file=templated_yaml_file,
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_tailscale])
)

pulumi.export('tailscale_operator_name', tailscale_operator)
