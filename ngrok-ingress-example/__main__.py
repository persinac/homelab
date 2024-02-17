from dotenv import load_dotenv
import os
import pulumi
from pulumi_kubernetes import Provider
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.core.v1 import Namespace


# load env vars
load_dotenv()
kube_conf_path = os.getenv('kube_conf_path')
ngrok_api_key = os.getenv('ngrok_api_key')
ngrok_auth_token = os.getenv('ngrok_auth_token')


namespace_ngrok_ingress_controller_name = 'ngrok'

# Read the kubeconfig file
with open(kube_conf_path, 'r') as kubeconfig_file:
    kubeconfig = kubeconfig_file.read()

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


# define the helm chart
ingress_controller_chart = Chart(
    "kubernetes-ingress-controller",
    ChartOpts(
        chart="kubernetes-ingress-controller",
        version="0.12.1",
        fetch_opts=FetchOpts(
            repo="https://ngrok.github.io/kubernetes-ingress-controller",
            destination="downloaded-charts",
            untar=True,
            untar_dir="untarred"
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
            namespace_ngrok_ingress_controller
        ]
    )
)

pulumi.export('chart_version', ingress_controller_chart.urn)