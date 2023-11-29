import pulumi
import pulumi_rke as rke
from pulumi_kubernetes import Provider
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from pulumi_kubernetes.core.v1 import (
    Namespace,
    Service,
    Secret,
    PodTemplateSpecArgs,
    PodSpecArgs,
    ServiceAccount,
    ServiceSpecArgs,
    ServicePortArgs,
    ContainerArgs,
    ConfigMap
)
from pulumi_kubernetes.rbac.v1 import ClusterRole, ClusterRoleBinding, Role, RoleBinding
from pulumi_kubernetes.batch.v1 import Job
from pulumi_kubernetes.networking.v1 import IngressClass
from pulumi_kubernetes.admissionregistration.v1 import ValidatingWebhookConfiguration

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
    ingress={"provider": "none"},
    kubernetes_version="v1.26.4-rancher2-1",
    ssh_agent_auth=True
)

kubeconf = cluster.kube_config_yaml
print(kubeconf)
pulumi.export("kubeconfig", kubeconf)

# set up provider
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconf)

namespace_ingress_nginx_name = 'ingress-nginx'
ingress_nginx_ns = Namespace(
    "ingress-nginx-ns",
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cluster])
)

"""
SERVICE ACCOUNTS
"""
service_account_ingress_nginx_name = "ingress-nginx"
service_account_ingress_nginx = ServiceAccount(
    "ingress-nginx-sa",
    api_version="v1",
    kind="ServiceAccount",
    automount_service_account_token=True,
    metadata={
        "name": service_account_ingress_nginx_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ingress_nginx_ns])
)

service_account_ingress_admission_name = "ingress-nginx-admission"
service_account_ingress_nginx_admission = ServiceAccount(
    "ingress-nginx-admission-sa",
    api_version="v1",
    kind="ServiceAccount",
    automount_service_account_token=True,
    metadata={
        "name": service_account_ingress_admission_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ingress_nginx_ns])
)

