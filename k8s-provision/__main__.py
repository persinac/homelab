import pulumi
import pulumi_docker as docker
import pulumi_command as command
# pulumi state delete --target-dependents
with open('C:\\homelab\\alex-ser-1', 'r') as file:
    node_1_ssh_key = file.read()


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

"""
Once rancher UI is deployed, I manually provision k8s cluster and create the appropriate nodes.
This was due to rke limitations for v1 and provisioning networking for talking to multi nodes.
"""

# Export the command result, which includes stdout and stderr
pulumi.export("command_result", rancher_container_command)
