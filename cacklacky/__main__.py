import os
import base64
from dotenv import load_dotenv
import pulumi
from pulumi_kubernetes import Provider as KUBE_Provider, apiextensions, certificates
from pulumi_kubernetes.core.v1 import Namespace, ResourceRequirementsArgs, VolumeArgs, \
    PersistentVolumeClaimVolumeSourceArgs, VolumeMountArgs, EnvFromSourceArgs
from pulumi_kubernetes.core.v1.outputs import Container, Secret
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs, StatefulSet
from pulumi_kubernetes.core.v1 import (
    ContainerPortArgs,
    ConfigMapVolumeSourceArgs,
    Pod,
    PodTemplateSpecArgs,
    PodSpecArgs,
    ConfigMap,
    ContainerArgs,
    ProbeArgs,
    Service,
    ServiceSpecArgs,
    ServicePortArgs,
    HTTPGetActionArgs,
    PersistentVolumeClaim,
    PersistentVolumeClaimSpecArgs,
    VolumeResourceRequirementsArgs,
    PodSecurityContextArgs,
    SecretVolumeSourceArgs
)
from pulumi_kubernetes.core.v1.outputs import VolumeMount, EnvVar, Volume, PersistentVolumeClaimVolumeSource, \
    ContainerPort, ConfigMapVolumeSource
from pulumi_kubernetes.meta.v1 import ObjectMetaArgs, LabelSelectorArgs
from pulumi_cloudflare import (
    Provider,
    Record,
    Tunnel,
    TunnelConfig,
    TunnelConfigConfigArgs,
    TunnelConfigConfigIngressRuleArgs,
)
from pulumi_kubernetes.meta.v1.outputs import LabelSelector
from trino.properties_configmap import coordinator_config_map, worker_config_map
from trino.properties_deployments import (
    trino_volume_claim_tmp_data_metadata,
    trino_volume_claim_tmp_data_spec_args
)

from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts

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

api_badge_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"{hostname}",
    path="/api",
    service=f"http://cackalacky-badge-api-service.{namespace_ckc}:80"
)

discord_bot_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"ckc-bot.{hostname}",
    service=f"http://cackalacky-discord-api.{namespace_ckc}:80"
)

prefix_host_specific_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"2048.{hostname}",
    service="http://game-2048-service.test-2048-game:80"
)

base_ckc_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    hostname=f"{hostname}",
    service=f"http://cackalacky-ui-service.{namespace_ckc}:80"
)

catch_all_ingress_rule = TunnelConfigConfigIngressRuleArgs(
    service="http://localhost:7891"
)

# Create the TunnelConfig resource using the ingress rule
tunnel_config = TunnelConfig(
    "tunnel-config",
    account_id=cloudflare_account_id,
    tunnel_id=tunnel.id,
    config=TunnelConfigConfigArgs(
        ingress_rules=[
            api_badge_ingress_rule,
            discord_bot_ingress_rule,
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

game2048_dns_record = Record(
    "2048-cackalacky-cname",
    zone_id=cloudflare_zone_id,
    name="2048",  # This is relative to the domain name associated with the zone. e.g. 'www.example.com'
    type="CNAME",
    value=tunnel.cname,
    proxied=True,
    opts=pulumi.ResourceOptions(provider=cloudflare_provider, depends_on=[tunnel], ignore_changes=["*"])
)

discord_bot_dns_record = Record(
    "discord-bot-cackalacky-cname",
    zone_id=cloudflare_zone_id,
    name="ckc-bot",  # This is relative to the domain name associated with the zone. e.g. 'www.example.com'
    type="CNAME",
    value=tunnel.cname,
    proxied=True,
    opts=pulumi.ResourceOptions(
        provider=cloudflare_provider,
        depends_on=[tunnel],
        ignore_changes=["*"]
    )
)

"""
K8S Specific Setup
 - The following will setup pods, containers, etc in the k8s cluster
"""
# Read the kubeconfig file
with open(kube_conf_path, 'r') as kubeconfig_file:
    kubeconfig = kubeconfig_file.read()

print(kubeconfig)
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
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_obj_ckc],
        ignore_changes=["*"]
    )
)

