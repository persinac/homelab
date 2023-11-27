import pulumi
import pulumi_rke as rke
from pulumi_kubernetes import Provider
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Namespace, Service, Secret
from pulumi_kubernetes.apiextensions.v1 import CustomResourceDefinition
from pulumi_kubernetes.apiextensions import CustomResource
from pulumi_kubernetes.yaml import ConfigFile
from pulumi_kubernetes_cert_manager import CertManager, ReleaseArgs

with open('C:\\homelab\\id_rsa', 'r') as file:
    ssh_key = file.read()

# Define nodes for the cluster
node = rke.ClusterNodeArgs(
    address="100.117.77.150",
    user="alex-ser-1",
    ssh_key=ssh_key,
    roles=["controlplane", "etcd", "worker"]
)

# Define the RKE cluster configuration
cluster = rke.Cluster(
    "testing-cluster",
    nodes=[node],
    cluster_name="test-1",
    enable_cri_dockerd=True,
    kubernetes_version="v1.26.4-rancher2-1",
    ssh_agent_auth=True
)

kubeconf = cluster.kube_config_yaml
print(kubeconf)
pulumi.export("kubeconfig", kubeconf)

# set up provider
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconf)

# Set up cert-manager CRDs
# crds = ConfigFile(
#     name="cert-manager-crds",
#     file="https://raw.githubusercontent.com/jetstack/cert-manager/release-0.11/deploy/manifests/00-crds.yaml",
#     opts=pulumi.ResourceOptions(provider=k8s_provider)
# )


# setup cert-manager
ns_name = 'dev-cert-manager'
namespace = Namespace(
    'dev-cert-manager-ns',
    metadata={
        "name": ns_name,
        "labels": {
            "certmanager.k8s.io/disable-validation": "true"
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cluster])
)

manager = CertManager('cert-manager',
    install_crds=True,
    helm_options=ReleaseArgs(
        namespace=ns_name,
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace])
)

# cert-manager clusterIssuer
# cluster_issuer = CustomResource(
#     "letsencrypt-staging",
#     api_version="cert-manager.io/v1",
#     kind="Issuer",
#     metadata={
#         "name": "letsencrypt-staging",
#         "namespace": namespace.metadata["name"]
#     },
#     spec={
#         "acme": {
#             "email": "apfbacc@gmail.com",
#             "server": "https://acme-v02.api.letsencrypt.org/directory",
#             "privateKeySecretRef": {
#                 "name": "letsencrypt-staging"
#             },
#             "solvers": [{
#                 "http01": {
#                     "ingress": {
#                         "class": "nginx"
#                     }
#                 }
#             }]
#         }
#     },
#     opts=pulumi.ResourceOptions(provider=k8s_provider),
# )
#
# # Create a TLS certificate
# cert = CustomResource(
#     "tls-certificate",
#     api_version="cert-manager.io/v1",
#     kind="Certificate",
#     metadata={"name": "test-certificate", "namespace": "dev"},
#     spec={
#         "secretName": "test-certificate",
#         "dnsNames": ["rhino-augmented.ts.net"],
#         "acme": {
#             "config": [
#                 {
#                     "http01": {
#                         "ingressClass": "nginx"
#                     },
#                     "domains": ["rhino-augmented.ts.net"]
#                 }
#             ]
#         },
#         "issuerRef": {
#             "name": "letsencrypt-staging",
#             "kind": "ClusterIssuer"
#         }
#     },
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cluster_issuer]))
#
# # Deploy Nginx Ingress
# ingress = Deployment(
#     "nginx-ingress",
#     metadata={
#         "namespace": "dev",
#         "name": "demo"
#     },
#     spec={
#         "replicas": 1,
#         "selector": {
#             "matchLabels": {
#                 "app.kubernetes.io/name": "demo",
#                 "app.kubernetes.io/part-of": "demo"
#             }
#         },
#         "template": {
#             "metadata": {
#                 "labels": {
#                     "app.kubernetes.io/name": "demo",
#                     "app.kubernetes.io/part-of": "demo"
#                 },
#                 "annotations": {
#                     "nginx.ingress.kubernetes.io/ssl-redirect": "true"  # Redirects http to https.
#                 }
#             },
#             "spec": {
#                 "containers": [{
#                     "name": "nginx",
#                     "image": "nginx:1.14.2",
#                     "ports": [
#                         {"name": "http", "containerPort": 80},
#                         {"name": "https", "containerPort": 443}
#                     ],
#                     "volumeMounts": [{
#                         "mountPath": "/etc/nginx/ssl",
#                         "name": "tls-certificate"
#                     }]
#                 }],
#                 "volumes": [{
#                     "name": "tls-certificate",
#                     "secret": {
#                         "secretName": cert.spec.apply(lambda spec: spec["secretName"])
#                     },
#                 }]
#             }
#         }
#     },
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert])
# )
#
# ingress_service = Service(
#     "demo-service",
#     metadata={
#         "namespace": "dev",
#         "name": "demo"
#     },
#     spec={
#         "selector": ingress.spec["template"]["metadata"]["labels"],
#         "ports": [
#             {"name": "http", "port": 80, "targetPort": 80},
#             {"name": "https", "port": 443, "targetPort": 443}
#         ],
#         "type": "LoadBalancer"
#     },
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ingress])
# )

# pulumi.export("ingress_ip", ingress_service.status.apply(lambda s: s['loadBalancer']['ingress'][0]['ip']))
