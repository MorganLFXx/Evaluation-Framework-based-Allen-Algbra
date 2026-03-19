import json
from generate.generate_response import detail_post_question, allen_helper


def item2question(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    hints = sample["hints"]
    question = (
        "Please help me determine the allen relationship between "
        f"'{sample['events'][l]}' and '{sample['events'][r]}' based on following information steps by steps."
    )
    question += detail_post_question + "\n"
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    return messages


def json_to_jsonl():
    """
    将 JSON 文件转换为 JSONL 文件
    :param json_file_path: 输入的 JSON 文件路径
    :param jsonl_file_path: 输出的 JSONL 文件路径
    """
    json_file_path = "datasets/debug_bases_1.json"
    jsonl_file_path = f"{json_file_path}l"
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_file_path}")
        return

    try:
        with open(jsonl_file_path, "w", encoding="utf-8") as f:
            i = 0
            for item in json_data:
                messages = item2question(item)
                transformed_item = {
                    "custom_id": i,
                    "method": "POST",
                    "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "body": {"model": "qwen3.5-plus", "messages": messages},
                }
                f.write(json.dumps(transformed_item, ensure_ascii=False) + "\n")
                i += 1
        print(f"转换成功！JSONL 文件已保存至：{jsonl_file_path}")
    except Exception as e:
        print(f"写入文件失败：{e}")


def main():
    json_to_jsonl()


if __name__ == "__main__":
    main()
