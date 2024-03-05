import os
import base64
from dotenv import load_dotenv
import pulumi
from pulumi_kubernetes import Provider as KUBE_Provider
from pulumi_kubernetes.core.v1 import Namespace
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from pulumi_kubernetes.core.v1 import (
    PodTemplateSpecArgs,
    PodSpecArgs,
    ContainerArgs,
    ProbeArgs,
    HTTPGetActionArgs
)
from pulumi_kubernetes.meta.v1 import ObjectMetaArgs, LabelSelectorArgs
from pulumi_cloudflare import (
    Provider,
    Record,
    Tunnel,
    TunnelConfig,
    TunnelConfigConfigArgs,
    TunnelConfigConfigIngressRuleArgs,
)

# load env vars
load_dotenv()
kube_conf_path = os.getenv('kube_conf_path')
cloudflare_tunnel_secret = os.getenv('cloudflare_tunnel_secret')
cloudflare_account_id = os.getenv('cloudflare_account_id')
cloudflare_zone_id = os.getenv('cloudflare_zone_id')
hostname = os.getenv('hostname')

# Set the namespace here so we can reference
namespace_ckc = "cackalacky"

"""
Cloudflare Specific setup
 - The following will configure objects on the cloudflare side
"""
# Set the API token using the pulumi.Config object
config = pulumi.Config()
cloudflare_api_token = config.require_secret('cloudflareApiToken')

# Create a Cloudflare provider instance with the API token
cloudflare_provider = Provider(
    'cloudflareProvider',
    api_token=cloudflare_api_token
)

# Convert raw secret to base64
cloudflare_tunnel_secret_base64_encoded = base64.b64encode(cloudflare_tunnel_secret.encode("utf-8"))
cloudflare_tunnel_secret_base64_encoded_str = str(cloudflare_tunnel_secret_base64_encoded, "utf-8")

# Create a new Cloudflare Tunnel resource
tunnel = Tunnel(
    "cloudflare-cackalacky-tunnel",
    name="cloudflare-cackalacky-tunnel",
    secret=cloudflare_tunnel_secret_base64_encoded_str,
    account_id=cloudflare_account_id,
    config_src="cloudflare",
    opts=pulumi.ResourceOptions(
        provider=cloudflare_provider
    )
)

catch_all_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    service="http://localhost:7891"
)

host_specific_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=hostname,
    service="http://game-2048-service.test-2048-game:80"
)

prefix_host_specific_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"2048.{hostname}",
    service="http://game-2048-service.test-2048-game:80"
)

base_ckc_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"{hostname}",
    service=f"http://cackalacky-fe-service.{namespace_ckc}:80"
)

api_badge_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"{hostname}",
    path="/api",
    service=f"http://cackalacky-badge-api-service.{namespace_ckc}:80"
)

# Create the TunnelConfig resource using the ingress rule
tunnel_config = TunnelConfig(
    "tunnel-config",
    account_id=cloudflare_account_id,
    tunnel_id=tunnel.id,
    config=TunnelConfigConfigArgs(
        ingress_rules=[
            api_badge_ingress_rule,
            prefix_host_specific_ingress_rule,
            base_ckc_ingress_rule,
            # prefix_host_specific_ingress_rule,
            # Bad Configuration: The last ingress rule must match all URLs (i.e. it should not have a hostname or path filter)
            catch_all_ingress_rule
        ]
    ),
    opts=pulumi.ResourceOptions(
        provider=cloudflare_provider
    )
)

pulumi.export('tunnel_token', pulumi.Output.secret(tunnel.tunnel_token))
pulumi.export("tunnel_id", tunnel.id)
pulumi.export("tunnel_cname", tunnel.cname)

# Create a DNS CNAME record for your hostname pointing to the tunnel IP.
root_dns_record = Record(
    "root-cackalacky-cname",
    zone_id=cloudflare_zone_id,
    name="@",  # @ corresponds to the domain - this is specific to cloudflare in what they call CNAME flattening
    type="CNAME",
    value=tunnel.cname,  # Replace with the desired destination IP address.
    proxied=True,
    opts=pulumi.ResourceOptions(provider=cloudflare_provider, depends_on=[tunnel])
)

# Create a WWW DNS CNAME record for your hostname pointing to the tunnel IP.
www_dns_record = Record(
    "www-cackalacky-cname",
    zone_id=cloudflare_zone_id,
    name="www",  # This is relative to the domain name associated with the zone. e.g. 'www.example.com'
    type="CNAME",
    value=tunnel.cname,
    proxied=True,
    opts=pulumi.ResourceOptions(provider=cloudflare_provider, depends_on=[tunnel])
)

"""
K8S Specific Setup
 - The following will setup pods, containers, etc in the k8s cluster
"""
# Read the kubeconfig file
with open(kube_conf_path, 'r') as kubeconfig_file:
    kubeconfig = kubeconfig_file.read()

# set up provider
k8s_provider = KUBE_Provider("k8s-provider", kubeconfig=kubeconfig)

namespace_ckc = "cackalacky"
namespace_obj_ckc = Namespace(
    namespace_ckc,
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_ckc,
        "labels": {
            "app.kubernetes.io/instance": namespace_ckc,
            "app.kubernetes.io/name": namespace_ckc
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[tunnel])
)

# Define the cloudflared Deployment
cloudflared_labels = {"app": "cloudflared", "pod": "cloudflared"}
cloudflared_deployment = Deployment(
    "cloudflared-deployment",
    metadata=ObjectMetaArgs(
        labels=cloudflared_labels,
        name="cloudflared-deployment",
        namespace=namespace_ckc,
    ),
    spec=DeploymentSpecArgs(
        replicas=2,
        selector=LabelSelectorArgs(
            match_labels={"pod": "cloudflared"},
        ),
        template=PodTemplateSpecArgs(
            metadata=ObjectMetaArgs(
                labels={"pod": "cloudflared"},
            ),
            spec=PodSpecArgs(
                containers=[ContainerArgs(
                    command=["cloudflared", "tunnel", "--metrics", "0.0.0.0:2000", "run"],
                    args=["--token", tunnel.tunnel_token],
                    image="cloudflare/cloudflared:latest",
                    name="cloudflared",
                    liveness_probe=ProbeArgs(
                        http_get=HTTPGetActionArgs(
                            path="/ready",
                            port=2000,
                        ),
                        failure_threshold=1,
                        initial_delay_seconds=10,
                        period_seconds=10,
                    ),
                )],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_obj_ckc])
)
