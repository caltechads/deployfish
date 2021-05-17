from ..abstract import Adapter

from deployfish.core.models import Cluster


class EventTargetAdapter(Adapter):

    def get_cluster_arn(self):
        try:
            cluster = Cluster.objects.get(self.data['cluster'])
        except Cluster.DoesNotExist as e:
            raise self.SchemaException('EventTarget: {}'.format(str(e)))
        return cluster.arn

    def get_vpc_configuration(self):
        # FIXME: use VpcConfigurationMixin for this
        data = {}
        source = self.data.get('vpc_configuration', None)
        if source:
            data['Subnets'] = source['subnets']
            if 'security_groups' in source:
                data['SecurityGroups'] = source['security_groups']
            if 'public_ip' in source:
                data['AssignPublicIp'] = 'ENABLED' if source['public_ip'] else 'DISABLED'
        return data

    def convert(self):
        data = {}
        data['Id'] = 'deployfish-' + self.data['name']
        data['Arn'] = self.get_cluster_arn()
        data['RoleArn'] = self.data['schedule_role']
        ecs = {}
        ecs['TaskCount'] = self.data.get('count', 1)
        ecs['LaunchType'] = self.data.get('launch_type', 'EC2')
        if ecs['LaunchType'] == 'FARGATE':
            vpc_configuration = self.get_vpc_configuration()
            if vpc_configuration:
                ecs['NetworkConfiguration'] = {}
                ecs['NetworkConfiguration']['awsvpcConfiguration'] = vpc_configuration
            ecs['PlatformVersion'] = self.data.get('platform_version', 'LATEST')
        if 'grouo' in self.data:
            ecs['Group'] = self.data['group']
        # FIXME: Deal with placementConstraints, placementStrategy and capacityProviderStrategy
        data['EcsParameters'] = ecs
        return data, {}


class EventScheduleRuleAdapter(Adapter):

    def convert(self):
        data = {}
        data['Name'] = 'deployfish-' + self.data['name']
        data['ScheduleExpression'] = self.data['schedule']
        data['State'] = 'ENABLED'
        data['Description'] = 'Scheduler for task: {}'.format(self.data['name'])
        return data, {}
