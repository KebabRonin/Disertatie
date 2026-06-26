import argparse
import os
import re

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from tqdm import tqdm

ENTRY_RE = re.compile(r"([A-Za-z0-9_]+)\s*-\s*([+-]?\d+(?:\.\d+)?)\s*%")
RESTART_RE = re.compile(r".*\.restarting.*", re.IGNORECASE)
GIF_FRAME_DURATION_MS = 1000 // 30


def parse_mutation_blocks(handle, total_bytes=None, track_restarts=False):
    blocks = []
    restart_flags = []
    current = None
    fallback_lines = []
    pending_restart = False

    with tqdm(total=total_bytes, unit="B", unit_scale=True, desc="Parsing blocks") as progress:
        for raw_line in handle:
            progress.update(len(raw_line))
            line = raw_line.decode("utf-8", errors="ignore").rstrip("\r\n")
            if track_restarts and RESTART_RE.match(line):
                pending_restart = True
            if "Mutation rates for this generation" in line:
                if current is not None:
                    blocks.append(current)
                    restart_flags.append(pending_restart)
                current = []
                pending_restart = False
                continue
            if current is None:
                if ENTRY_RE.search(line):
                    fallback_lines.append(line)
                continue
            current.append(line)

    if current is not None:
        blocks.append(current)
        restart_flags.append(pending_restart)

    if not blocks:
        # Fallback: parse the whole file as a single block.
        blocks = [fallback_lines]
        restart_flags = [False]
    if not track_restarts:
        restart_flags = [False] * len(blocks)
    return blocks, restart_flags


def parse_block(lines):
    values = {}
    for line in lines:
        for match in ENTRY_RE.finditer(line):
            label = match.group(1)
            value = float(match.group(2))
            if label.startswith("f1_"):
                continue
            if value < 0:
                continue
            values[label] = value
    return values


def build_series(blocks):
    blocks_with_flags, restart_flags = (blocks, [False] * len(blocks)) if isinstance(blocks, list) and blocks and isinstance(blocks[0], list) else (blocks[0], blocks[1])
    return build_series_with_restarts(blocks_with_flags, restart_flags)


def build_series_with_restarts(blocks, restart_flags):
    records = [parse_block(block) for block in blocks]
    labels = []
    for record in records:
        for label in record:
            if label not in labels:
                labels.append(label)

    series = {label: [] for label in labels}
    for record in records:
        for label in labels:
            series[label].append(record.get(label, np.nan))
    return labels, series, restart_flags


def build_ascii_report(labels, normalized_values):
    return build_ascii_report_with_restarts(labels, normalized_values, [False] * normalized_values.shape[1])


def build_ascii_report_with_restarts(labels, normalized_values, restart_flags):
    means = np.nanmean(normalized_values, axis=1)
    mins = np.nanmin(normalized_values, axis=1)
    maxs = np.nanmax(normalized_values, axis=1)
    stds = np.nanstd(normalized_values, axis=1)

    frame_means = np.nanmean(normalized_values, axis=0)
    frame_maxes = np.nanmax(normalized_values, axis=0)

    top_mean = sorted(
        ((labels[index], means[index], mins[index], maxs[index], stds[index]) for index in range(len(labels))),
        key=lambda row: row[1],
        reverse=True,
    )
    most_variable = sorted(
        ((labels[index], means[index], mins[index], maxs[index], stds[index]) for index in range(len(labels))),
        key=lambda row: row[4],
        reverse=True,
    )

    def fmt_row(row):
        label, mean, min_val, max_val, std = row
        return f"{label:<12} mean={mean:0.4f} min={min_val:0.4f} max={max_val:0.4f} std={std:0.4f}"

    report_lines = [
        "Mutation rate summary (normalized probabilities)",
        "=" * 54,
        f"Frames analyzed: {normalized_values.shape[1]}",
        f"Labels plotted:   {len(labels)}",
        f"Per-frame mean share: {float(np.nanmean(frame_means)):0.4f}",
        f"Per-frame peak share: {float(np.nanmean(frame_maxes)):0.4f}",
        "",
        "Top labels by average share:",
    ]

    for row in top_mean[:10]:
        report_lines.append(f"  {fmt_row(row)}")

    report_lines.extend([
        "",
        "Most variable labels:",
    ])

    for row in most_variable[:10]:
        report_lines.append(f"  {fmt_row(row)}")

    report_lines.extend([
        "",
        "Frame snapshots:",
    ])

    snapshot_frames = [0, 1, 2, 9, 49, 99, 199, 499, 999, normalized_values.shape[1] - 1]
    seen_frames = set()
    for frame_index in snapshot_frames:
        if frame_index < 0 or frame_index >= normalized_values.shape[1]:
            continue
        if frame_index in seen_frames:
            continue
        seen_frames.add(frame_index)
        column = normalized_values[:, frame_index]
        order = np.argsort(column)[::-1]
        top_five = ", ".join(f"{labels[index]}={column[index]:0.4f}" for index in order[:5])
        restart_marker = " [RESTART]" if restart_flags[frame_index] else ""
        report_lines.append(f"  generation {frame_index + 1:>4}: {top_five}{restart_marker}")

    return "\n".join(report_lines)


