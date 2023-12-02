from typing import Dict
from dotenv import load_dotenv
import os
import pulumi
from pulumi_kubernetes import Provider
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.yaml import ConfigFile


def replace_placeholders(yaml_content: str, replacements: Dict) -> str:
    """Replace templated placeholders with the given replacement values.

    This is primarily used for secret replacement and injection. Can be extended
    based on your tailscale operator requirements.

    Parameters
    ----------
    yaml_content: str
    replacements: Dict

    Returns
    -------
    str
    """
    for key, value in replacements.items():
        yaml_content = yaml_content.replace(f'#{key}#', value)
    return yaml_content

# load env vars
load_dotenv()
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')

# read the templated file
with open('tailscale-operator.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(templated_yaml_content, {'client_id_in': client_id, 'client_secret_in': client_secret})

# create new yaml file for the tailscale operator
injected_yaml_file_name = 'formatted-tailscale-operator.yaml'
with open(injected_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)

stack_ref = pulumi.StackReference("persinac/k8s-provision/dev-k8s-stack")
kubeconfig = stack_ref.get_output("kubeconfig")
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconfig)

# Create tailscale namespace
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

# Apply the templated YAML content as a configfile
tailscale_operator = ConfigFile(
    'tailscale-operator',
    file=injected_yaml_file_name,
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_tailscale])
)

# output the operator
pulumi.export('tailscale_operator_name', tailscale_operator)