""" Longhorn & Redis """

# Create a PersistentVolumeClaim (PVC)
redis_pvc = PersistentVolumeClaim(
    "redis_pvc",
    metadata=ObjectMetaArgs(
        name="redis-pvc",
        namespace=namespace_ckc,
    ),
    spec=PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],
        storage_class_name="longhorn",
        resources=VolumeResourceRequirementsArgs(
            requests={
                "storage": "5Gi"
            }
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_obj_ckc])
)

metadata = ObjectMetaArgs(
    name="redis-server",
    namespace=namespace_ckc
)

# The container spec for the Redis server
container = {
    "name": "redis-server",
    "image": "redis",
    "args": ["--appendonly", "yes"],
    "ports": [ContainerPort(name="redis-server", container_port=6379)],
    "volume_mounts": [VolumeMount(name="lv-storage", mount_path="/data")],
    "env": [EnvVar(name="ALLOW_EMPTY_PASSWORD", value="yes")],
}

# Volumes that the pod will use
volume = Volume(
    name="lv-storage",
    persistent_volume_claim=PersistentVolumeClaimVolumeSource(claim_name="redis-pvc"),
)

spec = {
    "replicas": 1,
    "selector": LabelSelector(match_labels={"app": "redis-server"}),
    "template": {
        "metadata": {"labels": {"app": "redis-server", "name": "redis-server"}},
        "spec": {
            "containers": [container],
            "volumes": [volume],
        },
    },
}

# Creating the deployment resource
redis_deployment = Deployment(
    "redis-deployment",
    metadata=metadata,
    spec=spec,
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_obj_ckc, redis_pvc])
)

# Define the metadata for the Service
metadata = ObjectMetaArgs(
    annotations={
        "field.cattle.io/description": "This redis service connects to the ckc redis DB"
    },
    name="redis-svc",
    namespace=namespace_ckc
)

# Define the spec for the Service
service_spec = ServiceSpecArgs(
    ports=[
        ServicePortArgs(
            name="tcp",
            port=6379,
            protocol="TCP",
            target_port=6379
        )
    ],
    selector={
        "app": "redis-server"
    },
    session_affinity="None",
    type="ClusterIP"
)

# Create the Service using the metadata and spec defined above
redis_service = Service(
    "redis-service",
    metadata=metadata,
    spec=service_spec
)

# Export the name of the Service
pulumi.export('service_name', redis_service.metadata['name'])

# Export the name of the deployment
pulumi.export('deployment_name', redis_deployment.metadata['name'])
# Export the name of the PersistentVolumeClaim
pulumi.export('persistent_volume_claim_name', redis_pvc.metadata.apply(lambda meta: meta.name))

""" TRINO """
trino_conf_coordinator_map = coordinator_config_map(namespace_ckc)
trino_conf_worker_map = worker_config_map(namespace_ckc)

trino_conf_coordinator = ConfigMap(
    "trino-conf-coordinator",
    metadata=ObjectMetaArgs(
        name="trino-conf-coordinator",
        namespace=namespace_ckc
    ),
    data=trino_conf_coordinator_map,
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_obj_ckc])
)

trino_conf_worker = ConfigMap(
    "trino-conf-worker",
    metadata=ObjectMetaArgs(
        name="trino-conf-worker",
        namespace=namespace_ckc
    ),
    data=trino_conf_worker_map,
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_obj_ckc])
)

trino_volume_claim_template = PersistentVolumeClaim(
    "trino-volume-claim",
    metadata=trino_volume_claim_tmp_data_metadata,
    spec=trino_volume_claim_tmp_data_spec_args,
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_obj_ckc])
)