def draw_animation(labels, series, output_path, restart_flags=None):
    if restart_flags is None:
        restart_flags = [False] * len(next(iter(series.values())))
    generations = len(next(iter(series.values())))
    values = np.vstack([series[label] for label in labels])
    values = values.astype(float)

    column_sums = np.nansum(values, axis=0)
    normalized_values = np.divide(
        values,
        column_sums,
        out=np.zeros_like(values, dtype=float),
        where=column_sums > 0,
    )

    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("No numeric mutation probabilities found to plot.")

    left = 0.0
    right = 1.0

    width = 1400
    row_height = 28
    top_margin = 84
    bottom_margin = 36
    left_margin = 300
    right_margin = 60
    height = top_margin + bottom_margin + max(1, len(labels)) * row_height

    font = ImageFont.load_default()
    title_font = ImageFont.load_default()

    def measure(draw, text):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def render_frame(frame):
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        title = f"Normalized mutation probability evolution - generation {frame + 1} / {generations}"
        draw.text((20, 18), title, fill="#111111", font=title_font)
        draw.text((20, 40), "Normalized probability", fill="#444444", font=font)

        axis_y = top_margin - 10
        axis_left = left_margin
        axis_right = width - right_margin
        draw.line((axis_left, axis_y, axis_right, axis_y), fill="#444444", width=1)

        zero_x = axis_left + int((0.0 - left) / (right - left) * (axis_right - axis_left))
        draw.line((zero_x, top_margin - 14, zero_x, height - bottom_margin + 6), fill="#666666", width=1)

        current = normalized_values[:, frame]
        for index, (label, val) in enumerate(zip(labels, current)):
            y = top_margin + index * row_height
            draw.text((20, y + 2), label, fill="#111111", font=font)

            if np.isnan(val):
                bar_color = "#bbbbbb"
                val = 0.0
            else:
                bar_color = "#1f77b4"

            bar_end = zero_x + int((val / (right - left)) * (axis_right - axis_left))
            x0, x1 = sorted((zero_x, bar_end))
            draw.rectangle((x0, y + 4, x1, y + row_height - 6), fill=bar_color)

            value_text = f"{val:.3f}"
            value_width, _ = measure(draw, value_text)
            text_x = min(axis_right - value_width, max(axis_left + 6, x1 + 8))
            draw.text((text_x, y + 2), value_text, fill="#222222", font=font)

        return image

    first_frame = render_frame(0)
    first_frame.save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=(render_frame(frame) for frame in range(1, generations)),
        duration=GIF_FRAME_DURATION_MS,
        loop=0,
        optimize=False,
    )

    return build_ascii_report_with_restarts(labels, normalized_values, restart_flags)


def main():
    parser = argparse.ArgumentParser(description="Parse mutation probability logs and generate a GIF bar plot.")
    parser.add_argument("file", help="Input log file containing mutation probability blocks.")
    args = parser.parse_args()

    input_path = args.file
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    total_bytes = os.path.getsize(input_path)
    with open(input_path, "rb") as handle:
        blocks, restart_flags = parse_mutation_blocks(handle, total_bytes=total_bytes, track_restarts=True)
    if not blocks or all(not parse_block(block) for block in blocks):
        raise ValueError("No mutation probability blocks found in the input file.")

    labels, series, restart_flags = build_series_with_restarts(blocks, restart_flags)

    import re
    idx = re.findall(r'results_(\d+)\.stdout', input_path)[0]
    output_path = os.path.join(os.path.dirname(input_path), f"probgif_{idx}.gif")
    report = draw_animation(labels, series, output_path, restart_flags)
    print(f"Saved GIF to {output_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