"""
ROLES
"""
role_ingress_nginx = Role(
    "ingress-nginx-role",
    kind="Role",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_nginx_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    rules=[
        {
            "api_groups": [""],
            "resources": ["namespaces"],
            "verbs": ["get"],
        },
        {
            "api_groups": [""],
            "resources": ["configmaps", "pods", "secrets", "endpoints"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": [""],
            "resources": ["services"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": ["networking.k8s.io"],
            "resources": ["ingresses"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": ["networking.k8s.io"],
            "resources": ["ingresses/status"],
            "verbs": ["update"],
        },
        {
            "api_groups": ["networking.k8s.io"],
            "resources": ["ingressclasses"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": [""],
            "resource_names": ["ingress-nginx-leader"],
            "resources": ["configmaps"],
            "verbs": ["get", "update"],
        },
        {
            "api_groups": [""],
            "resources": ["configmaps"],
            "verbs": ["create"],
        },
        {
            "api_groups": ["coordination.k8s.io"],
            "resource_names": ["ingress-nginx-leader"],
            "resources": ["leases"],
            "verbs": ["get", "update"],
        },
        {
            "api_groups": ["coordination.k8s.io"],
            "resources": ["leases"],
            "verbs": ["create"],
        },
        {
            "api_groups": [""],
            "resources": ["events"],
            "verbs": ["create", "patch"],
        },
        {
            "api_groups": ["discovery.k8s.io"],
            "resources": ["endpointslices"],
            "verbs": ["get", "list", "watch"]
        },
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[service_account_ingress_nginx])
)

role_ingress_nginx_admission = Role(
    "ingress-nginx-admission-role",
    kind="Role",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_admission_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    rules=[
        {
            "api_groups": [""],
            "resources": ["secrets"],
            "verbs": ["get", "create", "list", "watch", "update"],
        }
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[service_account_ingress_nginx_admission])
)

"""
CLUSTER ROLES
"""

cluster_role_ingress_nginx = ClusterRole(
    "ingress-nginx-role-cluster",
    kind="ClusterRole",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    rules=[
        {
            "api_groups": [""],
            "resources": ["configmaps", "endpoints", "namespaces", "nodes", "pods", "secrets"],
            "verbs": ["list", "watch"],
        },
        {
            "api_groups": ["coordination.k8s.io"],
            "resources": ["leases"],
            "verbs": ["list", "watch"],
        },
        {
            "api_groups": [""],
            "resources": ["nodes"],
            "verbs": ["get"],
        },
        {
            "api_groups": [""],
            "resources": ["services"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": ["networking.k8s.io"],
            "resources": ["ingresses"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": [""],
            "resources": ["events"],
            "verbs": ["create", "patch"],
        },
        {
            "api_groups": ["networking.k8s.io"],
            "resources": ["ingresses/status"],
            "verbs": ["update"],
        },
        {
            "api_groups": ["networking.k8s.io"],
            "resources": ["ingressclasses"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "api_groups": ["discovery.k8s.io"],
            "resources": ["endpointslices"],
            "verbs": ["get", "list", "watch"]
        }
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[service_account_ingress_nginx])
)

cluster_role_ingress_nginx_admission = ClusterRole(
    "ingress-nginx-admission-role-cluster",
    kind="ClusterRole",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_admission_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    rules=[
        {
            "api_groups": ["admissionregistration.k8s.io"],
            "resources": ["validatingwebhookconfigurations"],
            "verbs": ["get", "update"],
        }
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[service_account_ingress_nginx_admission])
)

"""
SERVICE ACCOUNT ROLE BINDING
"""
role_binding_ingress_nginx = RoleBinding(
    "ingress-nginx-role-binding",
    kind="RoleBinding",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_nginx_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    role_ref={
        "api_group": "rbac.authorization.k8s.io",
        "kind": "Role",
        "name": service_account_ingress_nginx_name
    },
    subjects=[{
        "kind": "ServiceAccount",
        "name": service_account_ingress_nginx_name,
        "namespace": namespace_ingress_nginx_name
    }],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[role_ingress_nginx])
)

role_binding_ingress_nginx_admission = RoleBinding(
    "ingress-nginx-admission-role-binding",
    kind="RoleBinding",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_admission_name,
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    role_ref={
        "api_group": "rbac.authorization.k8s.io",
        "kind": "Role",
        "name": service_account_ingress_admission_name
    },
    subjects=[{
        "kind": "ServiceAccount",
        "name": service_account_ingress_admission_name,
        "namespace": namespace_ingress_nginx_name
    }],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[role_ingress_nginx_admission])
)

"""
CLUSTER ROLE BINDING
"""
cluster_role_binding_ingress_nginx = ClusterRoleBinding(
    "ingress-nginx-cluster-role-binding",
    kind="ClusterRoleBinding",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    role_ref={
        "api_group": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": namespace_ingress_nginx_name
    },
    subjects=[{
        "kind": "ServiceAccount",
        "name": namespace_ingress_nginx_name,
        "namespace": namespace_ingress_nginx_name
    }],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cluster_role_ingress_nginx])
)

cluster_role_binding_ingress_admission_nginx = ClusterRoleBinding(
    "ingress-nginx-admission-cluster-role-binding",
    kind="ClusterRoleBinding",
    api_version="rbac.authorization.k8s.io/v1",
    metadata={
        "name": service_account_ingress_admission_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    role_ref={
        "api_group": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": service_account_ingress_admission_name,
    },
    subjects=[{
        "kind": "ServiceAccount",
        "name": service_account_ingress_admission_name,
        "namespace": namespace_ingress_nginx_name
    }],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cluster_role_ingress_nginx_admission])
)

"""
CONFIG MAP
"""
config_map_ingress_nginx_controller = ConfigMap(
    "config-map-ingress-nginx-controller",
    api_version="v1",
    data={
        "allow-snippet-annotations": "true"
    },
    kind="ConfigMap",
    metadata={
        "name": "config-map-ingress-nginx-controller",
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[role_binding_ingress_nginx_admission])
)

"""
Ingress Controller
"""
ingress_class_nginx = IngressClass(
    "ingress-class-nginx",
    kind="IngressClass",
    api_version="networking.k8s.io/v1",
    metadata={
        "name": "nginx",
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    spec={
        "controller": "k8s.io/ingress-nginx"
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

""" 
JOBS 
"""
job_ingress_nginx_admission_create = Job(
    "job-ingress-nginx-controller-admission-create",
    api_version="batch/v1",
    kind="Job",
    metadata={
        "name": "ingress-nginx-admission-create",
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    # JobSpecArgs["template"] -> PodTemplateSpecArgs
    # PodTemplateSpecArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L17924C20-L17924C20
    # PodSpecArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L16957
    # ContainerArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L4367
    # PodSecurityContextArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L16125
    spec={
        "template": {  # PodTemplateSpecArgs
            "metadata": {
                "name": "ingress-nginx-admission-create",
                "namespace": namespace_ingress_nginx_name,
                "labels": {
                    "app.kubernetes.io/component": "admission-webhook",
                    "app.kubernetes.io/instance": namespace_ingress_nginx_name,
                    "app.kubernetes.io/name": namespace_ingress_nginx_name,
                    "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
                    "app.kubernetes.io/version": "1.5.1"
                }
            },
            "spec": {  # PodSpecArgs
                "containers": [{  # ContainerArgs
                    "args": [
                        "create",
                        "--host=ingress-nginx-controller-admission,ingress-nginx-controller-admission.$(POD_NAMESPACE).svc",
                        "--namespace=$(POD_NAMESPACE)",
                        "--secret-name=ingress-nginx-admission",
                    ],
                    "env": [
                        {  # EnvVarArgs
                            "name": "POD_NAMESPACE",
                            "value_from": {  # EnvVarSourceArgs
                                "field_ref": {  # ObjectFieldSelectorArgs
                                    "field_path": "metadata.namespace"
                                }
                            }
                        }
                    ],
                    "image": "registry.k8s.io/ingress-nginx/kube-webhook-certgen:v20220916-gd32f8c343@sha256:39c5b2e3310dc4264d638ad28d9d1d96c4cbb2b2dcfb52368fe4e3c63f61e10f",
                    "image_pull_policy": "IfNotPresent",
                    "name": "create",
                    "security_context": {  # SecurityContextArgs
                        "allow_privilege_escalation": True
                    }
                }],
                "node_selector": {"kubernetes.io/os": "linux"},
                "restart_policy": "OnFailure",
                "security_context": {  # PodSecurityContextArgs
                    "fs_group": 2000,
                    "run_as_non_root": True,
                    "run_as_user": 2000
                },
                "service_account_name": service_account_ingress_admission_name
            }
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[service_account_ingress_nginx_admission])
)

validating_webhook_conf_ingress_nginx = ValidatingWebhookConfiguration(
    "validating-webhook-conf-ingress-nginx",
    kind="ValidatingWebhookConfiguration",
    api_version="admissionregistration.k8s.io/v1",
    metadata={
        "name": service_account_ingress_admission_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    webhooks=[  # Sequence[ValidatingWebhookArgs]
        {
            "admission_review_versions": ["v1"],
            "client_config": {  # WebhookClientConfigArgs
                "service": {  # ServiceReferenceArgs
                    "name": "ingress-nginx-controller-admission",
                    "namespace": namespace_ingress_nginx_name,
                    "path": "/networking/v1/ingresses",
                }
            },
            "failure_policy": "Fail",
            "match_policy": "Equivalent",
            "name": "validate.nginx.ingress.kubernetes.io",
            "rules": [
                {  # RuleWithOperationsArgs
                    "api_groups": ["networking.k8s.io"],
                    "api_versions": ["v1"],
                    "operations": ["CREATE", "UPDATE"],
                    "resources": ["ingresses"],
                }
            ],
            "side_effects": "None"
        }
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[job_ingress_nginx_admission_create])
)

job_ingress_nginx_admission_patch = Job(
    "job-ingress-nginx-controller-admission-patch",
    api_version="batch/v1",
    kind="Job",
    metadata={
        "name": "ingress-nginx-admission-patch",
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "admission-webhook",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    # JobSpecArgs["template"] -> PodTemplateSpecArgs
    # PodTemplateSpecArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L17924C20-L17924C20
    # PodSpecArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L16957
    # ContainerArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L4367
    # PodSecurityContextArgs -> https://github.com/pulumi/pulumi-kubernetes/blob/master/sdk/python/pulumi_kubernetes/core/v1/_inputs.py#L16125
    spec={
        "template": {  # PodTemplateSpecArgs
            "metadata": {
                "name": "ingress-nginx-admission-patch",
                "namespace": namespace_ingress_nginx_name,
                "labels": {
                    "app.kubernetes.io/component": "admission-webhook",
                    "app.kubernetes.io/instance": namespace_ingress_nginx_name,
                    "app.kubernetes.io/name": namespace_ingress_nginx_name,
                    "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
                    "app.kubernetes.io/version": "1.5.1"
                }
            },
            "spec": {  # PodSpecArgs
                "containers": [{  # ContainerArgs
                    "args": [
                        "patch",
                        "--webhook-name=ingress-nginx-admission",
                        "--namespace=$(POD_NAMESPACE)",
                        "--patch-mutating=false",
                        "--secret-name=ingress-nginx-admission",
                        "--patch-failure-policy=Fail",
                    ],
                    "env": [
                        {  # EnvVarArgs
                            "name": "POD_NAMESPACE",
                            "value_from": {  # EnvVarSourceArgs
                                "field_ref": {  # ObjectFieldSelectorArgs
                                    "field_path": "metadata.namespace"
                                }
                            }
                        }
                    ],
                    "image": "registry.k8s.io/ingress-nginx/kube-webhook-certgen:v20220916-gd32f8c343@sha256:39c5b2e3310dc4264d638ad28d9d1d96c4cbb2b2dcfb52368fe4e3c63f61e10f",
                    "image_pull_policy": "IfNotPresent",
                    "name": "patch",
                    "security_context": {  # SecurityContextArgs
                        "allow_privilege_escalation": False
                    }
                }],
                "node_selector": {"kubernetes.io/os": "linux"},
                "restart_policy": "OnFailure",
                "security_context": {  # PodSecurityContextArgs
                    "fs_group": 2000,
                    "run_as_non_root": True,
                    "run_as_user": 2000
                },
                "service_account_name": service_account_ingress_admission_name
            }
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider,
                                depends_on=[job_ingress_nginx_admission_create, validating_webhook_conf_ingress_nginx])
)

app_deployment = Deployment(
    "deploy-ingress-nginx-controller",
    api_version="apps/v1",
    kind="Deployment",
    metadata={
        "name": "ingress-nginx-controller",
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    spec={  # DeploymentSpecArgs
        "min_ready_seconds": 0,
        "revision_history_limit": 10,
        "selector": {  # LabelSelectorArgs
            "match_labels": {
                "app.kubernetes.io/component": "controller",
                "app.kubernetes.io/instance": namespace_ingress_nginx_name,
                "app.kubernetes.io/name": namespace_ingress_nginx_name
            }
        },
        "template": {  # PodTemplateSpecArgs
            "metadata": {
                "labels": {
                    "app.kubernetes.io/component": "controller",
                    "app.kubernetes.io/instance": namespace_ingress_nginx_name,
                    "app.kubernetes.io/name": namespace_ingress_nginx_name,
                }
            },
            "spec": {  # PodSpecArgs
                "containers": [{  # ContainerArgs
                    "args": [
                        "/nginx-ingress-controller",
                        "--election-id=ingress-nginx-leader",
                        "--controller-class=k8s.io/ingress-nginx",
                        "--ingress-class=nginx",
                        "--configmap=$(POD_NAMESPACE)/ingress-nginx-controller",
                        "--validating-webhook=:8443",
                        "--validating-webhook-certificate=/usr/local/certificates/cert",
                        "--validating-webhook-key=/usr/local/certificates/key",
                    ],
                    "env": [
                        {  # EnvVarArgs
                            "name": "POD_NAME",
                            "value_from": {  # EnvVarSourceArgs
                                "field_ref": {  # ObjectFieldSelectorArgs
                                    "field_path": "metadata.name"
                                }
                            }
                        },
                        {  # EnvVarArgs
                            "name": "POD_NAMESPACE",
                            "value_from": {  # EnvVarSourceArgs
                                "field_ref": {  # ObjectFieldSelectorArgs
                                    "field_path": "metadata.namespace"
                                }
                            }
                        },
                        {  # EnvVarArgs
                            "name": "LD_PRELOAD",
                            "value": "/usr/local/lib/libmimalloc.so"
                        }
                    ],
                    "image": "registry.k8s.io/ingress-nginx/controller:v1.5.1@sha256:4ba73c697770664c1e00e9f968de14e08f606ff961c76e5d7033a4a9c593c629",
                    "image_pull_policy": "IfNotPresent",
                    "lifecycle": {  # LifecycleArgs
                        "pre_stop": {  # LifecycleHandlerArgs
                            "exec": {  # ExecActionArgs
                                "command": ["/wait-shutdown"]
                            }
                        }
                    },
                    "liveness_probe": {  # ProbeArgs
                        "failure_threshold": 5,
                        "http_get": {  # HTTPGetActionArgs
                            "path": "/healthz",
                            "port": 10254,
                            "scheme": "HTTP"
                        },
                        "initial_delay_seconds": 10,
                        "period_seconds": 10,
                        "success_threshold": 1,
                        "timeout_seconds": 1
                    },
                    "name": "controller",
                    "ports": [  # Sequence[ContainerPortArgs]
                        {"container_port": 80, "name": "http", "protocol": "TCP"},
                        {"container_port": 443, "name": "https", "protocol": "TCP"},
                        {"container_port": 8443, "name": "webhook", "protocol": "TCP"},
                    ],
                    "readiness_probe": {
                        "failure_threshold": 3,
                        "http_get": {  # HTTPGetActionArgs
                            "path": "/healthz",
                            "port": 10254,
                            "scheme": "HTTP"
                        },
                        "initial_delay_seconds": 10,
                        "period_seconds": 10,
                        "success_threshold": 1,
                        "timeout_seconds": 1
                    },
                    "resources": {  # ResourceRequirementsArgs
                        "requests": {
                            "cpu": "100m",
                            "memory": "90Mi"
                        }
                    },
                    "security_context": {
                        "allow_privilege_escalation": True,
                        "capabilities": {  # CapabilitiesArgs
                            "add": ["NET_BIND_SERVICE"],
                            "drop": ["ALL"],
                        },
                        "run_as_user": 101
                    },
                    "volume_mounts": [  # Sequence[VolumeMountArgs]
                        {"mount_path": "/usr/local/certificates/", "name": "webhook-cert", "read_only": True}
                    ]
                }],
                "dns_policy": "ClusterFirst",
                "node_selector": {
                    "kubernetes.io/os": "linux"
                },
                "service_account_name": service_account_ingress_nginx_name,
                "termination_grace_period_seconds": 300,
                "volumes": [  # Sequence[VolumeArgs]
                    {
                        "name": "webhook-cert",
                        "secret": {  # SecretVolumeSourceArgs
                            "secret_name": "ingress-nginx-admission"
                        }
                    }
                ]
            }
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[job_ingress_nginx_admission_patch])
)

"""
SERVICES
"""
service_ingress_nginx_controller = Service(
    "service-ingress-nginx-controller",
    api_version="v1",
    kind="Service",
    metadata={
        "name": "ingress-nginx-controller",
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    spec={
        "ip_families": ["IPv4"],
        "ip_family_policy": "SingleStack",
        "ports": [
            {
                "app_protocol": "http",
                "name": "http",
                "port": 80,
                "protocol": "TCP",
                "target_port": "http",
            },
            {
                "app_protocol": "https",
                "name": "https",
                "port": 443,
                "protocol": "TCP",
                "target_port": "https",
            }
        ],
        "selector": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
        },
        "type": "NodePort"
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[app_deployment])
)

service_ingress_nginx_controller_admission = Service(
    "service-ingress-nginx-controller-admission",
    api_version="v1",
    kind="Service",
    metadata={
        "name": "ingress-nginx-controller-admission",
        "namespace": namespace_ingress_nginx_name,
        "labels": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
            "app.kubernetes.io/part-of": namespace_ingress_nginx_name,
            "app.kubernetes.io/version": "1.5.1"
        }
    },
    spec={  # ServiceSpecArgs
        "ports": [
            {
                "app_protocol": "https",
                "name": "https-webhook",
                "port": 443,
                "target_port": "webhook",
            }
        ],
        "selector": {
            "app.kubernetes.io/component": "controller",
            "app.kubernetes.io/instance": namespace_ingress_nginx_name,
            "app.kubernetes.io/name": namespace_ingress_nginx_name,
        },
        "type": "ClusterIP"
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[app_deployment])
)
