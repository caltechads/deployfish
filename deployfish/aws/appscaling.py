# -*- coding: utf-8 -*-

from botocore.exceptions import ClientError
from deployfish.aws import get_boto3_session
from deployfish.aws.cloudwatch import ECSServiceCPUAlarm


class ScalingPolicy(object):
    """
    A class which allows us to manage Application AutoScaling ScalingPolicies.
    """

    def __init__(self, serviceName, clusterName, yml=None, aws=None):
        """
        ``yml`` is dict parsed from one of the scaling policy subsection of the
        ``application-scaling`` section from ``deployfish.yml``.  Example:

            {
                'cpu': '>=60',
                'check_every_seconds': 60,
                'periods': 5,
                'cooldown': 60,
                'scale_by': 1
            }

        ``aws`` is an entry from the ``ScalingPolicies`` list in the response from
        ``boto3.client('application-autoscaling').describe_scaling_policies()`

        :param serviceName: the name of an ECS service in cluster ``clusterName``
        :type serviceName: string

        :param clusterName: the name of an ECS cluster
        :type clusterName: string

        :param yml: scaling policy from ``deployfish.yml`` as described above
        :type yml: dict

        :param aws: scaling policy AWS dict as described above
        :type aws: dict
        """
        if not yml:
            yml = {}
        if not aws:
            aws = {}
        self.scaling = get_boto3_session().client('application-autoscaling')
        self.serviceName = serviceName
        self.clusterName = clusterName
        self.alarm = None
        self.__defaults()
        self.from_yaml(yml)
        self.from_aws(aws)
        self.alarm = None
        if yml:
            self.alarm = ECSServiceCPUAlarm(
                self.serviceName,
                self.clusterName,
                scaling_policy_arn=self.arn,
                yml=yml
            )

    def __defaults(self):
        self._name = None
        self._cooldown = 0
        self._scale_by = 0
        self._MetricIntervalLowerBound = None
        self._MetricIntervalUpperBound = None
        self._cpu = ''

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in ['MetricIntervalLowerBound', 'MetricIntervalUpperBound']:
                if not getattr(self, "_" + attr):
                    if self.cpu:
                        if (('>' in self.cpu and attr == 'MetricIntervalLowerBound') or
                                ('<' in self.cpu and attr == 'MetricIntervalUpperBound')):
                            setattr(self, "_" + attr, 0)
                    elif self.__aws_scaling_policy:
                        adj = self.__aws_scaling_policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]
                        if attr in adj:
                            setattr(self, "_" + attr, adj[attr])
                return getattr(self, "_" + attr)
            else:
                raise AttributeError

    @property
    def cpu(self):
        """
        We're keeping track of cpu here in the scaling policy so we can set the
        StepAdjustment ``MetricIntervalLowerBound`` and
        ``MetricIntervalUpperBound`` parameters appropriately.
        """
        if not self._cpu:
            if self.alarm:
                self._cpu = self.alarm.cpu
        return self._cpu

    @cpu.setter
    def cpu(self, value):
        self._cpu = value

    @property
    def arn(self):
        """
        The ARN for the policy.  We'll only have this if the policy exists in AWS.
        """
        if self.exists():
            return self.__aws_scaling_policy['PolicyARN']
        return None

    @property
    def name(self):
        """
        The name the scaling policy should have in AWS.
        """
        if self.exists():
            self.name = self.__aws_scaling_policy['PolicyName']
        else:
            if self._scale_by < 0:
                direction = 'scale-down'
            else:
                direction = 'scale-up'
            self.name = '{}-{}-{}'.format(self.clusterName, self.serviceName, direction)
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def scale_by(self):
        """
        The number of tasks to scale by when this policy is activated.  If
        positive, scale up; if negative, scale down.
        """
        # we always want to prefer what was set via yaml here.  yaml loads
        # come before aws loads, so _scale_by should be set already by the
        # time we get here
        if not self._scale_by and self.exists():
            adjustment = self.__aws_scaling_policy['StepScalingPolicyConfiguration']['StepAdjustments'][0]
            self._scale_by = adjustment['ScalingAdjustment']
        return self._scale_by

    @scale_by.setter
    def scale_by(self, scale_by):
        self._scale_by = scale_by

    @property
    def cooldown(self):
        """
        The amount of time, in seconds, after a scaling activity completes where
        previous trigger-related scaling activities can influence future scaling
        events.  Look at the documentation for PutScalingPolicy.  The actual cooldown
        meaning is more complicated than this.
        """
        if not self._cooldown and self.exists():
            self._cooldown = self.__aws_scaling_policy['StepScalingPolicyConfiguration']['Cooldown']
        return self._cooldown

    @cooldown.setter
    def cooldown(self, cooldown):
        self._cooldown = cooldown

    def from_aws(self, aws=None):
        self.__aws_scaling_policy = {}
        if aws:
            self.__aws_scaling_policy = aws
        else:
            response = self.scaling.describe_scaling_policies(
                PolicyNames=[self.name],
                ServiceNamespace='ecs',
                ResourceId='service/{}/{}'.format(self.clusterName, self.serviceName),
                ScalableDimension='ecs:service:DesiredCount'
            )
            if response['ScalingPolicies']:
                self.__aws_scaling_policy = response['ScalingPolicies'][0]

    def from_yaml(self, yml):
        """
        Load our configuration from the config read from ``deployfish.yml``.

        :param yml: a scaling policy level entry from the ``deployfish.yml`` file
        :type yml: dict
        """
        if yml:
            self.cooldown = yml['cooldown']
            self.scale_by = yml['scale_by']
            self.cpu = yml['cpu']

    def exists(self):
        """
        Return ``True`` if application autoscaling has been set up for the
        service named ``self.serviceName`` in a cluster named
        ``self.clusterName`` exists, and data related to that is loaded into
        this object.

        :rtype: boolean
        """
        if self.__aws_scaling_policy:
            return True
        return False

    def _render_create(self):
        """
        Return the argument list that we'll pass to ``put_scaling_policy()``.

        :rtype: dict
        """
        r = {
            'PolicyName': self.name,
            'ServiceNamespace': 'ecs',
            'ResourceId': 'service/{}/{}'.format(self.clusterName, self.serviceName),
            'ScalableDimension': 'ecs:service:DesiredCount',
            'PolicyType': 'StepScaling',
            'StepScalingPolicyConfiguration': {
                'AdjustmentType': 'ChangeInCapacity',
                'StepAdjustments': []
            }
        }
        adjustment = {'ScalingAdjustment': self.scale_by}
        if self.MetricIntervalLowerBound is not None:
            adjustment['MetricIntervalLowerBound'] = self.MetricIntervalLowerBound
        if self.MetricIntervalUpperBound is not None:
            adjustment['MetricIntervalUpperBound'] = self.MetricIntervalUpperBound
        r['StepScalingPolicyConfiguration']['StepAdjustments'].append(adjustment)
        r['StepScalingPolicyConfiguration']['Cooldown'] = self.cooldown
        r['StepScalingPolicyConfiguration']['MetricAggregationType'] = 'Average'
        return r

    def _render_delete(self):
        """
        Return the argument list that we'll pass to ``delete_scaling_policy()``.

        :rtype: dict
        """
        return {
            'PolicyName': self.name,
            'ServiceNamespace': 'ecs',
            'ResourceId': 'service/{}/{}'.format(self.clusterName, self.serviceName),
            'ScalableDimension': 'ecs:service:DesiredCount'
        }

    def __eq__(self, other):
        if (self.MetricIntervalLowerBound == other.MetricIntervalLowerBound and
            self.MetricIntervalUpperBound == other.MetricIntervalUpperBound and
            self.cooldown == other.cooldown and
            self.scale_by == other.scale_by and
            self.clusterName == other.clusterName and
            self.serviceName == other.serviceName
        ):
            return True
        return False

    def __ne__(self, other):
        return not self == other

    def create(self):
        """
        Create the scaling policy and its associated CloudWatch alarm.
        """
        self.scaling.put_scaling_policy(**self._render_create())
        self.from_aws()
        self.alarm.scaling_policy_arn = self.arn
        self.alarm.create()

    def delete(self):
        """
        Delete the scaling policy and its associated CloudWatch alarm.
        """
        if self.exists():
            try:
                self.scaling.delete_scaling_policy(**self._render_delete())
            except ClientError:
                pass
            self.alarm.delete()
        self.__aws_scaling_policy = {}

    def needs_update(self):
        """
        If our desired scaling policy or associated CloudWatch alarm is
        different than what actually exists in AWS, return ``True``, else return
        ``False``.

        :rtype: boolean
        """
        if self == ScalingPolicy(self.serviceName, self.clusterName, aws=self.__aws_scaling_policy):
            if self.alarm.needs_update():
                return True
            return False
        return True

    def update(self):
        """
        If our desired scaling policy or associated CloudWatch alarm is
        different than what actually exists in AWS, delete them and recreate
        them with the config we want.
        """
        if self != ScalingPolicy(self.serviceName, self.clusterName, aws=self.__aws_scaling_policy):
            # The scaling policy itself needs updating
            self.delete()
            self.create()
        else:
            # The scaling policy doesn't need updating, but maybe the alarm does
            self.alarm.update()


