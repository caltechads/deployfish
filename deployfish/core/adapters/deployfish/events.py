from .mixins import DeployfishYamlAdapter


class EventTargetAdapter(DeployfishYamlAdapter):

    class ClusterDoesNotExist(Exception):
        pass

    def get_cluster_arn(self):
        kwargs = {}
        if self.data['cluster_name'] != 'default':
            kwargs['clusters'] = [self.data['cluster_name']]
        response = self.ecs.describe_clusters(**kwargs)
        if response['clusters']:
            return response['clusters'][0]['clusterArn']
        else:
            raise self.ClusterDoesNotExist(
                'ECS Cluster "{}" does not exist in AWS'.format(self.data['cluster_name'])
            )

    def get_vpc_configuration(self):
        data = {}
        source = self.data.get('vpc_configuration', None)
        if source:
            data['subnets'] = source['subnets']
            if 'security_groups' in source:
                data['securityGroups'] = source['security_groups']
            if 'public_ip' in source:
                data['assignPublicIp'] = 'ENABLED' if source['public_ip'] else 'DISABLED'
        return data

    def convert(self):
        data = {}
        data['Id'] = self.data['name']
        data['Arn'] = self.get_cluster_arn(self)
        data['RoleArn'] = self.data['schedule_role']
        ecs = {}
        ecs['TaskCount'] = self.data.get('count', 1)
        ecs['LaunchType'] = self.data.get('launch_type', 'EC2')
        if ecs['launchType'] == 'FARGATE':
            vpc_configuration = self.get_vpc_configuration()
            if vpc_configuration:
                ecs['networkConfiguration'] = {}
                ecs['networkConfiguration']['awsVpcConfiguration'] = vpc_configuration
            ecs['PlatformVersion'] = self.task.platform_version
        if self.task.group:
            ecs['Group'] = self.task.group
        data['EcsParameters'] = ecs
        return data


class EventScheduleRuleAdapter(DeployfishYamlAdapter):

    def convert(self):
        data = {}
        data['Name'] = self.data['name']
        data['ScheduleExpression'] = self.data['schedule_expression']
        data['State'] = 'ENABLED',
        data['EventPattern'] = None
        data['Description'] = 'Scheduler for task: {}'.format(self.data['name'])
        data['RoleArn'] = None
        return data, {}
