from unittest.mock import MagicMock

from deployfish.core.models.cloudwatch import CloudwatchAlarm
from deployfish.core.models.efs import EFSFileSystem
from deployfish.core.models.rds import RDSInstance


class TestCloudwatchAlarmModel:
    def test_alarm_name_property(self) -> None:
        alarm = CloudwatchAlarm(
            {
                "AlarmName": "cpu-high",
                "AlarmArn": "arn:aws:cloudwatch:us-west-2:123:alarm:cpu-high",
                "MetricName": "CPUUtilization",
            }
        )
        assert alarm.name == "cpu-high"
        assert alarm.pk == "cpu-high"


class TestEFSFileSystemModel:
    def test_efs_name_and_pk(self) -> None:
        fs = EFSFileSystem(
            {
                "FileSystemId": "fs-abc123",
                "Name": "shared-storage",
                "LifeCycleState": "available",
            }
        )
        assert fs.pk == "fs-abc123"
        assert fs.name == "shared-storage"


class TestRDSInstanceModel:
    def test_rds_endpoint_and_engine(self) -> None:
        db = RDSInstance(
            {
                "DBInstanceIdentifier": "mydb",
                "DBInstanceArn": "arn:aws:rds:1:db:mydb",
                "Engine": "postgres",
                "Endpoint": {"Address": "mydb.example.com", "Port": 5432},
            }
        )
        assert db.name == "mydb"
        assert db.engine == "postgres"
        assert db.hostname == "mydb.example.com"

    def test_rds_manager_get(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_db_instances.return_value = {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "mydb",
                    "DBInstanceArn": "arn:aws:rds:1:db:mydb",
                    "Engine": "postgres",
                    "Endpoint": {"Address": "mydb.example.com", "Port": 5432},
                }
            ],
        }
        db = RDSInstance.objects.get("mydb")
        assert db.pk == "mydb"