class ApplicationAutoscaling(object):
    """
    This manages the ECS Application AutoScaling hierarchy of objects in AWS.

    This hierarchy looks like this:

        ApplicationAutoScaling()                     [AWS object: scalable target]
            ├── ScalingPolicy('scale-up')            [AWS object: scaling policy]
            │   └── ECSServiceCPUAlarm('scale-up')   [AWS object: CloudWatch alarm]
            └── ScalingPolicy('scale-down')          [AWS object: scaling policy]
                └── ECSServiceCPUAlarm('scale-down') [AWS object: CloudWatch alarm]
    """

    def __init__(self, serviceName, clusterName, yml=None, aws=None):
        """
        ``yml`` is dict parsed from the ``application-scaling`` section from
        ``deployfish.yml``.  Example:

            {
                'min_capacity': 2,
                'max_capacity': 4,
                'role_arn': 'arn:aws:iam::123445678901:role/ecsServiceRole',
                'scale-up': {
                    'cpu': '>=60',
                    'check_every_seconds': 60,
                    'periods': 5,
                    'cooldown': 60,
                    'scale_by': 1
                },
                'scale-down': {
                    'cpu': '<=30',
                    'check_every_seconds': 60,
                    'periods': 30,
                    'cooldown': 60,
                    'scale_by': -1
                }
            }

        ``aws`` is an entry from the ``ScalableTargets`` list in the response from
        ``boto3.client('application-autoscaling').describe_scalable_targets()`

        :param serviceName: the name of an ECS service in cluster ``clusterName``
        :type serviceName: string

        :param clusterName: the name of an ECS cluster
        :type clusterName: string

        :param yml: scaling config from ``deployfish.yml`` as described above
        :type yml: dict

        :param aws: scalable target AWS dict as described above
        :type aws: dict
        """
        if aws is None:
            aws = {}
        if yml is None:
            yml = {}
        self.scaling = get_boto3_session().client('application-autoscaling')
        self.serviceName = serviceName
        self.clusterName = clusterName
        self.__yml = {}
        self.policies = {}
        self.__defaults()
        self.from_yaml(yml)
        self.from_aws(aws)

    def __defaults(self):
        self._MinCapacity = 0
        self._MaxCapacity = 0
        self._RoleARN = None

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in ['MinCapacity', 'MaxCapacity', 'RoleARN']:
                if not getattr(self, "_" + attr) and self.__aws_scalable_target and attr in self.__aws_scalable_target:
                    setattr(self, "_" + attr, self.__aws_scalable_target[attr])
                return getattr(self, "_" + attr)
            else:
                raise AttributeError

    def __setattr__(self, attr, value):
        if attr in ['MinCapacity', 'MaxCapacity', 'RoleARN']:
            setattr(self, "_" + attr, value)
        else:
            super(ApplicationAutoscaling, self).__setattr__(attr, value)

    @property
    def resource_id(self):
        return "service/{}/{}".format(self.clusterName, self.serviceName)

    def from_aws(self, aws=None):
        self.__aws_scalable_target = {}
        if aws:
            self.__aws_scalable_target = aws
        else:
            response = self.scaling.describe_scalable_targets(
                ServiceNamespace='ecs',
                ResourceIds=['service/{}/{}'.format(self.clusterName, self.serviceName)],
                ScalableDimension='ecs:service:DesiredCount'
            )
            if response['ScalableTargets']:
                self.__aws_scalable_target = response['ScalableTargets'][0]

    def from_yaml(self, yml):
        """
        Load our configuration from the config read from ``deployfish.yml``.

        :param yml: a application-scaling level entry from the ``deployfish.yml`` file
        :type yml: dict
        """
        if yml:
            self.__yml = yml
            self.MinCapacity = yml['min_capacity']
            self.MaxCapacity = yml['max_capacity']
            self._RoleARN = yml['role_arn']
            self.policies['scale-up'] = ScalingPolicy(self.serviceName, self.clusterName, yml['scale-up'])
            self.policies['scale-down'] = ScalingPolicy(self.serviceName, self.clusterName, yml['scale-down'])

    def exists(self):
        """
        Return ``True`` if application autoscaling has been set up for the
        service named ``self.serviceName`` in a cluster named
        ``self.clusterName`` exists, and data related to that is loaded into
        this object.

        :rtype: boolean
        """
        if self.__aws_scalable_target:
            return True
        return False

    def should_exist(self):
        """
        Return ``True`` if we were defined in the ``deployfish.yml`` file and
        thus should exist or be made to exist in AWS, ``False`` otherwise.

        :rtype: boolean
        """
        return bool(self.__yml)   # essentially, is self.__yml the empty dict?

    def _render_create(self):
        """
        Return a dict to pass as ``**kwargs`` to ``ecs.register_scalable_target()``.

        This method exists so we can write unittests for the args without having
        to mock the ``register_scalable_target`` method.
        """
        return {
            'ServiceNamespace': 'ecs',
            'ResourceId': self.resource_id,
            'ScalableDimension': 'ecs:service:DesiredCount',
            'MinCapacity': self.MinCapacity,
            'MaxCapacity': self.MaxCapacity,
            'RoleARN': self.RoleARN
        }

    def _render_delete(self):
        """
        Return a dict to pass as ``**kwargs`` to ``ecs.deregister_scalable_target()``.

        This method exists so we can write unittests for the args without having
        to mock the ``deregister_scalable_target`` method.
        """
        return {
            'ServiceNamespace': 'ecs',
            'ResourceId': self.resource_id,
            'ScalableDimension': 'ecs:service:DesiredCount'
        }

    def __eq__(self, other):
        if (self.resource_id == other.resource_id and
            self.MinCapacity == other.MinCapacity and
            self.MaxCapacity == other.MaxCapacity and
            self.RoleARN == other.RoleARN):  # NOQA
            return True
        return False

    def __ne__(self, other):
        return not self == other

    def create(self):
        if not self.exists():
            self.scaling.register_scalable_target(**self._render_create())
            for policy in self.policies.keys():
                self.policies[policy].create()

    def delete(self):
        if self.exists():
            for policy in self.policies.keys():
                self.policies[policy].delete()
            self.scaling.deregister_scalable_target(**self._render_delete())
            self.__aws_scalable_target = {}

    def needs_update(self):
        if self == ApplicationAutoscaling(self.serviceName, self.clusterName, aws=self.__aws_scalable_target):
            for policy in self.policies.keys():
                if self.policies[policy].needs_update():
                    return True
            return False
        return True

    def update(self):
        if self != ApplicationAutoscaling(self.serviceName, self.clusterName, aws=self.__aws_scalable_target):
            # the scalable target itself needs updating
            self.delete()
            self.create()
        else:
            # the scalable target itself doesn't need updating but maybe
            # the scaling policies do
            for policy in self.policies.keys():
                self.policies[policy].update()
