from dotenv import load_dotenv
import os
import requests
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

zhipu_apikey = os.getenv("ZHIPU_API_KEY")
pony_apikey = os.getenv("PONY_API_KEY")
deepseek_apikey = os.getenv("DEEPSEEK_API_KEY")
tongyi_apikey = os.getenv("TONGYI_API_KEY")


local_model = [
    "qwen3.5-2b",
    "qwen3.5-4b",
    "qwen3.5-9b",
    "qwen3.5-9b-gemini",
    "qwen3.5-27b",
    "qwen3.5-35b",
]
opensource_model = local_model + ["qwen3.5-122b-a10b", "qwen3.5-397b-a17b"]


class ResponseModel(BaseModel):
    thinking: str = Field(
        description=(
            "Summary of your thoughtfully considered thinking process"
            "Note: 1. The 'thinking' field should divided into 2 parts: hint interpretation phase and reasoning phase. In hint interpretation phase, you should interpret basic meaning of all hints one by one. In reasoning phase, you should provide thinking process bases on the interpreted hints. "
            "2. In 'thinking' field, use '1. Hint Interpretation Phase: hint1: xxx, hint2: xxx, ... 2. Reasoning Phase: ...' format.",
        )
    )
    answer_single: str = Field(
        description="The abbreviation of the final answer.If you still have multiple answers and cannot decide, answer all of them."
        # " You can only reply 'I can not determine' when there are more than six possible outcomes with uncertain probabilities."
        # There is only one correct answer. If you still have multiple answers and cannot decide, answer all of them.
    )


def call_zhipu_api(query: str) -> str:
    message = [{"role": "user", "content": query}]

    model = "glm-z1-flash"

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {
        "Authorization": f"Bearer {zhipu_apikey}",
        "Content-Type": "application/json",
    }

    data = {"model": model, "messages": message, "temperature": 1.0}

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API调用失败: {response.status_code}, {response.text}")


def call_deepseek_api(messages, call_model) -> str:
    client = OpenAI(api_key=deepseek_apikey, base_url="https://api.deepseek.com")

    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            temperature=0,
            max_tokens=55000,
            stream=False,
            timeout=300,  # 5分钟超时
            extra_body={"enable_thinking": True},
            # response_format={"type": "json_object"},
        )
    except Exception as e:
        raise Exception(f"API调用失败: {str(e)}")

    return response.choices[0].message


def call_fast_tongyi_api(messages, call_model):
    client = OpenAI(
        api_key=tongyi_apikey,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    try:
        response = client.chat.completions.create(
            model=call_model,
            messages=messages,
            temperature=0,
            max_tokens=20000,
            stream=False,
            timeout=60,
            extra_body={"enable_thinking": False},
        )
        # print(response.choices[0])
        # print(response.usage.total_tokens)
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        raise Exception(f"API调用失败: {str(e)}")
    return response.choices[0].message


def call_tongyi_api(messages, call_model="qwen3.5-plus"):
    client = OpenAI(
        api_key=tongyi_apikey,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    try:
        response = client.chat.completions.create(
            model=call_model,
            messages=messages,
            temperature=0,
            max_tokens=55000,
            stream=False,
            timeout=300,  # 5分钟超时
            extra_body={"enable_thinking": True},
            response_format=(
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "ResponseModel",
                        "schema": ResponseModel.model_json_schema(),
                    },
                }
                if call_model in opensource_model
                else {"type": "json_object"}
            ),
        )
        # print(response.choices[0])
        # print(response.usage.total_tokens)
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        raise Exception(f"API调用失败: {str(e)}")
    return response.choices[0].message


def call_local_api(messages, call_model) -> dict:
    client = OpenAI(base_url="http://localhost:18235/v1", api_key="test")

    try:
        response = client.chat.completions.create(
            model=call_model,
            messages=messages,
            temperature=0,
            max_tokens=55000,
            stream=False,
            timeout=300,  # 5分钟超时
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ResponseModel",
                    "schema": ResponseModel.model_json_schema(),
                },
            },
        )
        # print(response.choices[0])
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        raise Exception(f"API调用失败: {str(e)}")

    return response.choices[0].message


def call_api(messages, call_model) -> str:
    # return call_tongyi_api(messages, call_model).content
    # return call_local_api(messages, call_model).content
    return call_fast_tongyi_api(messages, call_model).content


def call_thinking_api(messages, call_model) -> dict:
    if call_model in opensource_model:
        messages.extend(  # 使用prompt trick引导模型分离思考过程
            [
                {"role": "assistant", "content": "Here is my thinking process:\n"},
                {
                    "role": "user",
                    "content": "\n\nThinking complete. Now, output ONLY the JSON.",
                },
            ]
        )

    if call_model in local_model:
        return call_local_api(messages, call_model)
    elif call_model.startswith("deepseek"):
        return call_deepseek_api(messages, call_model)
    else:
        return call_tongyi_api(messages, call_model)


def main():
    try:
        message = [
            {"role": "user", "content": "请给我介绍你的身份，你有什么能力？"},
        ]
        result = call_api(message, "qwen3.5-9b")
        print(result)
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()
