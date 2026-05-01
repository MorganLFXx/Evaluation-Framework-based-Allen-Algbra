"""!!!Deprecated!!!"""

"""Extract error sample from answered datasets, then repeatedly generate and verify them to filter out the most difficult ones."""

import json
import shutil
import os
from generate.generate_response import multi_thread_generate


def load_datasets(names: list) -> list:
    """
    Input: a list of file names to the answered datasets
    Output: a list of all error samples and skip samples extracted from the datasets
    Skip judge: 'right' not in sample
    Error judge: use sample['right']
    """
    path_template = "datasets/answers/{name}_with_answers.json"
    samples = []
    for name in names:
        path = path_template.format(name=name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Dataset file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sample in data:
            if "right" not in sample or sample["right"] is False:
                samples.append(sample)

    for idx, sample in enumerate(samples):
        sample["id"] = idx
    return samples


def sample_preprocess(samples: list, ques_type="single"):
    """
    Del some attributes belong to answered datasets to restore the original dataset
    """
    to_deleted = []
    if ques_type == "single":
        to_deleted = ["answer_single", "thinking", "right"]
    elif ques_type == "conflict":
        to_deleted = ["answer_single", "right"]
    elif ques_type == "fill":
        pass
    for sample in samples:
        for attr in to_deleted:
            if attr in sample:
                del sample[attr]
    return samples


def batch_responses(samples: list, chat_type, workers: int, model: str):
    multi_thread_generate(samples, "error_extract", chat_type, model, workers)
    shutil.rmtree("datasets/temp/error_extract")


def batch_check(names: list):
    samples = load_datasets(names)
    samples = sample_preprocess(samples)
    with open("datasets/answers/error_samples_batch_with_answers.json", "r") as f:
        results = json.load(f)
    final_samples = []
    for sample in samples:
        sample_id = sample["id"]
        corresponding_results = results[4 * sample_id : 4 * sample_id + 4]
        right_count = sum(
            [1 for res in corresponding_results if res.get("right", False) == True]
        )
        if right_count < 2:
            final_samples.append(sample)
    with open("datasets/error_samples_filtered.json", "w") as f:
        json.dump(final_samples, f, indent=4)
    print(
        f"Filtered {len(final_samples)} difficult samples from {len(samples)} error samples."
    )


def batch_generate(names: list):
    samples = load_datasets(names)
    samples = sample_preprocess(samples)
    new_data = []
    round = 4
    for sample in samples:
        for _ in range(round):
            new_data.append(sample)
    with open("datasets/error_samples_batch.json", "w") as f:
        json.dump(new_data, f, indent=4)
    print(f"Generated {len(new_data)} samples for error extraction.")


def main(names: list, ques_type, workers, model):
    """
    1. Load the answered datasets and extract the error samples
    2. Repeatedly generate and verify the error samples to filter out the most difficult
    3. Output the final error samples to a json file
    """
    round = 4
    threshold = 2
    temp_answer_path = "datasets/explain/temp/"
    os.makedirs(temp_answer_path, exist_ok=True)
    final_samples = []
    samples = load_datasets(names)
    samples = sample_preprocess(samples, ques_type)
    for sample in samples:
        sample["count"] = 0
    for _ in range(round):
        batch_responses(samples, ques_type, workers, model)
        for sample in samples:
            if sample["right"] == False:
                sample["count"] += 1
        samples = [sample for sample in samples if sample["count"] < threshold]
        if len(samples) == 0:
            break
        for idx, sample in enumerate(samples):
            sample["id"] = idx
        with open(os.path.join(temp_answer_path, f"round_{_}.json"), "w") as f:
            json.dump(samples, f, indent=4)

    output_path = "datasets/error_samples.json"
    with open(output_path, "w") as f:
        json.dump(final_samples, f, indent=4)

    shutil.rmtree(temp_answer_path)


def main_batch():
    model = "qwenplus"
    template = "{name}_{model}"
    name_list = ["test_bases", "test_4", "test_15", "test_20", "test_25", "test_50"]
    path_list = [template.format(name=name, model=model) for name in name_list]
    batch_check(path_list)


if __name__ == "__main__":
    main()
