import pulumi
import pulumi_rke as rke
import pulumi_docker as docker
import pulumi_command as command
# pulumi state delete --target-dependents
with open('C:\\homelab\\alex-ser-1', 'r') as file:
    node_1_ssh_key = file.read()

# Define nodes for the cluster
node = rke.ClusterNodeArgs(
    address="100.69.154.17",
    user="alex",
    ssh_key=node_1_ssh_key,
    roles=["controlplane", "etcd", "worker"],
    labels={
        "node": "alex-ser-1"
    }
)

# Define the RKE cluster configuration
cluster = rke.Cluster(
    "homelab-cluster",
    nodes=[node],
    cluster_name="homelab-single-node",
    enable_cri_dockerd=True,
    ingress={
        "dns_policy": "Default",
        "network_mode": "hostNetwork",
        "provider": "nginx"
    },
    kubernetes_version="v1.26.4-rancher2-1",
    ssh_agent_auth=True
)

# Export kubeconfig
kubeconf = cluster.kube_config_yaml
pulumi.export("kubeconfig", kubeconf)

# Define remote server connection details
connection = command.remote.ConnectionArgs(
    host="100.69.154.17",
    user="alex",
    private_key=node_1_ssh_key
)

# Define the Docker image for Rancher on the remote server
rancher_image = docker.RemoteImage("rancher-image", name="rancher/rancher:latest")

# Define the command to run Docker container using the image on the remote server
rancher_container_command = command.remote.Command(
    "rancher-container-command",
    create=f"docker run -d --privileged --restart=unless-stopped -p 80:80 -p 443:443 --name rancher rancher/rancher:latest",
    delete="docker stop rancher && docker rm rancher",
    connection=connection,
    opts=pulumi.ResourceOptions(
        depends_on=[
            rancher_image
        ]
    )
)

# Export the command result, which includes stdout and stderr
pulumi.export("command_result", rancher_container_command)
