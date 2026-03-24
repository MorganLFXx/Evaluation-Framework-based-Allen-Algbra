"""
entry for the whole project
the parse_args should be parsed here
"""

import argparse
import os

from generate import generate_data
from generate import generate_response
from generate import generate_sp_task
from explain import qa_checker
from explain import error_checker


def main():
    parser = argparse.ArgumentParser(description="Project entry point")
    subparsers = parser.add_subparsers(dest="command")

    data_parser = subparsers.add_parser("data", help="Generate data samples")
    data_parser.add_argument("--n", type=int, default=1, help="生成样例数量")
    data_parser.add_argument("--name", type=str, required=True, help="生成的文件名")
    data_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="样例递归深度，每基于target生成一次formula算一层",
    )
    data_parser.add_argument(
        "--type",
        type=str,
        choices=["single", "conflict", "fill"],
        help="生成的任务类型",
        default="single",
    )

    response_parser = subparsers.add_parser("response", help="Generate responses")
    response_parser.add_argument(
        "--name", type=str, required=True, help="需要生成答案的文件名"
    )
    response_parser.add_argument(
        "--chat_type",
        type=str,
        choices=["single", "conflict", "fill"],
        help="问题类型",
    )
    response_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并行调用线程数",
    )
    response_parser.add_argument(
        "--merge_only",
        action="store_true",
        help="只从temp恢复并整合输出，不再调用API",
    )
    response_parser.add_argument(
        "--model",
        type=str,
        help="调用的模型名称",
    )

    qa_parser = subparsers.add_parser("qa", help="QA checker utilities")
    qa_parser.add_argument(
        "--mode",
        type=str,
        choices=["answer_verify", "overlap_check", "model_error_overlap_check"],
        default="answer_verify",
        help="运行模式",
    )
    qa_parser.add_argument("--name", type=str, help="校验的文件名")

    error_parser = subparsers.add_parser("error", help="Error checker utilities")
    error_parser.add_argument(
        "--path",
        required=True,
        help="Input dataset files or dataset names",
    )
    error_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并行校验线程数",
    )
    error_parser.add_argument(
        "--model",
        type=str,
        default="qwen3.5-plus",
        help="Model name for call_api",
    )

    pipeline_parser = subparsers.add_parser("pipeline", help="Run the full pipeline")
    pipeline_parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Dataset name for the full pipeline",
    )
    pipeline_parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of samples to generate for the full pipeline",
    )
    pipeline_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Recursion depth for data generation in the full pipeline",
    )
    pipeline_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for response generation",
    )
    pipeline_parser.add_argument(
        "--chat_type",
        type=str,
        choices=["single", "conflict", "fill"],
        help="问题类型",
        default="single",
    )
    pipeline_parser.add_argument(
        "--model",
        type=str,
        default="deepseek-v3.2",
        help="Model name for response generation in the full pipeline",
    )
    pipeline_parser.add_argument(
        "--check-model",
        type=str,
        default="qwen3.5-plus",
        help="Model name for answer verification in the full pipeline",
    )
    pipeline_parser.add_argument(
        "--skip-error-check",
        action="store_true",
        help="Whether to skip error checking in the full pipeline",
    )

    args = parser.parse_args()
    if args.command == "data":
        generate_data.main(
            n=args.n,
            name=args.name,
            depth=args.depth,
            hint="indirect pos",
        )
        if args.type == "conflict":
            generate_sp_task.generate_conflict_task(args.name)
        if args.type == "fill":
            generate_sp_task.generate_fillblank_task(args.name)
    elif args.command == "response":
        generate_response.main(
            name=args.name,
            chat_type=args.chat_type,
            model=args.model,
            workers=args.workers,
            merge_only=args.merge_only,
            hint="hint",
        )
    elif args.command == "qa":
        if args.mode == "answer_verify":
            qa_checker.answer_verify(args.name)
        else:
            raise ValueError(f"Unsupported mode: {args.mode}")
    elif args.command == "error":
        error_checker.main(
            path=args.path,
            workers=args.workers,
            model=args.model,
        )
    elif args.command == "pipeline":
        # 1. 数据生成(如果已有则跳过)
        if not os.path.exists(f"datasets/{args.name}.json"):
            generate_data.main(
                n=args.n,
                name=args.name,
                depth=args.depth,
                hint="indirect pos",
            )
        # 2. 回答生成
        generate_response.main(
            name=args.name,
            chat_type=args.chat_type,
            model=args.model,
            workers=args.workers,
            merge_only=False,
            hint="hint",
        )
        # 3. 答案校验
        right = qa_checker.answer_verify(args.name)
        print(f"Answer verification completed. Correct answers: {right}")
        # 4. 错误校验(暂时跳过)
        if not args.skip_error_check:
            error_checker.main(
                path=args.name,
                workers=(
                    right // 8
                ),  # 根据正确率动态调整错误校验的线程数，避免过多线程导致API调用过快
                model=args.check_model,
            )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