trino_volume_tmp_data = Volume(
    name="trino-tmp-data",
    persistent_volume_claim=PersistentVolumeClaimVolumeSource(
        claim_name="trino-tmp-data"
    )
)

"""
This works, but doesn't use any of the volumes I created...
TODO -> get the volumes mounted:
server.config.path => Defaults to "/etc/trino"
 - This has all of the configs
server.node.dataDir => Defaults to "/data/trino"

https://trinodb.github.io/charts/charts/trino/
"""
trino_chart = Chart(
    'trino',
    config=ChartOpts(
        namespace=namespace_ckc,
        chart='trino',
        version='0.19.0',
        fetch_opts=FetchOpts(
            repo='https://trinodb.github.io/charts',
        ),
        values={
            'image': {
                'tag': 443
            },
            'additionalCatalogs': {
                "hive": f"""
                    connector.name=hive
                    hive.metastore.uri=thrift://cackalacky-hive.{namespace_ckc}:9083
                    hive.s3.endpoint=s3.amazonaws.com
                    hive.s3.aws-access-key={os.getenv("HIVE_S3_IAM_ACCESS_KEY")}
                    hive.s3.aws-secret-key={os.getenv("HIVE_S3_IAM_SECRET_KEY")}
                """
            },
            'coordinator': {
                'resources': {
                    'requests': {
                        'cpu': '2',
                        'memory': '8Gi',
                    },
                    'limits': {
                        'cpu': '4',
                        'memory': '8Gi',
                    },
                },
                'additionalVolumes': [],
                'additionalVolumeMounts': []
            },
            'worker': {
                'replicas': 2,
                'resources': {
                    'requests': {
                        'cpu': '2',
                        'memory': '8Gi',
                    },
                    'limits': {
                        'cpu': '4',
                        'memory': '8Gi',
                    },
                },
                'additionalVolumes': [
                    # {
                    #     "name": "trino-tmp-data",
                    #     "persistentVolumeClaim": {"claimName": "trino-data"}
                    # }
                    # """
                    # - name: trino-tmp-data
                    #   persistentVolumeClaim:
                    #     claimName: trino-data
                    # """
                ],
                'additionalVolumeMounts': [
                    # {
                    #     "name": "trino-tmp-data",
                    #     "mountPath": "/tmp"
                    # }
                    # """
                    # - name: trino-tmp-data
                    #   mountPath: /tmp
                    # """
                ]
            }
        }
    )
)

"""
superset
"""
superset_chart = Chart(
    'superset',
    config=ChartOpts(
        namespace=namespace_ckc,
        chart='superset',
        version='0.12.7',
        fetch_opts=FetchOpts(
            repo='https://apache.github.io/superset',
        ),
        values={
            "configOverrides": {
                "secret": "SECRET_KEY = 'asdflqergu3458248935algbgasdf1324t354gf'"
            }
        }
    )
)

""" TODO -> MetalLB helm deploy """
# helm repo add metallb https://metallb.github.io/metallb
# helm repo refresh
metallb_version = "0.14.4"
metallb_namespace_str = "metallb-system"

namespace_metal_lb = Namespace(
    "metallb-namespace",
    metadata=ObjectMetaArgs(
        name=metallb_namespace_str,
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_obj_ckc]
    )
)

metal_lb_release = Chart(
    "metal-lb-release",
    config=ChartOpts(
        chart="metallb",
        version="v1.6.3",
        fetch_opts=FetchOpts(
            repo='https://metallb.github.io/metallb',
        ),
        namespace=namespace_metal_lb.metadata["name"]
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_metal_lb]
    )
)


""" TODO -> MetalLB custom resources: ip pool & L2 advertisements """
ip_range = "192.168.4.100-192.168.4.110"
ip_address_pool = apiextensions.CustomResource(
    "first-pool",
    api_version="metallb.io/v1beta1",
    kind="IPAddressPool",
    metadata={
        "name": "first-pool",
        "namespace": namespace_metal_lb.metadata["name"]
    },
    spec={
        "addresses": [ip_range]
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[metal_lb_release]
    )
)

