from botocore.exceptions import ClientError
from deployfish.aws import get_boto3_session


class ASG(object):

    """
    This class exists to manage the number of instances in our ECS service's dedicated
    autoscaling group.  Not useful if this ASG runs a bunch of different services.
    """

    def __init__(self, group_name=None, yml=None):
        if yml is None:
            yml = {}
        self.asg = get_boto3_session().client('autoscaling')
        self.__groupName = group_name
        self.from_yaml(yml)
        self.from_aws()

    def from_yaml(self, yml):
        if 'autoscalinggroup_name' in yml:
            self.__groupName = yml['autoscalinggroup_name']

    def from_aws(self):
        if self.__groupName:
            self.__aws_autoscaling_group = self.__get_autoscaling_group(self.__groupName)
        else:
            self.__aws_autoscaling_group = {}

    def __get_autoscaling_group(self, groupName):
        if groupName:
            try:
                response = self.asg.describe_auto_scaling_groups(
                    AutoScalingGroupNames=[groupName]
                )
            except ClientError:
                return {}
            else:
                return response['AutoScalingGroups'][0]
        else:
            return {}

    @property
    def name(self):
        return self.__groupName

    @property
    def count(self):
        if self.exists():
            return self.__aws_autoscaling_group['DesiredCapacity']
        else:
            return None

    @property
    def min(self):
        if self.exists():
            return self.__aws_autoscaling_group['MinSize']
        else:
            return None

    @property
    def max(self):
        if self.exists():
            return self.__aws_autoscaling_group['MaxSize']
        else:
            return None

    def exists(self):
        if self.__aws_autoscaling_group:
            return True
        return False

    def scale(self, count, force=True):
        if self.exists():
            if count < 0:
                count = 0
            min_size = self.min
            max_size = self.max
            if force:
                if count < self.min:
                    min_size = count
                elif count > self.max:
                    max_size = count
            else:
                if count < self.min:
                    count = self.min
                if count > self.max:
                    count = self.max
            self.asg.update_auto_scaling_group(
                AutoScalingGroupName=self.__groupName,
                DesiredCapacity=count,
                MinSize=min_size,
                MaxSize=max_size
            )
            self.from_aws()
