# *****************************************************************************
# Copyright (c) 2026 IBM Corporation and other Contributors.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# *****************************************************************************

import logging
from unittest.mock import MagicMock

from kubernetes.dynamic.resource import ResourceField

from mas.devops import mas, aiservice
from mas.devops.ocp import listInstances

# -----------------------------------------------------------------------------
# WARNING: All tests must be written with strictly no external dependencies.
# Mocks must be used in place of any calls to OpenShift API etc.
# -----------------------------------------------------------------------------


def _storageClass(name, provisioner="example.com/provisioner", isDefault=False):
    annotations = {"storageclass.kubernetes.io/is-default-class": "true"} if isDefault else {}
    return ResourceField({"metadata": ResourceField({"name": name, "annotations": ResourceField(annotations)}), "provisioner": provisioner})


def _clientWithStorageClasses(storageClasses):
    storageClassApi = MagicMock()
    storageClassApi.get.return_value = MagicMock(items=storageClasses)
    client = MagicMock()
    client.resources.get.side_effect = lambda **kwargs: (
        storageClassApi if kwargs["api_version"] == "storage.k8s.io/v1" and kwargs["kind"] == "StorageClass" else None
    )
    return client


def _clientWithInstances(apiVersion, kind, instances):
    instanceApi = MagicMock()
    instanceApi.get.return_value.to_dict.return_value = {"items": instances}
    client = MagicMock()
    client.resources.get.side_effect = lambda **kwargs: instanceApi if kwargs["api_version"] == apiVersion and kwargs["kind"] == kind else None
    return client


def test_aws_without_efs_returns_no_rwx():
    """
    Given an AWS cluster with gp3-csi but no efs storage class
    When the default storage classes are detected
    Then rwo is gp3-csi and rwx is None (ibm-mas/cli#1520)
    """
    client = _clientWithStorageClasses([_storageClass("gp2-csi", "ebs.csi.aws.com"), _storageClass("gp3-csi", "ebs.csi.aws.com")])
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "aws"
    assert result.rwo == "gp3-csi"
    assert result.rwx is None


def test_aws_with_efs_returns_efs_rwx():
    """
    Given an AWS cluster with both gp3-csi and efs storage classes
    When the default storage classes are detected
    Then rwo is gp3-csi and rwx is efs
    """
    client = _clientWithStorageClasses([_storageClass("efs", "efs.csi.aws.com"), _storageClass("gp3-csi", "ebs.csi.aws.com")])
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "aws"
    assert result.rwo == "gp3-csi"
    assert result.rwx == "efs"


def test_azure_without_rwo_returns_no_rwo():
    """
    Given an Azure cluster with azurefiles-premium but no managed-premium storage class
    When the default storage classes are detected
    Then rwx is azurefiles-premium and rwo is None
    """
    client = _clientWithStorageClasses([_storageClass("azurefiles-premium")])
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "azure"
    assert result.rwo is None
    assert result.rwx == "azurefiles-premium"


def test_rook_ceph_detected_by_provisioner():
    """
    Given a cluster with Rook-Ceph RBD and CephFS storage classes with non-standard names
    When the default storage classes are detected
    Then RBD is used for RWO and CephFS for RWX (ibm-mas/cli#2634)
    """
    client = _clientWithStorageClasses(
        [
            _storageClass("local-path", "rancher.io/local-path"),
            _storageClass("rook-cephfs", "rook-ceph.cephfs.csi.ceph.com"),
            _storageClass("rook-ceph-block", "rook-ceph.rbd.csi.ceph.com"),
        ]
    )
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "rook-ceph"
    assert result.rwo == "rook-ceph-block"
    assert result.rwx == "rook-cephfs"


def test_rook_ceph_prefers_default_class():
    """
    Given a cluster with two Rook-Ceph RBD storage classes, the second annotated as the default
    When the default storage classes are detected
    Then the default RBD class is used for RWO and rwx is None as there is no CephFS class
    """
    client = _clientWithStorageClasses(
        [
            _storageClass("ceph-block-retain", "rook-ceph.rbd.csi.ceph.com"),
            _storageClass("ceph-block", "rook-ceph.rbd.csi.ceph.com", isDefault=True),
        ]
    )
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "rook-ceph"
    assert result.rwo == "ceph-block"
    assert result.rwx is None