l2_advertisement = apiextensions.CustomResource(
    "example-l2advertisement",
    api_version="metallb.io/v1beta1",
    kind="L2Advertisement",
    metadata={
        "name": "example",
        "namespace": namespace_metal_lb.metadata["name"]
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[metal_lb_release]
    )
)

""" NGinx Config Map """
nginx_config_data = {
    "default.conf": """\
    server {
        listen 80;
        server_name cackalacky.ninja www.cackalacky.ninja;
    
        # Redirect all traffic to HTTPS
        return 301 https://$host$request_uri;
    }
    server {
        listen 443 ssl;
        server_name cackalacky.ninja;
        
        resolver 10.43.0.10 valid=10s; # core dns service ip
    
        ssl_certificate /etc/nginx/certs/tls.crt;
        ssl_certificate_key /etc/nginx/certs/tls.key;
    
        location / {
            set $service_url http://cackalacky-badge-api-service.cackalacky.svc.cluster.local;
            proxy_pass $service_url;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    """,
    "nginx.conf": """\
    events {
        worker_connections 1024;
    }

    http {
        include       /etc/nginx/mime.types;
        default_type  application/octet-stream;

        include /etc/nginx/conf.d/*.conf;
    }"""
}

nginx_config = ConfigMap(
    "nginx-badge-config",
    metadata=ObjectMetaArgs(
        name="nginx-badge-config",
        namespace=namespace_ckc,
        annotations={
            "field.cattle.io/description": "config stuffsssss"
        }
    ),
    data=nginx_config_data,
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_obj_ckc]
    )
)

# Export the name of the ConfigMap
pulumi.export("configmap_name", nginx_config.metadata.name)

""" nginx image deploy to pod """
nginx_deployment = Deployment(
    "nginx-deployment",
    metadata=ObjectMetaArgs(
      namespace=namespace_ckc,
      name="nginx"
    ),
    spec=DeploymentSpecArgs(
        replicas=1,
        selector=LabelSelectorArgs(
            match_labels={"app": "nginx"}
        ),
        template=PodTemplateSpecArgs(
            metadata=ObjectMetaArgs(
                labels={"app": "nginx"}
            ),
            spec=PodSpecArgs(
                containers=[
                    ContainerArgs(
                        name="nginx",
                        image="nginx:1.19.0",
                        ports=[
                            ContainerPortArgs(container_port=80),
                            ContainerPortArgs(container_port=443)
                        ],
                        volume_mounts=[
                            VolumeMountArgs(
                                name="config-volume",
                                mount_path="/etc/nginx/nginx.conf",
                                sub_path="nginx.conf",
                            ),
                            VolumeMountArgs(
                                name="config-volume",
                                mount_path="/etc/nginx/conf.d/default.conf",
                                sub_path="default.conf",
                            ),
                            VolumeMountArgs(
                                name="cert-volume",
                                mount_path="/etc/nginx/certs",
                                read_only=True,
                            )
                        ]
                    )
                ],
                volumes=[
                    VolumeArgs(
                        name="config-volume",
                        config_map=ConfigMapVolumeSourceArgs(
                            name=nginx_config.metadata.name,
                        ),
                    ),
                    VolumeArgs(
                        name="cert-volume",
                        secret=SecretVolumeSourceArgs(
                            secret_name="ckc-badge-cert-secret-clone",
                        ),
                    )
                ],
            )
        )
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_obj_ckc]
    )
)


""" TODO -> Service that points to badge api with MetalLB annotation """
nginx_metallb_ckc_badge_api_service = Service(
    "nginx",
    metadata={
        "name": "nginx-badge",
        "annotations": {
            "metallb.universe.tf/loadBalancerIPs": "192.168.4.105"
        },
    },
    spec={
        "type": "LoadBalancer",
        "ports": [{
            "port": 80,
            "targetPort": 80,
        }],
        "selector": {
            "app": "nginx",
        },
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[
            nginx_deployment,
            l2_advertisement,
            ip_address_pool
        ]
    )
)

