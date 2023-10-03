import json
import os
import traceback
from typing import Any, NamedTuple, Self

import boto3
import botocore
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
bedrock_runtime_client = boto3.client("bedrock-runtime")


class ClientError(Exception):
    def __init__(self: Self, input_param: str, message: str) -> None:
        self.message = message
        super().__init__(f"{message}: {input_param}")


class ServerError(Exception):
    def __init__(self: Self, input_param: str, message: str) -> None:
        super().__init__(f"{message}: {input_param}")


class EnvParam(NamedTuple):
    MODEL_ID: str

    @classmethod
    def from_env(cls: type["EnvParam"]) -> "EnvParam":
        try:
            return EnvParam(**{k: os.environ[k] for k in EnvParam._fields})
        except Exception as e:
            raise ServerError(
                json.dumps(os.environ),
                "Required environment variables are not set.",
            ) from e


class ApiEvent(NamedTuple):
    prompt: str

    @classmethod
    def from_event(cls: type["ApiEvent"], event: dict[str, Any]) -> "ApiEvent":
        try:
            body = json.loads(event["body"])
            return ApiEvent(
                prompt=body["prompt"],
            )
        except Exception as e:
            raise ClientError(event["body"], "Invalid parameter.") from e

    def to_body(self: Self) -> str:
        return json.dumps({"prompt": self.prompt})


def invoke_model(
    client: Any,  # noqa: ANN401
    modelid: str,
    body: str,
) -> str:
    try:
        res = client.invoke_model(modelId=modelid, body=body)
        return "\n".join(
            [x["data"]["text"] for x in json.loads(res["body"].read())["completions"]],
        )
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "InternalServerError":
            raise ServerError(
                body,
                error.response["Error"]["Message"],
            ) from error
        else:
            raise ClientError(
                body,
                error.response["Error"]["Message"],
            ) from error


class Response(NamedTuple):
    status_code: int
    message: str

    def data(self: Self) -> dict[str, Any]:
        return {
            "statusCode": self.status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, DELETE",
                "Access-Control-Allow-Credentials": True,
                "Access-Control-Allow-Headers": "origin, x-requested-with",
            },
            "body": json.dumps(
                {
                    "message": self.message,
                },
            ),
            "isBase64Encoded": False,
        }


def service(
    body: ApiEvent,
    bedrock_client: Any,  # noqa: ANN401
    env: EnvParam,
) -> Response:
    res = invoke_model(bedrock_client, env.MODEL_ID, body.to_body())
    return Response(
        status_code=200,
        message=res,
    )


@logger.inject_lambda_context(
    correlation_id_path="requestContext.requestId",
)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    try:
        return service(
            body=ApiEvent.from_event(event),
            bedrock_client=bedrock_runtime_client,
            env=EnvParam.from_env(),
        ).data()
    except ServerError:
        logger.error(traceback.format_exc())
        return Response(
            status_code=500,
            message="internal server error. Please access again after some time.",
        ).data()
    except ClientError as ce:
        logger.warning(traceback.format_exc())
        return Response(
            status_code=400,
            message=f"client error. {ce.message}",
        ).data()
    except Exception:
        logger.error(traceback.format_exc())
        return Response(
            status_code=500,
            message="internal server error. Please contact the operator.",
        ).data()
