import builtins
import contextlib
import json
from collections.abc import Sequence
from typing import Any, Protocol

from jsondiff import diff

from deployfish.types import SupportsCache

from .abstract import Manager, Model

#: Max ssm parameters per call.
MAX_SSM_PARAMETERS_PER_CALL = 10

# ----------------------------------------
# Protocols
# ----------------------------------------


class SupportsSecrets(SupportsCache, Protocol):
    """
    Model supports secrets behavior.
    """

    @property
    def secrets_prefix(self) -> str:
        """
        Secrets prefix.
        """
        ...

    @property
    def secrets(self) -> dict[str, "Secret"]:
        """
        Secrets.
        """
        ...


# ----------------------------------------
# Mixins
# ----------------------------------------


class SecretsMixin:
    """
    Model secrets mixin behavior.
    """

    @property
    def secrets_prefix(self) -> str:
        """
        Secrets prefix.
        """
        raise NotImplementedError

    @property
    def secrets(self: SupportsSecrets) -> dict[str, "Secret"]:
        """
        Secrets.

        Returns:
            Operation result.

        """
        return self.cache["secrets"]

    @secrets.setter
    def secrets(self: SupportsSecrets, value: dict[str, "Secret"]) -> None:
        """
        Secrets.

        Args:
            value: value.

        """
        self.cache["secrets"] = value

    def write_secrets(self: SupportsSecrets) -> None:
        # Add and update secrets we do need
        """
        Write secrets.
        """
        for secret in list(self.secrets.values()):
            with contextlib.suppress(secret.ReadOnly):
                secret.save()
        # now delete any secrets that we no longer need
        if self.secrets:
            aws_pks = Secret.objects.list_names(self.secrets_prefix)
            our_pks = [s.pk for s in list(self.secrets.values())]
            for_deletion = list(set(aws_pks) - set(our_pks))
            if for_deletion:
                Secret.objects.delete_many_by_name(for_deletion)

    def reload_secrets(self: SupportsSecrets) -> None:
        """
        Reload secrets.
        """
        if "secrets" in self.cache:
            del self.cache["secrets"]

    def diff_secrets(
        self: SupportsSecrets,
        other: Sequence["Secret"] | dict[str, "Secret"],
        *,
        ignore_external: bool = False,
    ) -> dict[str, Any]:
        """
        Diff our list of Secrets against `other`.

        `other` is either a list of Secrets and ExternalSecrets, or is a dict where
        the key is the Secret name and the value is the Secret object.

        Args:
            other: other.

        Keyword Args:
            ignore_external: ignore external.

        Returns:
            Operation result.

        """
        us = {}
        them = {}
        if isinstance(other, dict):
            other = list(other.values())
        if ignore_external:
            other = [s for s in other if not isinstance(s, ExternalSecret)]
        if self.secrets:
            our_secrets = sorted(self.secrets.values(), key=lambda x: x.name)
            if ignore_external:
                our_secrets = [
                    s for s in our_secrets if not isinstance(s, ExternalSecret)
                ]
            us = {s.name: s.render_for_diff() for s in our_secrets}
        if other:
            their_secrets = sorted(other, key=lambda x: x.name)
            them = {s.name: s.render_for_diff() for s in their_secrets}
        return json.loads(diff(them, us, syntax="explicit", dump=True))


# ----------------------------------------
# Managers
# ----------------------------------------


