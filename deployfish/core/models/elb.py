import builtins
import fnmatch
import re
from collections.abc import Sequence
from typing import Any

from .abstract import Manager, Model
from .ec2 import Instance
from .mixins import TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class ClassicLoadBalancerManager(Manager):
    """
    Model classic load balancer manager behavior.
    """
    #: Service.
    service = "elb"

    def get(self, pk: str, **_) -> "ClassicLoadBalancer":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        instances = self.get_many([pk])
        if len(instances) > 1:
            msg = f"Got more than one load balancer when searching for pk={pk}"
            raise ClassicLoadBalancer.MultipleObjectsReturned(msg)
        return instances[0]

    def get_many(self, pks: list[str], **kwargs) -> Sequence["ClassicLoadBalancer"]:
        """
        Get many.

        Args:
            pks: pks.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.
        """
        kwargs = {"LoadBalancerNames": pks}
        paginator = self.client.get_paginator("describe_load_balancers")
        response_iterator = paginator.paginate(**kwargs)
        lbs = []
        try:
            for response in response_iterator:
                lbs.extend(response["LoadBalancerDescriptions"])
        except self.client.exceptions.AccessPointNotFoundException as e:
            msg = e.args[0]
            lbname = "Unknown"
            m = re.search(r"Cannot find Load Balancer (?P<lbname>[0-9A-Za-z]+)", msg)
            if m:
                lbname = m.group("lbname")
            msg_0 = f'No Classic Load Balancer with name "{lbname}" exists in AWS'
            raise ClassicLoadBalancer.DoesNotExist(msg_0)
        return [ClassicLoadBalancer(lb) for lb in lbs]

    def list(
        self, vpc_id: str | None = None, scheme: str = "any", name: str | None = None
    ) -> Sequence["ClassicLoadBalancer"]:
        """
        List.

        Args:
            vpc_id: vpc id.
            scheme: scheme.
            name: name.

        Returns:
            Operation result.
        """
        paginator = self.client.get_paginator("describe_load_balancers")
        response_iterator = paginator.paginate()
        lb_data = []
        for response in response_iterator:
            try:
                lb_data.extend(response["LoadBalancerDescriptions"])
            except self.client.exceptions.AccessPointNotFoundException as e:
                msg = e.args[0]
                lbname = "Unknown"
                m = re.search(
                    r"Cannot find Load Balancer (?P<lbname>[0-9A-Za-z]+)", msg
                )
                if m:
                    lbname = m.group("lbname")
                msg_0 = f'No Classic Load Balancer with name "{lbname}" exists in AWS'
                raise ClassicLoadBalancer.DoesNotExist(msg_0)
        lbs = []
        for lb in lb_data:
            if name and not fnmatch.fnmatch(lb["LoadBalancerName"], name):
                continue
            if vpc_id and lb["VPCId"] != vpc_id:
                continue
            if scheme not in ["any", lb["Scheme"]]:
                continue
            lbs.append(ClassicLoadBalancer(lb))
        return lbs

    def get_tags(self, pk: str) -> builtins.list[dict[str, str]]:
        """
        Get tags.

        Args:
            pk: pk.

        Returns:
            Operation result.
        """
        response = self.client.describe_tags(LoadBalancerName=pk)
        return response["TagDescriptions"]["Tags"]


class ClassicLoadBalancerTargetManager(Manager):
    """
    Model classic load balancer target manager behavior.
    """
    #: Service.
    service = "elb"

    def list(self, load_balancer_name: str) -> Sequence["ClassicLoadBalancerTarget"]:
        """
        List.

        Args:
            load_balancer_name: load balancer name.

        Returns:
            Operation result.
        """
        try:
            response = self.client.describe_instance_health(
                LoadBalancerName=load_balancer_name
            )
        except self.client.exceptions.AccessPointNotFoundException:
            msg = f'No Classic Load Balancer named "{load_balancer_name}" exists in AWS'
            raise ClassicLoadBalancer.DoesNotExist(msg)
        targets = []
        for data in response["InstanceStates"]:
            instance = Instance.objects.get(data["InstanceId"])
            targets.append(ClassicLoadBalancerTarget(data, instance))
        return targets


