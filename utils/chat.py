from time import sleep
from dotenv import load_dotenv
import os
import requests
from openai import OpenAI

load_dotenv()

zhipu_apikey = os.getenv("ZHIPU_API_KEY")
pony_apikey = os.getenv("PONY_API_KEY")
deepseek_apikey = os.getenv("DEEPSEEK_API_KEY")
tongyi_apikey = os.getenv("TONGYI_API_KEY")


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
            max_tokens=40000,
            timeout=300,  # 5分钟超时
            stream=False,
        )
    except Exception as e:
        raise Exception(f"API调用失败: {str(e)}")

    return response.choices[0].message.content


def call_pony_api(messages, call_model) -> str:
    client = OpenAI(
        base_url="https://api.tokenpony.cn/v1", api_key=pony_apikey  # 替换为您的API Key
    )
    try:
        response = client.chat.completions.create(
            # model="glm-4.6",
            # model="qwen3-next-80b-a3b-instruct",
            # model="deepseek-v3.2",
            # model="qwen3-32b",
            # model="qwen3-8b",
            model=call_model,
            messages=messages,
            temperature=0,
            max_tokens=20000,
            stream=False,
            timeout=300,  # 5分钟超时
            extra_body={"chat_template_kwargs": {"thinking": True}},
        )
    except Exception as e:
        raise Exception(f"API调用失败: {str(e)}")
    return response.choices[0].message.content


def call_tongyi_api(messages, call_model="qwen3.5-plus-2026-02-15") -> str:
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
            timeout=300,  # 5分钟超时
            extra_body={"enable_thinking": True},
        )
    except Exception as e:
        print(f"API调用失败: {str(e)}")
        raise Exception(f"API调用失败: {str(e)}")
    return response.choices[0].message.content


def call_api(messages, call_model) -> str:
    return call_tongyi_api(messages, call_model)


def main():
    try:

        message = [
            {"role": "user", "content": "请给我介绍你的身份，你有什么能力？"},
        ]
        result = call_api(message, "qwen3.5-plus")
        print(result)
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()