def test_odf_custom_names_detected_by_provisioner():
    """
    Given an ODF cluster whose storage classes have non-default names
    When the default storage classes are detected
    Then they are detected by provisioner as an ODF provider
    """
    client = _clientWithStorageClasses(
        [
            _storageClass("my-rbd", "openshift-storage.rbd.csi.ceph.com"),
            _storageClass("my-cephfs", "openshift-storage.cephfs.csi.ceph.com"),
        ]
    )
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "ocs"
    assert result.rwo == "my-rbd"
    assert result.rwx == "my-cephfs"


def test_odf_well_known_names_take_precedence():
    """
    Given an ODF cluster with the standard ocs-storagecluster storage class names
    When the default storage classes are detected
    Then the name-based ocs provider is returned
    """
    client = _clientWithStorageClasses(
        [
            _storageClass("ocs-storagecluster-cephfs", "openshift-storage.cephfs.csi.ceph.com"),
            _storageClass("ocs-storagecluster-ceph-rbd", "openshift-storage.rbd.csi.ceph.com"),
        ]
    )
    result = mas.getDefaultStorageClasses(client)
    assert result.provider == "ocs"
    assert result.providerName == "OpenShift Container Storage"
    assert result.rwo == "ocs-storagecluster-ceph-rbd"
    assert result.rwx == "ocs-storagecluster-cephfs"


def test_unknown_storage_returns_none():
    """
    Given a cluster with no recognised storage classes
    When the default storage classes are detected
    Then all attributes are None
    """
    client = _clientWithStorageClasses([_storageClass("local-path", "rancher.io/local-path")])
    result = mas.getDefaultStorageClasses(client)
    assert result.provider is None
    assert result.providerName is None
    assert result.rwo is None
    assert result.rwx is None


def test_list_unreconciled_mas_instances_does_not_raise(caplog):
    """
    Given Suite CRs that have never reconciled (no status, empty status, null versions)
    When MAS instances are listed
    Then all instances are returned and logged with an unknown version (ibm-mas/cli#1944)
    """
    instances = [
        {"metadata": {"name": "inst1"}},
        {"metadata": {"name": "inst2"}, "status": {}},
        {"metadata": {"name": "inst3"}, "status": {"versions": None}},
        {"metadata": {"name": "inst4"}, "status": None},
        {"metadata": {"name": "inst5"}, "status": {"versions": {"reconciled": "9.1.0"}}},
    ]
    client = _clientWithInstances("core.mas.ibm.com/v1", "Suite", instances)
    with caplog.at_level(logging.INFO):
        result = mas.listMasInstances(client)
    assert result == instances
    assert " * inst1 vunknown" in caplog.text
    assert " * inst4 vunknown" in caplog.text
    assert " * inst5 v9.1.0" in caplog.text
    assert "There are no Suite instances" not in caplog.text


def test_list_unreconciled_aiservice_instances_does_not_raise():
    """
    Given an AIServiceApp CR that has never reconciled
    When AI Service instances are listed
    Then the instance is returned without raising
    """
    instances = [{"metadata": {"name": "aib1"}, "status": {"conditions": []}}]
    client = _clientWithInstances("aiservice.ibm.com/v1", "AIServiceApp", instances)
    assert aiservice.listAiServiceInstances(client) == instances


def test_list_no_instances(caplog):
    """
    Given no instances of a custom resource
    When instances are listed
    Then an empty list is returned and the "no instances" message is logged
    """
    client = _clientWithInstances("core.mas.ibm.com/v1", "Suite", [])
    with caplog.at_level(logging.INFO):
        assert listInstances(client, "core.mas.ibm.com/v1", "Suite") == []
    assert "There are no Suite instances" in caplog.text
