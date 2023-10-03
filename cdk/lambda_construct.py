from pathlib import Path
from typing import Any, Self

import aws_cdk as cdk
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from cdk.paramater import build_name, paramater


class LambdaConstruct(Construct):
    def __init__(
        self: Self,
        scope: Construct,
        construct_id: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = cdk.Stack.of(self).region
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "powertools",
            layer_version_arn=f"arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:40",
        )

        lib_layer = lambda_.LayerVersion(
            self,
            "lib",
            code=lambda_.Code.from_asset(".layers"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
        )

        self.function = lambda_.Function(
            scope=self,
            id="function",
            code=lambda_.Code.from_asset(
                str(Path.cwd() / "src" / "app" / construct_id),
            ),
            handler="lambda_function.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment=paramater["lambda"][construct_id]["env"],  # type: ignore  # noqa: PGH003, E501
            memory_size=paramater["lambda"][construct_id]["memory_size"],  # type: ignore  # noqa: PGH003, E501
            layers=[powertools_layer, lib_layer],
            function_name=build_name("function", construct_id),
        )

        self.function.add_environment(
            "POWERTOOLS_SERVICE_NAME",
            construct_id,
        )

        self.logs = logs.LogGroup(
            scope=self,
            id="logs",
            log_group_name=f"/aws/lambda/{self.function.function_name}",
            retention=logs.RetentionDays.THIRTEEN_MONTHS,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
