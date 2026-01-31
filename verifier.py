import json
import argparse


def main():
    parser = argparse.ArgumentParser(description="Run script with parameters")
    parser.add_argument("--name", type=str, required=True, help="校验的文件名")
    args = parser.parse_args()
    with open(f"datasets/{args.name}_with_answers.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    level1 = 0
    level2 = 0
    level1_true = 0
    level2_true = 0
    i, j = 0, 0
    for item in data:
        check = 1 if item["answer_single"][0].strip() == item["target"]["rel"] else 0
        if item["level"] == 1:
            level1 += 1
            level1_true += check
            if check == 0 and i < 20:
                answer = item["answer_single"][0].strip()
                if answer.startswith("<think>"):
                    answer = "None"
                print(
                    f"level1错误样例: target={item['target']['rel']}, answer={answer}"
                )
                i += 1
        elif item["level"] == 2:
            level2 += 1
            level2_true += check
            if check == 0 and j < 20:
                answer = item["answer_single"][0].strip()
                if answer.startswith("<think>"):
                    answer = "None"
                print(
                    f"level2错误样例: target={item['target']['rel']}, answer={answer}"
                )
                j += 1

    print(f"Level 1 Accuracy: {level1_true}/{level1} = {level1_true/level1:.4f}")
    print(f"Level 2 Accuracy: {level2_true}/{level2} = {level2_true/level2:.4f}")


if __name__ == "__main__":
    main()
