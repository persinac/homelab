from typing import Dict
from dotenv import load_dotenv
import os
import sys
import pulumi
from pulumi_kubernetes import Provider
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.yaml import ConfigFile


sys.path.insert(0, 'C:\PyCharmProjects\homelab')

from utilities._yaml import replace_placeholders


# load env vars
load_dotenv()
kube_conf_path = os.getenv('kube_conf_path')
ngrok_subdomain = os.getenv('ngrok_domain')
ngrok_api_key = os.getenv('ngrok_api_key')
ngrok_auth_token = os.getenv('ngrok_auth_token')


namespace_2048_game_name = 'test-2048-game'

# Game deployment
with open('manifest_yamls/ingress-game-deployment.yaml', 'r') as file:
    templated_yaml_content = file.read()

# Inject .env values and get formatted yaml
injected_yaml_content = replace_placeholders(
    templated_yaml_content,
    {
        'namespace': namespace_2048_game_name
    }
)

injected_game_deploy_yaml_file_name = 'formatted_yamls/ingress-game-deployment.yaml'
with open(injected_game_deploy_yaml_file_name, 'w') as file:
    file.write(injected_yaml_content)

# Read the kubeconfig file
with open(kube_conf_path, 'r') as kubeconfig_file:
    kubeconfig = kubeconfig_file.read()

# injected_game_deploy_yaml_file_name = "manifest_yamls/testing.yaml"

# set up provider
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconfig)

# Create the ingress controller namespace
namespace_2048_game = Namespace(
    namespace_2048_game_name,
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_2048_game_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_2048_game_name,
            "app.kubernetes.io/name": namespace_2048_game_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Apply the templated YAML content as a configfile
game_deployment_manifest = ConfigFile(
    '2048-game-deployment-manifest',
    file=injected_game_deploy_yaml_file_name,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_2048_game]
    )
)

