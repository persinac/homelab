from pulumi_kubernetes.core.v1 import (
    PodSecurityContextArgs,
    PodSpecArgs,
    ContainerPortArgs,
    ContainerArgs,
    ConfigMapVolumeSourceArgs,
    ServiceSpecArgs,
    ServicePortArgs,
    PersistentVolumeClaimSpecArgs,
    VolumeResourceRequirementsArgs,
    ResourceRequirementsArgs
)
from pulumi_kubernetes.core.v1.outputs import VolumeMount, Volume, ConfigMapVolumeSource, Container, \
    PersistentVolumeClaimVolumeSource
from pulumi_kubernetes.meta.v1 import ObjectMetaArgs

namespace_ckc = "cackalacky"
trino_image = "trinodb/trino:443"

""" SERVICE """
trino_service_metadata = ObjectMetaArgs(
    annotations={
        "field.cattle.io/description": "This trino service connects to the ckc trino DB"
    },
    name="trino-svc",
    namespace=namespace_ckc
)

# Define the spec for the Service
trino_service_spec = ServiceSpecArgs(
    ports=[
        ServicePortArgs(
            name="tcp",
            port=8080,
            protocol="TCP",
            target_port=8080
        )
    ],
    selector={
        "app": "trino-coordinator"
    },
    session_affinity="None",
    type="ClusterIP"
)

""" POD """
trino_cli_pod_metadata = ObjectMetaArgs(
    name="trino-cli",
    namespace=namespace_ckc
)

trino_cli_pod_spec_args = PodSpecArgs(
    containers=[
        ContainerArgs(
            name="trino-cli",
            image=trino_image,
            command=["tail", "-f", "/dev/null"],
            image_pull_policy="Always",
        )
    ],
    restart_policy="Always"
)

""" VOLUME CLAIM """
trino_volume_claim_tmp_data_metadata = ObjectMetaArgs(
    name="trino-data",
    namespace=namespace_ckc
)

trino_volume_claim_tmp_data_spec_args = PersistentVolumeClaimSpecArgs(
    storage_class_name="longhorn",
    access_modes=["ReadWriteOnce"],
    resources=VolumeResourceRequirementsArgs(
        requests={
            "storage": "200Gi"
        }
    )
)

""" VOLUME MOUNTS """
trino_volume_mounts = [
    VolumeMount(
        name="trino-cfg-vol",
        mount_path="/etc/trino/jvm.config",
        sub_path="jvm.config"
    ),
    VolumeMount(
        name="trino-cfg-vol",
        mount_path="/etc/trino/config.properties",
        sub_path="config.properties.worker"
    ),
    VolumeMount(
        name="trino-cfg-vol",
        mount_path="/etc/trino/catalog/hive.properties",
        sub_path="hive.properties"
    ),
    VolumeMount(
        name="trino-cfg-vol",
        mount_path="/etc/trino/catalog/pgsql.properties",
        sub_path="pgsql.properties"
    ),
    VolumeMount(
        name="trino-tmp-data",
        mount_path="/tmp"
    ),
]

""" COORDINATOR """
trino_coordinator_metadata = ObjectMetaArgs(
    name="trino-coordinator",
    namespace=namespace_ckc
)

trino_coordinator_spec = {
    "selector": {
        "matchLabels": {
            "app": "trino-coordinator"
        }
    },
    "strategy": {
        "type": "Recreate"
    },
    "template": {
        "metadata": {
            "labels": {
                "app": "trino-coordinator"
            }
        },
        "spec": {
            "containers": [
                {
                    "name": "trino",
                    "image": trino_image,
                    "ports": [ContainerPortArgs(container_port=8080)],
                    "volume_mounts": trino_volume_mounts,
                    "resources": ResourceRequirementsArgs(
                        requests={
                            "memory": "2G",
                            "cpu": 1
                        }
                    ),
                    "image_pull_policy": "Always"
                }
            ],
            "volumes": [
                {
                    "name": "trino-cfg-vol",
                    "configMap": ConfigMapVolumeSource(name="trino-configs")
                },
                Volume(
                    name="trino-tmp-data",
                    persistent_volume_claim=PersistentVolumeClaimVolumeSource(
                        claim_name="trino-volume-claim"
                    )
                )
            ]
        }
    }
}

""" WORKER """
trino_worker_stateful_set_metadata = ObjectMetaArgs(
    name="trino-worker",
    namespace=namespace_ckc
)

trino_worker_stateful_set_pod_security = PodSecurityContextArgs(
    fs_group=1000
)

trino_worker_cfg_volume = Volume(
    name="trino-cfg-vol",
    config_map=ConfigMapVolumeSource(
        name="trino-configs"
    )
)

trino_worker_stateful_set_container = {
    "name": "trino",
    "image": trino_image,
    "ports": [ContainerPortArgs(container_port=8080)],
    "volume_mounts": trino_volume_mounts,
    "resources": ResourceRequirementsArgs(
        requests={
            "memory": "4Gi",
            "cpu": "1"
        }
    ),
    "image_pull_policy": "Always"
}
