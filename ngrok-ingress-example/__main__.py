from typing import Dict
from dotenv import load_dotenv
import os
import pulumi
from pulumi_kubernetes import Provider, meta
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
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
ngrok_subdomain = os.getenv('ngrok_domain')
ngrok_api_key = os.getenv('ngrok_api_key')
ngrok_auth_token = os.getenv('ngrok_auth_token')


namespace_ngrok_ingress_controller_name = 'ngrok-ingress-controller-example'

# CRDs
with open('manifest_yamls/custom-resource-definitions.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'ngrok_domain_in': ngrok_subdomain,
        'ngrok-namespace': namespace_ngrok_ingress_controller_name
    }
)

injected_crds_yaml_file_name = 'formatted_yamls/custom-resource-definitions.yaml'
with open(injected_crds_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)


# Cluster Roles
with open('manifest_yamls/cluster-roles.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'ngrok_domain_in': ngrok_subdomain,
        'ngrok-namespace': namespace_ngrok_ingress_controller_name
    }
)

injected_cr_yaml_file_name = 'formatted_yamls/cluster-roles.yaml'
with open(injected_cr_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)


# Cluster Role Bindings
with open('manifest_yamls/cluster-role-bindings.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'ngrok_domain_in': ngrok_subdomain,
        'ngrok-namespace': namespace_ngrok_ingress_controller_name
    }
)

injected_crbs_yaml_file_name = 'formatted_yamls/cluster-role-bindings.yaml'
with open(injected_crbs_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)


# Game deployment
with open('manifest_yamls/ingress-game-deployment.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'ngrok_domain_in': ngrok_subdomain,
        'ngrok-namespace': namespace_ngrok_ingress_controller_name
    }
)

injected_game_deploy_yaml_file_name = 'formatted_yamls/ingress-game-deployment.yaml'
with open(injected_game_deploy_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)


# Define k8s stack reference
stack_ref = pulumi.StackReference("persinac/k8s-provision/dev-k8s-stack")
kubeconfig = stack_ref.get_output("kubeconfig")
print(kubeconfig)

# set up provider
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconfig)

# Create the ingress controller namespace
namespace_ngrok_ingress_controller = Namespace(
    namespace_ngrok_ingress_controller_name,
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_ngrok_ingress_controller_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_ngrok_ingress_controller_name,
            "app.kubernetes.io/name": namespace_ngrok_ingress_controller_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

## https://raw.githubusercontent.com/ngrok/kubernetes-ingress-controller/main/manifest-bundle.yaml

# Apply the templated YAML content as a configfile
ngrok_game_manifest_crds = ConfigFile(
    'ngrok-game-manifest-crds',
    file=injected_crds_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_ngrok_ingress_controller]
    )
)

# Apply the templated YAML content as a configfile
ngrok_game_manifest_cr = ConfigFile(
    'ngrok-game-manifest-cr',
    file=injected_cr_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[ngrok_game_manifest_crds]
    )
)

# Apply the templated YAML content as a configfile
ngrok_game_manifest_crbs = ConfigFile(
    'ngrok-game-manifest-crbs',
    file=injected_crbs_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[ngrok_game_manifest_cr]
    )
)


# define the helm chart
ingress_controller_chart = Chart(
    "ngrok-ingress-controller",
    ChartOpts(
        chart="ngrok-ingress-controller",
        fetch_opts=FetchOpts(
            repo="https://ngrok.github.io/kubernetes-ingress-controller"
        ),
        namespace=namespace_ngrok_ingress_controller_name,
        values={
            'namespace': namespace_ngrok_ingress_controller_name,
            'credentials': {
                'apiKey': ngrok_api_key,
                'authtoken': ngrok_auth_token
            }
        }
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[
            ngrok_game_manifest_crds,
            ngrok_game_manifest_cr,
            ngrok_game_manifest_crbs
        ]
    )
)

# Apply the templated YAML content as a configfile
ngrok_game_manifest_actual_game = ConfigFile(
    'ngrok-game-manifest-actual-game',
    file=injected_game_deploy_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[ingress_controller_chart]
    )
)


# output the operator
# pulumi.export('ngrok_game_manifest', ngrok_game_manifest)
# pulumi.export("ingress_controller_chart", ingress_controller_chart._name)