""" CERTS """
# I did the one click install in Rancher UI for cert manager and I regret it.
# install cert manager helm, installCRDs=true
# Here's the helm chart way...
"""
helm repo add jetstack https://charts.jetstack.io
helm repo update
"""
cert_manager_version = "1.6.3"
cert_manager_namespace_str = "cert-manager"

namespace_cert_manager = Namespace(
    "cert-manager-namespace",
    metadata=ObjectMetaArgs(
        name=cert_manager_namespace_str,
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_obj_ckc],
        additional_secret_outputs=["stringData"]
    )
)

# Deploy cert-manager using the Helm chart
cert_manager_release = Chart(
    "cert-manager-release",
    config=ChartOpts(
        chart="cert-manager",
        version="v1.6.3",
        fetch_opts=FetchOpts(
            repo='https://charts.jetstack.io',
        ),
        namespace=namespace_cert_manager.metadata["name"],
        values={"installCRDs": True},
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[namespace_cert_manager]
    )
)

test_secret = Secret(
    "cf-cert-manager-secret",
    api_version="v1",
    kind="Secret",
    metadata={
        "name": "cf-global-api-key",
        "namespace": namespace_cert_manager.metadata["name"]
    },
    type="Opaque",
    string_data={
        "api-key": os.getenv("CF_GLOBAL_API_KEY"),
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[cert_manager_release]
    )
)

letsencrypt_prod_cluster_issuer = apiextensions.CustomResource(
    "letsencrypt-prod-clusterissuer",
    api_version="cert-manager.io/v1",
    kind="ClusterIssuer",
    metadata={
        "name": "letsencrypt-prod",
        "namespace": namespace_cert_manager.metadata["name"]
    },
    spec={
        "acme": {
            "server": "https://acme-v02.api.letsencrypt.org/directory",
            "email": "alex.persinger@augmented.ninja",
            "privateKeySecretRef": {
                "name": "letsencrypt-prod"
            },
            "solvers": [{
                "dns01": {
                    "cloudflare": {
                        "email": "apfbacc@gmail.com",
                        "apiKeySecretRef": {
                            "name": test_secret.metadata['name'],
                            "key": "api-key"
                        }
                    }
                }
            }]
        }
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[cert_manager_release, test_secret]
    )
)

# Create a cert-manager.io/v1 Certificate
certificate = certificates.v1.Certificate(
    "ckc-badge-cert",
    metadata=ObjectMetaArgs(
        name="ckc-badge-cert",
        namespace=namespace_cert_manager.metadata["name"],
    ),
    spec=certificates.v1.CertificateSpecArgs(
        secret_name="ckc-badge-cert-secret",
        issuer_ref=certificates.v1.CertificateSpecIssuerRefArgs(
            name="letsencrypt-prod",
            kind="ClusterIssuer",
        ),
        dns_names=[
            "*.cackalacky.ninja",
            "cackalacky.ninja",
        ],
    )
)


pulumi.export('secret_name', test_secret.metadata['name'])
pulumi.export('cluster_issuer_name', letsencrypt_prod_cluster_issuer.metadata['name'])
pulumi.export('certificate_name', certificate.metadata.apply(lambda m: m.name))


"""
# DNS Validation - WORKS
apiVersion: v1
kind: Secret
metadata:
  name: testsecret
type: Opaque
stringData:
  api-key: <cf global api key>


apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
  namespace: default
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: alex.persinger@augmented.ninja
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - dns01:
        cloudflare:
          email: apfbacc@gmail.com
          apiKeySecretRef:
            name: testsecret
            key: api-key

  
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ckc-badge-cert
  namespace: default
spec:
  secretName: ckc-badge-cert-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - '*.cackalacky.ninja'
  - cackalacky.ninja
"""