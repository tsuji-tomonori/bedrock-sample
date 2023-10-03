from typing import Any, Self

from aws_cdk import Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam
from constructs import Construct

from cdk.lambda_construct import LambdaConstruct
from cdk.paramater import build_name


class RootStack(Stack):
    def __init__(
        self: Self,
        scope: Construct,
        construct_id: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.api = apigw.RestApi(
            scope=self,
            id="api",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
            rest_api_name=build_name("api", "bedrock_test"),
            description="bedrock_test",
            deploy_options=apigw.StageOptions(
                data_trace_enabled=True,
                logging_level=apigw.MethodLoggingLevel.ERROR,
                stage_name="v1",
            ),
        )

        text = self.api.root.add_resource("text")

        self.text_api = LambdaConstruct(self, "text_api")
        text.add_method(
            http_method="POST",
            integration=apigw.LambdaIntegration(
                handler=self.text_api.function,
            ),
        )

        bedrock_access_policy = iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            effect=iam.Effect.ALLOW,
            resources=["*"],
        )

        assert self.text_api.function.role is not None
        self.text_api.function.role.add_to_principal_policy(bedrock_access_policy)