class SecretManager(Manager):
    """
    Manage our SSM Parameter Store parameters.   This differs from

    Args:
        model: model.

    """

    #: Service.
    service = "ssm"

    def __init__(
        self,
        model: type["Secret"] | type["ExternalSecret"],
        *,
        readonly: bool = False,
    ) -> None:
        #: Model.
        """
        Initialize SecretManager.

        Args:
            model: model.

        Keyword Args:
            readonly: readonly.

        """
        #: Model.
        self.model = model
        #: Readonly.
        self.readonly = readonly
        super().__init__()

    def _describe_parameters(
        self, key: str, option: str = "prefix"
    ) -> list[dict[str, Any]]:
        """
        Handle describe parameters.

        Args:
            key: key.
            option: option.

        Returns:
            Operation result.

        """
        option = "BeginsWith" if option == "prefix" else "Equals"
        paginator = self.client.get_paginator("describe_parameters")
        response_iterator = paginator.paginate(
            ParameterFilters=[{"Key": "Name", "Option": option, "Values": [key]}]
        )
        parameters = []
        for page in response_iterator:
            parameters.extend(page["Parameters"])
        return parameters

    def _get_parameter_values(
        self, names: list[str], *, decrypt: bool = True
    ) -> tuple[dict[str, Any], list[str]]:
        # get_parameters accepts at most 10 names, so batch requests first.
        """
        Handle get parameter values.

        Args:
            names: names.

        Keyword Args:
            decrypt: decrypt.

        Returns:
            Operation result.

        """
        names_chunks = [
            names[
                i * MAX_SSM_PARAMETERS_PER_CALL : (i + 1) * MAX_SSM_PARAMETERS_PER_CALL
            ]
            for i in range(
                (len(names) + MAX_SSM_PARAMETERS_PER_CALL - 1)
                // MAX_SSM_PARAMETERS_PER_CALL
            )
        ]
        parameters = []
        non_existant = []
        for chunk in names_chunks:
            try:
                response = self.client.get_parameters(
                    Names=chunk, WithDecryption=decrypt
                )
            except self.client.exceptions.InvalidKeyId as e:
                raise self.model.DecryptionFailed(str(e)) from e
            if response.get("InvalidParameters"):
                non_existant.extend(response["InvalidParameters"])
            parameters.extend(response["Parameters"])
        return {p["Name"]: p for p in parameters}, non_existant

    def convert(self, parameter_data: dict[str, Any]) -> "Secret":
        """
        Convert.

        Args:
            parameter_data: parameter data.

        Returns:
            Operation result.

        """
        name = parameter_data["Name"].split(".")[-1]
        return self.model(parameter_data, name=name)

    def get(self, pk: str, **_) -> "Secret":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        values, non_existant_parameters = self._get_parameter_values([pk])
        params = self._describe_parameters(pk, option="equals")
        if non_existant_parameters:
            msg = f"No secret named {pk} exists in AWS"
            raise Secret.DoesNotExist(msg)
        data = params[0]
        data["ARN"] = values[pk]["ARN"]
        data["Value"] = values[pk]["Value"]
        return self.convert(data)

    def get_many(self, pks: list[str], **_) -> Sequence["Secret"]:
        """
        .. note::

            We need both encryption metadata from ``describe_parameters`` and
            values from ``get_parameters``, so this method combines both
            payloads into one returned secret list.

        Args:
            pks: pks.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        # Use get_parameter to get the parameter values
        values, non_existant_parameters = self._get_parameter_values(pks)
        prefixes = set()
        # Current implementation loads by prefix, which may fetch more
        # parameters than requested but preserves existing runtime behavior.
        for pk in pks:
            prefixes.add(pk.rsplit(".", 1)[0] + ".")
        descriptions = {}
        for prefix in prefixes:
            params = self._describe_parameters(prefix)
            for p in params:
                descriptions[p["Name"]] = p
        secrets = []
        for name, data in list(descriptions.items()):
            if name in values:
                data["ARN"] = values[name]["ARN"]
                data["Value"] = values[name]["Value"]
            secrets.append(self.convert(data))
        # Fake the non-existant parameters
        for param in non_existant_parameters:
            data = {"Name": param, "Type": "String", "Tier": "Standard"}
            secrets.append(self.convert(data))
        return secrets

    def list_names(self, prefix: str) -> list[str]:
        """
        List names.

        Args:
            prefix: prefix.

        Returns:
            Operation result.

        """
        if prefix.endswith("*"):
            prefix = prefix[:-1]
            if not prefix.endswith("."):
                prefix = prefix + "."
        parameters = self._describe_parameters(prefix)
        return [p["Name"] for p in parameters]

    def list(self, prefix: str, *, decrypt: bool = True) -> Sequence["Secret"]:
        """
        List.

        Args:
            prefix: prefix.

        Keyword Args:
            decrypt: decrypt.

        Returns:
            Operation result.

        """
        if prefix.endswith("*"):
            prefix = prefix[:-1]
            if not prefix.endswith("."):
                prefix = prefix + "."
        parameters = self._describe_parameters(prefix)
        # We have to do two loops here, because describe_parameters gives us the
        # KeyId for our KMS key, but does not give us Value or ARN, while
        # get_parameters gives us Value and ARN but no KeyId
        names = [parameter["Name"] for parameter in parameters]
        values, _ = self._get_parameter_values(names, decrypt=decrypt)
        secrets = []
        for parameter in parameters:
            parameter["ARN"] = values[parameter["Name"]]["ARN"]
            parameter["Value"] = values[parameter["Name"]]["Value"]
            secrets.append(self.convert(parameter))
        return secrets

    def save(self, obj: Model, **_) -> str:
        """
        Save.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        if not self.readonly:
            response = self.client.put_parameter(**obj.render_for_create())
            return response["Version"]
        msg = "This Secret is read only."
        raise self.model.ReadOnly(msg)

    def delete_many_by_name(self, pks: builtins.list[str]) -> None:
        """
        Delete many by name.

        Args:
            pks: pks.

        """
        if len(pks) <= MAX_SSM_PARAMETERS_PER_CALL:
            self.client.delete_parameters(Names=pks)
        else:
            # delete_parameters() will only take 10 params at a time, so we have
            # to split it up if we have more than 10
            chunks = [
                pks[
                    i * MAX_SSM_PARAMETERS_PER_CALL : (i + 1)
                    * MAX_SSM_PARAMETERS_PER_CALL
                ]
                for i in range(
                    (len(pks) + MAX_SSM_PARAMETERS_PER_CALL - 1)
                    // MAX_SSM_PARAMETERS_PER_CALL
                )
            ]
            for chunk in chunks:
                self.client.delete_parameters(Names=chunk)

    def delete(self, obj: Model, **_) -> None:
        """
        Delete.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        """
        if self.readonly:
            msg = "This Secret is read only."
            raise self.model.ReadOnly(msg)
        try:
            self.client.delete_parameter(Name=obj.pk)
        except self.client.exceptions.ParameterNotFound as e:
            raise Secret.DoesNotExist from e


