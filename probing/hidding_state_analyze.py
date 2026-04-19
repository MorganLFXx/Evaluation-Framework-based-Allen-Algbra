import argparse

from probing.pipeline import ProbePipelineConfig, run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Key-relation binary probing pipeline with control/treatment A/B statistics"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="test_10_final",
        help="Path to conflict task dataset JSON",
    )
    model_path = "/data/zhk/models/qwen-3.5-9b"
    # parser.add_argument(
    #     "--model-path",
    #     type=str,
    #     default="/data/zhk/models/qwen-3.5-9b",
    #     help="Local HuggingFace model path",
    # )
    # parser.add_argument(
    #     "--output-dir",
    #     type=str,
    #     default="outputs/",
    #     help="Directory to save probing features and report",
    # )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=50,
        help="Maximum number of samples to run",
    )
    parser.add_argument(
        "--layer-spec",
        type=str,
        default="-1,-2,-3,-4",
        help='Layer selection, e.g. "all" or "-1,-2,-3,-4"',
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.2,
        help="Test split ratio by paired keys",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help='Torch device, e.g. "auto", "cuda:0", "cpu"',
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="auto",
        choices=["auto", "float16", "bfloat16", "float32"],
        help="Model dtype",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=4096,
        help="Tokenizer max_length for prompt truncation",
    )
    parser.add_argument(
        "--bootstrap-steps",
        type=int,
        default=1000,
        help="Bootstrap iterations for A/B CI",
    )
    parser.add_argument(
        "--probe-lr",
        type=float,
        default=0.05,
        help="Learning rate for linear probe",
    )
    parser.add_argument(
        "--probe-epochs",
        type=int,
        default=300,
        help="Training epochs for linear probe",
    )
    parser.add_argument(
        "--no-feature-cache",
        action="store_true",
        help="Disable saving extracted feature cache",
    )

    args = parser.parse_args()
    dataset_path = f"datasets/final6/{args.dataset}.json"
    output_dir = f"outputs/{args.dataset}"
    cfg = ProbePipelineConfig(
        dataset_path=dataset_path,
        model_path=model_path,
        output_dir=output_dir,
        max_samples=args.max_samples,
        layer_spec=args.layer_spec,
        test_ratio=args.test_ratio,
        seed=args.seed,
        device=args.device,
        dtype=args.dtype,
        max_length=args.max_length,
        n_bootstrap=args.bootstrap_steps,
        probe_lr=args.probe_lr,
        probe_epochs=args.probe_epochs,
        save_feature_cache=not args.no_feature_cache,
    )

    report = run_pipeline(cfg)
    print(f"Probing pipeline finished. records={report['num_records']}")
    print(f"Report saved to: {cfg.output_dir}/report.json")


if __name__ == "__main__":
    main()
