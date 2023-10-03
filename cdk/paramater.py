paramater = {
    "lambda": {
        "text_api": {
            "env": {
                "LOG_LEVEL": "INFO",
                "MODEL_ID": "ai21.j2-mid-v1",
            },
            "memory_size": 128,
        },
    },
}


def build_name(service: str, hostname: str) -> str:
    return f"bedrocktest-{service}-{hostname}"
