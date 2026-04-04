import json


def single_check(sample):
    if sample["answer_single"][0].strip().startswith("<think>"):
        return False
    return sample["answer_single"][0].strip() == sample["target"]["rel"]


def conflict_check(sample):
    # judge answer_single is a int
    # if not sample["answer_single"][0].strip().isdigit():
    #     print("not digit")
    #     return False
    # answer = int(sample["answer_single"][0].strip())
    answer = sample["answer_single"][0]
    return answer == sample["target"]["conflict_no"]


def fill_check(sample):
    candidates = list(sample["target"]["blank_candidate"])
    answer = sample["answer_single"][0].strip()
    for c in candidates:
        if answer in c:
            return True
    return False


def sample_check(sample):
    if "conflict_no" in sample["target"]:
        return conflict_check(sample)
    elif "blank_object" in sample["target"]:
        return fill_check(sample)
    else:
        return single_check(sample)


def task_type(sample):
    if "conflict_no" in sample["target"]:
        return "conflict"
    if "blank_object" in sample["target"]:
        return "fill"
    return "single"


model_problem = (
    "I can not determine.(The model may be overthinking or the output is truncated.)"
)


def answer_verify(name):
    if not name:
        raise ValueError("name is required")
    with open(f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    has_checked = "right" in data[0]

    right = 0
    skip = 0
    for item in data:
        if (
            "answer_single" not in item
            or len(item["answer_single"]) == 0
            or item["answer_single"][0] == model_problem
        ):
            skip += 1
            continue
        item["right"] = sample_check(item)
        check = 1 if item["right"] else 0
        right += check
    if not has_checked:
        json.dump(
            data,
            open(f"datasets/answers/{name}_with_answers.json", "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=4,
        )
    # print(f"Get response error: {skip}")
    print(
        f"Skip: {skip}, Accuracy: {right}/{len(data)-skip} = {right/(len(data)-skip):.4f}"
    )
    return right


def _ensure_has_right(samples, name):
    if not samples:
        raise ValueError(f"No samples loaded for {name}")
    has_right = any("right" in s for s in samples)
    if not has_right:
        raise ValueError(
            f"Samples for {name} do not contain 'right'. Run answer_verify first."
        )


def analyze_samples(samples, name, expect_type=None):
    _ensure_has_right(samples, name)
    task_stats = {}
    path_len_stats = {}
    total = 0
    right = 0
    for item in samples:
        if "right" not in item:
            continue
        ttype = task_type(item)
        if expect_type and ttype != expect_type:
            continue
        total += 1
        check = 1 if item["right"] else 0
        right += check
        task_stats.setdefault(ttype, {"total": 0, "right": 0})
        task_stats[ttype]["total"] += 1
        task_stats[ttype]["right"] += check
        path_len = len(item.get("paths", []))
        path_len_stats.setdefault(ttype, {})
        path_len_stats[ttype].setdefault(path_len, {"total": 0, "right": 0})
        path_len_stats[ttype][path_len]["total"] += 1
        path_len_stats[ttype][path_len]["right"] += check

    if total == 0:
        print(f"No samples to analyze for {name}")
        return

    print(f"{name}: {right}/{total} = {right/total:.4f}")
    print("Task stats:")
    for key in sorted(task_stats.keys()):
        t_total = task_stats[key]["total"]
        t_right = task_stats[key]["right"]
        acc = t_right / t_total if t_total else 0.0
        print(f"  {key}: {t_right}/{t_total} = {acc:.4f}")
    print("Path length stats (by task):")
    for ttype in sorted(path_len_stats.keys()):
        print(f"  {ttype}:")
        for key in sorted(path_len_stats[ttype].keys()):
            p_total = path_len_stats[ttype][key]["total"]
            p_right = path_len_stats[ttype][key]["right"]
            acc = p_right / p_total if p_total else 0.0
            print(f"    len={key}: {p_right}/{p_total} = {acc:.4f}")


def final_single_analyze(model, samples=None):
    if samples is None:
        # open path and load samples
        path = f"datasets/answers/final_single_{model}_with_answers.json"
        with open(path, "r", encoding="utf-8") as f:
            samples = json.load(f)
    analyze_samples(samples, f"final_single_{model}", expect_type="single")


def final_conflict_analyze(model, samples=None):
    if samples is None:
        # open path and load samples
        path = f"datasets/answers/final_conflict_{model}_with_answers.json"
        with open(path, "r", encoding="utf-8") as f:
            samples = json.load(f)
    analyze_samples(samples, f"final_conflict_{model}", expect_type="conflict")


def final_fill_analyze(model, samples=None):
    if samples is None:
        # open path and load samples
        path = f"datasets/answers/final_fillblank_{model}_with_answers.json"
        with open(path, "r", encoding="utf-8") as f:
            samples = json.load(f)
    analyze_samples(samples, f"final_fillblank_{model}", expect_type="fill")


def final_all_analyze(model):
    # final_all包含single,conflict,fill三类的分析，是一个总的集成
    path = f"datasets/answers/final_all_{model}_with_answers.json"
    with open(path, "r", encoding="utf-8") as f:
        samples = json.load(f)
    analyze_samples(samples, f"final_all_{model}")


def final_task_analyze(name, model=None):
    # 统一入口, 按照name分流
    # name -> final_all, final_single, final_conflict, final_fill
    if not name:
        raise ValueError("name is required")
    if not model:
        raise ValueError("model is required")
    if name == "final_all":
        return final_all_analyze(model)
    if name == "final_single":
        return final_single_analyze(model)
    if name == "final_conflict":
        return final_conflict_analyze(model)
    if name == "final_fill":
        return final_fill_analyze(model)
    raise ValueError(f"Unsupported name: {name}")


def main(mode="answer_verify", name=None, names=None, show=5):
    if mode == "answer_verify":
        answer_verify(name)
    elif mode == "final":
        final_task_analyze(name)
    else:
        raise ValueError(f"Unsupported mode: {mode}")


if __name__ == "__main__":
    # main(mode="answer_verify", name="sample")
    candidates = [
        "'O2' overlaps 'I3' or Start('O2') < Start('I3') < End('O2') < End('I3').",
        "'O2' is finished by 'I3' or Start('O2') < Start('I3') < End('O2') = End('I3').",
        "'O2' contains 'I3' or Start('O2') < Start('I3') < End('I3') < End('O2').",
        "'O2' starts 'I3' or Start('O2') = Start('I3') < End('O2') < End('I3').",
        "'O2' equals 'I3' or Start('O2') = Start('I3') < End('O2') = End('I3').",
        "'O2' is started by 'I3' or Start('O2') = Start(''I3') < End('I3') < End('O2').",
        "'O2' during 'I3' or Start('I3') < Start(''O2') < End('O2') < End('I3').",
        "'O2' finishes 'I3' or Start('I3') < Start('O2') < End('O2') = End('I3').",
        "'I3' overlaps 'O2' or Start('I3') < Start('O2') < End('I3') < End('O2').",
    ]
    for c in candidates:
        pass
