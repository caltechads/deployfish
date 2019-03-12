from deployfish.aws import get_boto3_session


class TaskScheduler(object):

    # def __init__(self,
    #              schedule_expression,
    #              task_definition,
    #              cluster,
    #              count=1,
    #              network_configuration=None,
    #              version=None,
    #              group=None):
    #     self.schedule_expression = schedule_expression
    #     self.task_definition = task_definition
    #     self.cluster = cluster
    #     self.count = count
    #     self.network_configuration = network_configuration
    #     self.version = version
    #     self.group = group

    def __init__(self, task):
        self.task = task
        self.client = get_boto3_session().client('events')
        self.name = "{}-scheduler".format(self.task.taskName)
        self.target_name = "{}-scheduler-target".format(self.task.taskName)

    def _render(self):
        r = {}
        r['Rule'] = self.name
        target = {}
        target['Id'] = self.target_name
        target['Arn'] = self.task.cluster_arn
        target['RoleArn'] = self.task.schedule_role
        parms = {}
        parms['TaskDefinitionArn'] = self.task.active_task_definition.arn
        parms['TaskCount'] = self.task.desired_count
        parms['LaunchType'] = self.task.launchType
        if parms['LaunchType'] == 'FARGATE':
            conf = {}
            conf['Subnets'] = self.task.vpc_configuration['subnets']
            if 'security_groups' in self.task.vpc_configuration:
                conf['SecurityGroups'] = self.task.vpc_configuration['security_groups']
            if 'assignPublicIp' in self.task.vpc_configuration:
                conf['AssignPublicIp'] = self.task.vpc_configuration['assignPublicIp']
            parms['NetworkConfiguration'] = {
                'awsvpcConfiguration': conf
            }
        parms['PlatformVersion'] = self.task.platform_version
        if self.task.group:
            parms['Group'] = self.task.group
        target['EcsParameters'] = parms
        r['Targets'] = [target]
        return r

    def _create_rule(self):
        response = self.client.put_rule(
            Name=self.name,
            ScheduleExpression=self.task.schedule_expression,
            State='ENABLED',
            Description='Scheduler for task: {}'.format(self.task.taskName)
        )

    def _add_target(self):
        kwargs = self._render()
        self.client.put_targets(**kwargs)

    def _clear_targets(self):
        # the rule might not exist yet. this call will fail if that is the case
        try:
            response = self.client.list_targets_by_rule(
                Rule=self.name,
                Limit=1
            )
            target_ids = []
            for target in response['Targets']:
                target_ids.append(target['Id'])

            response = self.client.remove_targets(
                Rule=self.name,
                Ids=target_ids
            )
        except:
            pass

    def _delete_rule(self):
        self._clear_targets()
        self.client.delete_rule(Name=self.name)

    def schedule(self):
        self._clear_targets()
        self._create_rule()
        self._add_target()

    def unschedule(self):
        self._delete_rule()

