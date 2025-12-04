from time import sleep
from dotenv import load_dotenv
import os
import requests
from openai import OpenAI

load_dotenv()

zhipu_apikey = os.getenv("ZHIPU_API_KEY")
pony_apikey = os.getenv("PONY_API_KEY")


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


def call_pony_api(query: str) -> str:
    client = OpenAI(
        base_url="https://api.tokenpony.cn/v1", api_key=pony_apikey  # 替换为您的API Key
    )
    try:
        response = client.chat.completions.create(
            model="glm-4.6",  # 替换为您要使用的模型名称
            messages=[
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=5000,
            stream=False,
        )
    except Exception as e:
        raise Exception(f"API调用失败: {str(e)}")
    return response.choices[0].message.content


def main():
    try:
        # for i in range(1, 4):
        # n = i
        context = "旅行A 大约在 2019–2021 年，项目B 大致在 2024–2027 年左右。项目C 在 旅行A 结束后约 2 年开始。项目D 和 项目B 大概同时发生"
        # context = f"此外，节日庆典 发生在 2022 年。 此外，员工培训 大致在 2020–2023 年进行。 实验B 是在 节日庆典前{n}年发生的，任务A发生时间和员工培训大概同时。"
        question = "对比 C 和 D，它们的时间顺序大概是什么？"
        options_text = "\n".join(["C 在 D 之前", "C 和 D 有重叠", "C 在 D 之后"])
        # 使用示例
        messages = f"""根据以下信息回答问题。请从给定选项中选择最合适(觉得最可能即可，不是要绝对准确)的答案，直接输出选项内容，不要解释。
        上下文：
        {context}
        问题：
        {question}
        选项：
        {options_text}"""
        # print(f"第{i}次调用API:")
        result = call_pony_api(messages)
        # result = call_zhipu_api(messages)
        print(result)
        sleep(1)
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()

