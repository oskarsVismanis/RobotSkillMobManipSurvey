from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

folder = Path("../data/combined/new_datasets/all_databases/full")
output_file = "full_dataset_publishing_stats_summary.csv"

all_data = {}

# -------------------------
# Load and process CSVs
# -------------------------
for csv_file in folder.glob("*.csv"):
    try:
        df = pd.read_csv(csv_file)

        if "year" not in df.columns:
            print(f"Skipping {csv_file.name} (no 'year')")
            continue

        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df.dropna(subset=["year"])
        df["year"] = df["year"].astype(int)

        counts = df["year"].value_counts().sort_index()

        all_data[csv_file.stem] = counts

        print(f"Processed {csv_file.name}")

    except Exception as e:
        print(f"Error in {csv_file.name}: {e}")

# -------------------------
# Pivot table
# -------------------------
pivot_df = pd.DataFrame(all_data).T
pivot_df = pivot_df.fillna(0).astype(int)
pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)

# Save CSV
pivot_df.to_csv(output_file)
print(f"Saved pivot table to {output_file}")

# -------------------------
# HEATMAP
# -------------------------
# plt.figure(figsize=(12, 6))
# plt.imshow(pivot_df.values, aspect="auto")

# plt.xticks(range(len(pivot_df.columns)), pivot_df.columns, rotation=90)
# plt.yticks(range(len(pivot_df.index)), pivot_df.index)

# plt.colorbar(label="Number of papers")

# plt.title("Publication Years per Dataset (Heatmap)")
# plt.xlabel("Year")
# plt.ylabel("Dataset")

# plt.tight_layout()
# plt.show()

# -------------------------
# COLUMN / STACKED BAR CHART
# -------------------------
# plt.figure(figsize=(14, 6))

# pivot_df.plot(kind="bar", stacked=True, figsize=(14, 6), ax=plt.gca())

# plt.title("Publication Year Distribution per Dataset (Stacked)")
# plt.xlabel("Dataset (CSV file)")
# plt.ylabel("Number of papers")

# plt.legend(title="Year", bbox_to_anchor=(1.05, 1), loc="upper left")

# plt.tight_layout()
# plt.show()

# -------------------------
# GLOBAL YEAR TREND (sum across all datasets)
# -------------------------
start_year = 2000
end_year = 2025

# -------------------------
# Rename legend entries here
# -------------------------
name_map = {
    "action_full_combined_results": "action",
    "behaviour_full_combined_results": "behaviour",
    "capability_full_combined_results": "capability",
    "manipulate_full_combined_results": "manipulate",
    "motion_movement_full_combined_results": "motion / movement",
    "motor_full_combined_results": "motor",
    "navigate_full_combined_results": "navigate",
    "skill_full_combined_results": "skill",
    "task_full_combined_results": "task",
}

years = [y for y in pivot_df.columns if start_year <= int(y) <= end_year]

plot_order = [
    "action_full_combined_results",
    "behaviour_full_combined_results",
    "capability_full_combined_results",
    "manipulate_full_combined_results",
    "motion_movement_full_combined_results",
    "motor_full_combined_results",
    "navigate_full_combined_results",
    "skill_full_combined_results",
    "task_full_combined_results",
]

plt.figure(figsize=(14, 6))

for dataset in plot_order:
    if dataset not in pivot_df.index:
        continue

    # label = name_map.get(dataset, dataset)
    label = name_map.get(dataset, dataset).replace("/", "/\n")

    plt.plot(
        years,
        pivot_df.loc[dataset, years],
        marker="o",
        linewidth=1,
        alpha=0.7,
        label=label
    )

ax = plt.gca()

# # Axis limits
# ax.set_xlim(start_year, end_year)
# ax.margins(x=0)

# # Major ticks every 5 years (labeled)
# ax.set_xticks(range(start_year, end_year + 1, 5))

# # Minor ticks every year (unlabeled)
# ax.xaxis.set_minor_locator(MultipleLocator(1))

# # Gridlines
# ax.grid(True, which="major", axis="both", alpha=0.4)
# ax.grid(True, which="minor", axis="x", alpha=0.2)

ax.tick_params(axis="x", labelsize=12)
ax.tick_params(axis="y", labelsize=12)

# X axis
ax.set_xlim(start_year, end_year)
ax.set_xticks(range(start_year, end_year + 1, 5))
ax.xaxis.set_minor_locator(MultipleLocator(1))

# Y axis
ax.yaxis.set_major_locator(MultipleLocator(50))
ax.yaxis.set_minor_locator(MultipleLocator(10))

# Grid
ax.grid(True, which="major", axis="both", alpha=0.4)
ax.grid(True, which="minor", axis="both", alpha=0.2)
# ax.grid(True, which="minor", axis="x", alpha=0.2)

plt.title(f"Publication Trend ({start_year}-{end_year})")
plt.xlabel("Year", fontsize=13)
plt.ylabel("Num. of papers", fontsize=13)

plt.legend(bbox_to_anchor=(1.0, 1), loc="upper left", fontsize=13)

plt.tight_layout()
plt.show()