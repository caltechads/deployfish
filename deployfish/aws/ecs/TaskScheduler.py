from deployfish.aws import get_boto3_session


class TaskScheduler(object):
    """
    If the task has a schedule defined, manage an ECS cloudwatch event with the corresponding
    schedule, with the task as an event target.
    """

    def __init__(self, task):
        self.task = task
        self.client = get_boto3_session().client('events')
        self.name = "{}-scheduler".format(self.task.taskName)
        self.target_name = "{}-scheduler-target".format(self.task.taskName)

    def _render(self):
        """
        Generate the dict we will pass to boto3's `put_targets()`.

        :rtype: dict
        """
        r = {'Rule': self.name}
        target = {
            'Id': self.target_name,
            'Arn': self.task.cluster_arn,
            'RoleArn': self.task.schedule_role
        }
        parms = {
            'TaskDefinitionArn': self.task.active_task_definition.arn,
            'TaskCount': self.task.desired_count,
            'LaunchType': self.task.launchType
        }
        if parms['LaunchType'] == 'FARGATE':
            conf = {
                'Subnets': self.task.vpc_configuration['subnets']
            }
            if 'securityGroups' in self.task.vpc_configuration:
                conf['SecurityGroups'] = self.task.vpc_configuration['securityGroups']
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
        """
        Create or update the cloudwatch rule
        """
        self.client.put_rule(
            Name=self.name,
            ScheduleExpression=self.task.schedule_expression,
            State='ENABLED',
            Description='Scheduler for task: {}'.format(self.task.taskName)
        )

    def _add_target(self):
        """
        Add the ECS task configuration as a target to the rule
        """
        kwargs = self._render()
        self.client.put_targets(**kwargs)

    def _clear_targets(self):
        """
        Before we can remove the rule or update the target, we need to remove the old target.
        """
        # the rule might not exist yet. this call will fail if that is the case
        try:
            response = self.client.list_targets_by_rule(
                Rule=self.name,
                Limit=1
            )
            target_ids = []
            for target in response['Targets']:
                target_ids.append(target['Id'])

            self.client.remove_targets(Rule=self.name, Ids=target_ids)
        except:
            pass

    def _delete_rule(self):
        """
        Delete the AWS cloudwatch rule.
        """
        self._clear_targets()
        self.client.delete_rule(Name=self.name)

    def schedule(self):
        """
        Create or update an existing AWS Cloudwatch event rule with the task as the target.
        """
        self._clear_targets()
        self._create_rule()
        self._add_target()

    def unschedule(self):
        """
        Delete the AWS Cloudwatch event rule, with any existing targets.
        """
        self._delete_rule()
