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


def main():
    try:
        allen_helper = """You are an expert in time relation judgment, well-versed in Allen's interval algebra.
        This mathematical framework defines 13 fundamental types of temporal relationships：
        precedes(p), preceded_by(P), meets(m), met_by(M), overlaps(o), overlapped_by(O), finished_by(F), finishes(f), contains(D), during(d), starts(s), started_by(S), equals(e).
        Here are some things to note: 1. 'A overlaps B' means that there is overlap between A and B but A starts before B 2. 'starts' means A and B start at the same time but A ends before B 3. 'finishes' means A and B end at the same time but A starts after B.
        The basic time granularity is day. For example, A(2020.2.1-2022.2.3) and B(2022.2.3-2024.4.5) have the relation 'meets' because A ends when B starts.
        The correspondence between uppercase and lowercase letters of the same letter is inverse. For example, A p B is equivalent to B P A.
        """
        # In the final answers of all responses, you only need to use abbreviations to refer to the corresponding relationships.
        eventA = "Meeting"
        eventB = "Exhibition"
        eventC = "Travel"
        question = f"Please help me determine the allen relationship between {eventA} A and {eventB} B based on following hints.I will provide all hints step by step. Each time, you must guess all possible relationships.If there are more than six possibilities, please indicate that you cannot determine"
        hints = [
            f"1. {eventA} A took place from 2022.9.12 to 2022.12.5.",
            f"2. {eventC} C occurred from 2022.8.20 to 2022.12.5.",
            f"3. {eventC} C was overlapped by {eventB} B.",
            f"4. There is no overlap between {eventA} A and {eventB} B.",
            f"5. After Tom finished {eventA} A, he did not participate in {eventB} B immediately.",
        ]
        # 1
        message = question + "\n"
        for i in range(len(hints)):
            message += hints[i]
            messages = [
                {"role": "system", "content": allen_helper},
                {"role": "user", "content": message},
            ]
            print("== Hint ", i + 1, "==")
            result = call_pony_api(messages)
            print(result)
            sleep(1)
        # for i in range(len(hints)):
        #     if i == 0:
        #         messages = [
        #             {"role": "system", "content": allen_helper},
        #             {"role": "user", "content": message + hints[i]},
        #         ]
        #     else:
        #         messages.append({"role": "user", "content": hints[i]})
        #     print("== Hint ", i+1, "==")
        #     result = call_pony_api(messages)
        #     messages.append({"role": "assistant", "content": result})
        #     print(result)
        #     sleep(1)
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()
