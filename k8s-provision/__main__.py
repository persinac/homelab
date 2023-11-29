import pulumi
import pulumi_rke as rke

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

# Export kubeconfig
kubeconf = cluster.kube_config_yaml
pulumi.export("kubeconfig", kubeconf)

# # Define stack reference (replace "myOrg" and "myProject" with your organization and project names respectively)
# stack_ref = pulumi.StackReference("dev-k8s-stack")
#
# # Retrieve exported kubeconfig from the stack
# kubeconfig = stack_ref.get_output("kubeconfig")
# print(kubeconfig)