# ----------------------------------------
# Models
# ----------------------------------------


class Secret(Model):
    """
    An SSM Parameter Store Parameter.

    Args:
        data: data.
        name: name.

    """

    #: Objects.
    objects: SecretManager

    class DecryptionFailed(Exception):
        pass

    def __init__(self, data: dict[str, Any], name: str = ""):
        """
        Initialize Secret.

        Args:
            data: data.
            name: name.

        """
        super().__init__(data)
        #: Secret name.
        self.secret_name = name

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
        return self.data["Name"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.secret_name

    @property
    def arn(self) -> str | None:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data.get("ARN")

    def render_for_create(self) -> dict[str, Any]:
        """
        Render for create.

        Returns:
            Operation result.

        """
        data = self.render()
        if "ARN" in data:
            del data["ARN"]
            del data["LastModifiedDate"]
            del data["LastModifiedUser"]
            del data["Version"]
        data["Overwrite"] = True
        return data

    def render_for_diff(self) -> dict[str, Any]:
        """
        Render for diff.

        Returns:
            Operation result.

        """
        data = self.render()
        data["EnvVar"] = self.secret_name
        if "ARN" in data:
            del data["ARN"]
            del data["LastModifiedDate"]
            del data["LastModifiedUser"]
            del data["Version"]
            del data["Policies"]
        return data

    # ----------------------------
    # Secret-specific properties
    # ----------------------------

    @property
    def prefix(self) -> str:
        """
        Prefix.

        Returns:
            Operation result.

        """
        return self.data["Name"].rsplit(".", 1)[0]

    @prefix.setter
    def prefix(self, value: str) -> None:
        """
        Prefix.

        Args:
            value: value.

        """
        self.data["Name"] = f"{value}.{self.secret_name}"

    @property
    def is_secure(self) -> bool:
        """
        Is secure.

        Returns:
            Operation result.

        """
        return self.kms_key_id is not None

    @property
    def modified_username(self) -> str | None:
        """
        Modified username.

        Returns:
            Operation result.

        """
        user = self.data.get("LastModifiedUser", None)
        if user:
            return user.rsplit("/", 1)[1]
        return None

    @property
    def kms_key_id(self) -> str | None:
        """
        Kms key id.

        Returns:
            Operation result.

        """
        return self.data.get("KeyId")

    @kms_key_id.setter
    def kms_key_id(self, value: str) -> None:
        """
        Kms key id.

        Args:
            value: value.

        """
        self.data["Type"] = "SecureString"
        self.data["KeyId"] = value

    @property
    def value(self) -> str:
        """
        Value.

        Returns:
            Operation result.

        """
        return self.data["Value"]

    @value.setter
    def value(self, value: str) -> None:
        """
        Value.

        Args:
            value: value.

        """
        self.data["Value"] = value

    # ------------------------
    # Secret-specific actions
    # ------------------------

    def copy(self) -> "Secret":
        """
        Copy.

        Returns:
            Operation result.

        """
        data = self.render()
        if "ARN" in data:
            del data["ARN"]
            del data["LastModifiedDate"]
            del data["LastModifiedUser"]
            del data["Version"]
        return self.__class__(data, self.secret_name)

    def __str__(self) -> str:
        """
        Handle str.

        Returns:
            Operation result.

        """
        line = f"{self.secret_name}={self.value}"
        if self.data["Type"] == "SecureString":
            line = f"{line} [SECURE:{self.kms_key_id}]"
        return line


class ExternalSecret(Secret):
    """
    Model external secret behavior.
    """

    #: Objects.
    objects: SecretManager


Secret.objects = SecretManager(Secret)
ExternalSecret.objects = SecretManager(ExternalSecret, readonly=True)
