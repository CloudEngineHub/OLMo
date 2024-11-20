# python scripts/scaling/step2.py -k main -c scripts/scaling/step2.json -o figure/peteish-final/step2_main.png
# python scripts/scaling/step2.py -k main_mc -c scripts/scaling/step2_mc.json -o figure/peteish-final/step2_mc_main.png -y mc_acc

import argparse

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from olmo.scaling.scaling_laws.fitting_functions import (
    get_coefficients,
    get_std_errors,
    grad_sigmoid_fit,
    sigmoid,
    sigmoid_fit,
)
from olmo.scaling.scaling_laws.utils import (
    get_final_configs,
    get_step2_data_by_name,
    get_task_sets,
    prettify,
    tasks,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keys", nargs="+", default=[], help="Key(s) for tasks")
    parser.add_argument(
        "-y", "--y_metric", default="rc_acc", choices=["rc_acc", "mc_acc"], help="Metric to predict"
    )
    parser.add_argument("--moving_avg", type=int, default=1, help="Moving average for bpb loss")
    parser.add_argument(
        "--skip_perc",
        type=float,
        default=0.0,
        help="Percentage of intermediate ckpts to skip from the beginning (for loss to accuracy fitting)",
    )
    parser.add_argument("-c", "--config-path", type=str, required=True, help="Path to config file")
    parser.add_argument("-o", "--output-path", type=str, required=True, help="Path to write output figure")
    args = parser.parse_args()

    return args


def fit_step2(data_by_name, task_name, y_metric):
    train_xs, train_ys = [], []
    for name, data in data_by_name.items():
        if data["mode"] == "train":
            train_xs += data["xs"]
            train_ys += data["ys"]
        else:
            data["xs"] = data["xs"][-1:]
            data["ys"] = data["ys"][-1:]

    # add ideal points (these are not plotted)
    train_xs.append(0.0)
    train_ys.append(tasks[task_name].task_maximum)
    train_xs.append(max(train_xs))
    train_ys.append(tasks[task_name].task_minimum)

    # fit the parameters
    coefficients, cov = get_coefficients(
        train_xs,
        train_ys,
        sigmoid,
        p0=[tasks[task_name].task_minimum - 1.0, 0.9, 3.0, 1.0],
        bounds=([-1.0, 0.0, 0.0, 0.0], [0.0, np.inf, np.inf, 1.0]),
        disp=False,
        return_cov=True,
    )

    return coefficients, cov


def predict_step2(configs, data_by_name, coefficients, cov, y_metric):
    predicted_data_by_name = {}
    for name, data in data_by_name.items():
        config = configs[name]
        predicted_data_by_name[name] = {
            "xs": data["xs"],
            "ys": [sigmoid(x, *coefficients) for x in data["xs"]],
        }
        if config.mode == "eval":
            for x, y, y_pred in zip(data["xs"], data["ys"], predicted_data_by_name[name]["ys"]):
                rel_error = (y_pred - y) / y
                std_error = get_std_errors([x], [y_pred], coefficients, cov, sigmoid_fit, grad_sigmoid_fit)[0]
                delta_error = 1.96 * std_error

    xmin = 0.9 * min(min(data["xs"]) for data in data_by_name.values())
    xmax = max(max(data["xs"]) for data in data_by_name.values())
    xs = np.linspace(xmin, xmax, 100)
    plotted_predicted_data = {
        "xs": xs,
        "ys": [sigmoid(x, *coefficients) for x in xs],
    }

    return predicted_data_by_name, plotted_predicted_data, (y, y_pred, rel_error, delta_error)


def plot_step2(
    configs,
    data_by_name,
    predicted_data_by_name,
    plotted_predicted_data,
    task_name,
    fit_str,
    y_metric,
    coefficients,
    cov,
    ax=plt.gca(),
):
    std_errors = get_std_errors(
        plotted_predicted_data["xs"],
        plotted_predicted_data["ys"],
        coefficients,
        cov,
        sigmoid_fit,
        grad_sigmoid_fit,
    )

    # Compute prediction intervals
    plotted_y_lower = plotted_predicted_data["ys"] - 1.96 * std_errors
    plotted_y_upper = plotted_predicted_data["ys"] + 1.96 * std_errors
    unsigned_rel_errs = []
    for name, data in data_by_name.items():
        config = configs[name]
        predicted_data = predicted_data_by_name[name]

        ax.scatter(
            data["xs"],
            data["ys"],
            color=config.color,
            marker="o" if config.mode == "train" else "x",
            s=10,
            label=f"{config.label} ({'fitted' if config.mode == 'train' else 'target'})",
        )
        for x, y, y_pred in zip(data["xs"], data["ys"], predicted_data["ys"]):
            rel_error = (y_pred - y) / y

            if config.mode == "train":
                unsigned_rel_errs.append(abs(rel_error))
            else:
                ax.scatter(
                    x,
                    y_pred,
                    color=config.color,
                    marker="o",
                    s=10,
                    label=f"{config.label} ({'predicted'})",
                )
                ax.annotate(
                    f"{np.abs(rel_error) * 100:.1f}%",
                    (x, y),
                    textcoords="offset points",
                    xytext=(3, 3),
                    ha="left",
                    va="bottom",
                    fontsize=8,
                    color=config.color,
                )
    avg_unsigned_rel_err = np.mean(unsigned_rel_errs)

    # plot the fitted curve
    ax.plot(
        plotted_predicted_data["xs"],
        plotted_predicted_data["ys"],
        color="black",
        linestyle="--",
        linewidth=1.5,
    )

    ax.fill_between(plotted_predicted_data["xs"], plotted_y_lower, plotted_y_upper, color="pink", alpha=0.3)

    ax.legend(loc="lower right", ncols=1, fontsize=8)
    ax.set_xlabel("Task loss")
    if y_metric == "rc_acc":
        ax.set_ylabel("Task RC accuracy")
    elif y_metric == "mc_acc":
        ax.set_ylabel("Task MC accuracy")
    else:
        raise ValueError(f"Invalid y_metric: {y_metric}")
    ax.set_ylim([0, 1.0])
    ax.set_title(
        f"{task_name}\n{fit_str}\navg rel error on fitting = {avg_unsigned_rel_err * 100:.2f}%",
        fontsize=9,
    )


def str_sigmoid(coefficients):
    a, x0, k, b = coefficients
    return f"Acc(L) = {a:.2f} / (1 + e^(-{k:.2f}(L - {x0:.2f}))) + {b:.2f}"


def main():
    args = parse_args()

    configs = get_final_configs(args.config_path)

    args.keys = get_task_sets(args.keys)

    sns.set_style("whitegrid")
    num_tasks = len(args.keys)
    num_cols = min(4, num_tasks)
    num_rows = (num_tasks + num_cols - 1) // num_cols
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(3.75 * num_cols, 3.25 * num_rows), squeeze=False)

    results = "Task Name | Actual Value | Predicted Value | Relative Error"

    for i, task_name in enumerate(args.keys):
        data_by_name = get_step2_data_by_name(
            configs, task_name, y_metric=args.y_metric, moving_avg=args.moving_avg, skip_perc=args.skip_perc
        )

        coefficients, cov = fit_step2(data_by_name, task_name, args.y_metric)
        a, x0, k, b = coefficients

        # make predictions
        predicted_data_by_name, plotted_predicted_data, (y, y_pred, rel_error, delta_error) = predict_step2(
            configs, data_by_name, coefficients, cov, y_metric=args.y_metric
        )

        results += f"\n{task_name} | {prettify(y, False)} | {prettify(y_pred, False)} | {prettify(rel_error)}"

        # plot the actual and predicted data
        ax = axes[i // num_cols][i % num_cols]

        plot_step2(
            configs,
            data_by_name,
            predicted_data_by_name,
            plotted_predicted_data,
            task_name,
            str_sigmoid(coefficients),
            args.y_metric,
            coefficients,
            cov,
            ax=ax,
        )

    fig.tight_layout()
    fig.savefig(args.output_path, dpi=300)

    print(results)


if __name__ == "__main__":
    main()