# ----------------------------------------
# Models
# ----------------------------------------


class ClassicLoadBalancer(TagsMixin, Model):
    """
    Model classic load balancer behavior.
    """
    #: Objects.
    objects = ClassicLoadBalancerManager()

    #: Lb type.
    lb_type: str = "Classic (ELB)"

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.name

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.data["LoadBalancerName"]

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    # ---------------------------------------
    # ClassicLoadBalancer-specific properties
    # ---------------------------------------

    @property
    def scheme(self) -> str:
        """
        Scheme.

        Returns:
            Operation result.
        """
        return self.data["Scheme"]

    @property
    def hostname(self) -> str:
        """
        Hostname.

        Returns:
            Operation result.
        """
        return self.data["DNSName"]

    @property
    def listeners(self) -> list[str]:
        """
        Listeners.

        Returns:
            Operation result.
        """
        return [listener["Listener"] for listener in self.data["ListenerDescriptions"]]

    @property
    def ssl_certificate_arn(self) -> str | None:
        """
        Ssl certificate arn.

        Returns:
            Operation result.
        """
        cert_id = None
        for listener in self.data["ListenerDescriptions"]:
            if (
                "SSLCertificateId" in listener["Listener"]
                and listener["Listener"]["SSLCertificateId"]
            ):
                cert_id = listener["Listener"]["SSLCertificateId"]
        return cert_id

    @property
    def ssl_policy(self) -> str | None:
        """
        Ssl policy.

        Returns:
            Operation result.
        """
        cert_id = None
        for listener in self.data["ListenerDescriptions"]:
            if listener.get("PolicyNames"):
                cert_id = listener["PolicyNames"][0]
        return cert_id

    @property
    def targets(self) -> Sequence["ClassicLoadBalancerTarget"]:
        """
        Targets.

        Returns:
            Operation result.
        """
        return ClassicLoadBalancerTarget.objects.list(self.pk)


class ClassicLoadBalancerTarget(TagsMixin, Model):
    """
    Model classic load balancer target behavior.

    Args:
        data: data.
        instance: instance.
    """
    #: Objects.
    objects = ClassicLoadBalancerTargetManager()

    def __init__(self, data: dict[str, Any], instance: Instance) -> None:
        """
        Initialize ClassicLoadBalancerTarget.

        Args:
            data: data.
            instance: instance.
        """
        super().__init__(data)
        #: Instance.
        self.instance: Instance = instance

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.instance.pk

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.instance.name

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    # ---------------------------------------------
    # ClassicLoadBalancerTarget-specific properties
    # ---------------------------------------------

    @property
    def hostname(self) -> str:
        """
        Hostname.

        Returns:
            Operation result.
        """
        return self.instance.hostname

    @property
    def private_hostname(self) -> str:
        """
        Private hostname.

        Returns:
            Operation result.
        """
        return self.instance.private_hostname

    @property
    def ip_address(self) -> str:
        """
        Ip address.

        Returns:
            Operation result.
        """
        return self.instance.ip_address

    @property
    def bastion(self) -> Instance | None:
        """
        Bastion.

        Returns:
            Operation result.
        """
        return self.instance.bastion

    @property
    def provisioner(self) -> Instance | None:
        """
        Provisioner.

        Returns:
            Operation result.
        """
        return self.instance.provisioner

    @property
    def autoscaling_group(self):
        """
        Autoscaling group.

        Returns:
            Operation result.
        """
        return self.instance.autoscaling_group

    @property
    def ssh_target(self):
        """
        Ssh target.

        Returns:
            Operation result.
        """
        return self.instance

    def render_for_display(self):
        """
        Render for display.

        Returns:
            Operation result.
        """
        data = self.render()
        data["Instance"] = self.instance.render_for_display()
        return data
