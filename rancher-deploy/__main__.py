import pulumi
from pulumi_kubernetes import Provider
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts, LocalChartOpts
from pulumi_kubernetes.core.v1 import Namespace, Secret
from pulumi_kubernetes.yaml import ConfigFile

# Define stack referenceF
stack_ref = pulumi.StackReference("persinac/k8s-provision/dev-k8s-stack")

# Retrieve exported kubeconfig from the stack
kubeconfig = stack_ref.get_output("kubeconfig")
print(kubeconfig)

# set up provider
k8s_provider = Provider("k8s-provider", kubeconfig=kubeconfig)

# Create the cattle-system namespace
namespace_cattle_system_name = 'cattle-system'
namespace_cattle_system = Namespace(
    f"{namespace_cattle_system_name}-ns",
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_cattle_system_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_cattle_system_name,
            "app.kubernetes.io/name": namespace_cattle_system_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)


# Apply cert-manager CRDs
cert_manager_crds = ConfigFile(
    "cert-manager-crds",
    file="https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.crds.yaml",
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Create the cert-manager namespace
namespace_cert_manager_name = 'cert-manager'
namespace_cert_manager = Namespace(
    f"{namespace_cert_manager_name}-ns",
    kind="Namespace",
    api_version="v1",
    metadata={
        "name": namespace_cert_manager_name,
        "labels": {
            "app.kubernetes.io/instance": namespace_cert_manager_name,
            "app.kubernetes.io/name": namespace_cert_manager_name
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert_manager_crds])
)

# create the secret - I was having issues with the helm chart deploying this.
# So, I extracted it out and made this secret a dependency of the primary deployment
bootstrap_secret = Secret(
    "bootstrap-secret",
    metadata={
        "namespace": namespace_cattle_system_name,
        "name": "bootstrap-secret"
    },
    data={
        "bootstrapPassword": "password"  # Your password encoded in Base64
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace_cattle_system])
)

# Install cert-manager from the jetstack Helm repository
cert_manager_chart = Chart(
    "cert-manager",
    ChartOpts(
        chart="cert-manager",
        version="1.13.2",  # Specify the version of cert-manager chart
        fetch_opts=FetchOpts(
            repo="https://charts.jetstack.io"
        ),
        namespace=namespace_cattle_system_name
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert_manager_crds, namespace_cattle_system])
)

# define the local tarball helm chart
local_rancher_chart_path = "./rancher-2.7.9.tgz"
rancher_chart = Chart(
    "rancher",
    LocalChartOpts(
        path=local_rancher_chart_path,
        namespace=namespace_cattle_system_name,
        values={
            "hostname": "nginx.rhino-augmented.ts.net",
            "replicas": 1
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert_manager_chart, bootstrap_secret])
)

# Export the Rancher chart name
pulumi.export("rancher_chart", rancher_chart._name)

# Output the names of the created namespaces
pulumi.export("cattle_system_namespace", namespace_cattle_system_name)
pulumi.export("cert_manager_namespace", namespace_cattle_system_name)
