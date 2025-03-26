import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
import numpy as np

def filterCSV(input_file, output_file, columns_to_keep):
    
    # Load the CSV file into a DataFrame
    df = pd.read_csv(input_file, encoding="utf-8-sig")

    # Check if the required columns exist in the DataFrame
    missing_columns = [col for col in columns_to_keep if col not in df.columns]
    if missing_columns:
        print(f"Warning: The following columns are missing from the CSV file: {', '.join(missing_columns)}")

    # Filter the DataFrame to keep only the specified columns
    filtered_df = df[columns_to_keep]

    if "Article Title" in filtered_df.columns:
        filtered_df = filtered_df.rename(columns={"Article Title": "Title"})

    if "Publication Year" in filtered_df.columns:
        filtered_df = filtered_df.rename(columns={"Publication Year": "Year"})

    # Save the filtered DataFrame to a new CSV file
    filtered_df.to_csv(output_file, index=False)

    print(f"Filtered CSV saved to '{output_file}'.")

    return filtered_df

def combineCSV(category):

    csv_files = glob.glob(category+"/*.csv")  # Adjust filename pattern if needed

    # Load and concatenate all files
    df_list = [pd.read_csv(file) for file in csv_files]
    combined_df = pd.concat(df_list, ignore_index=True)

    # Remove duplicates based on the 'Title' or 'DOI' column
    if "Title" in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=["Title"], keep="first")  # Adjust column name if needed

    # Save to a new merged CSV file
    combined_df.to_csv(category+"/combined.csv", index=False)

    print(f"Combined {len(df_list)} files into '{category}/combined.csv' with {len(combined_df)} unique papers.")

    return combined_df

def filterWoS(category):

    columns_to_keep = ["Article Title", "Publication Year", "DOI"]
    input_file = category+"/wos_0.csv"  # Path to your input CSV file
    output_file = category+"/f_wos_0.csv" 

    filtered_wos = filterCSV(input_file, output_file, columns_to_keep)

    return filtered_wos

def filterSCOPUS(category):

    columns_to_keep = ["Title", "Year", "DOI"]
    input_file = category+"/scopus.csv"  # Path to your input CSV file
    output_file = category+"/f_scopus.csv" 

    filtered_scopus = filterCSV(input_file, output_file, columns_to_keep)

    return filtered_scopus

def count_papers_per_year(category):

    csv_files = glob.glob("*.csv")

    # Read and combine all CSV files
    df_list = [pd.read_csv(file, encoding="utf-8-sig") for file in csv_files]
    combined_df = pd.concat(df_list, ignore_index=True)

    # Ensure 'Year' column is in numeric format (handles cases where it is read as string)
    combined_df["Year"] = pd.to_numeric(combined_df["Year"], errors="coerce")

    # Count occurrences of each year
    year_counts = combined_df["Year"].value_counts().sort_index()

    year_counts_df = year_counts.reset_index()
    year_counts_df.columns = ["Year", "Count"]
    year_counts_df.to_csv(category+"/year_counts.csv", index=False)

    # Print and return results
    print(year_counts)

def merge_year_counts():

    # Get list of all year_counts CSV files
    csv_files = glob.glob("year_counts/*_year_counts.csv")  # Adjust if needed

    # Dictionary to store dataframes
    dfs = {}

    # Read and store each CSV file
    for file in csv_files:
        # Extract the category (first word in filename)
        category = os.path.basename(file).split("_")[0]

        # Read the CSV file
        df = pd.read_csv(file)

        # Rename "Count" column to match category
        df.rename(columns={"Count": category}, inplace=True)

        # Store dataframe
        dfs[category] = df

    # Merge all dataframes on "Year"
    merged_df = None
    for category, df in dfs.items():
        if merged_df is None:
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, on="Year", how="outer")

    # Fill NaN values with 0 (for years missing in some categories)
    merged_df = merged_df.fillna(0)

    # Convert "Year" column to integer
    merged_df["Year"] = merged_df["Year"].astype(int)

    # Sort by Year
    merged_df = merged_df.sort_values("Year")

    # Save the merged data
    merged_df.to_csv("combined_year_counts.csv", index=False)

    print(f"Combined {len(csv_files)} files into 'combined_year_counts.csv'")

def drawGraph():
    # Load the combined CSV file
    df = pd.read_csv("combined_year_counts.csv")

    # Convert "Year" to numeric
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    # Fill missing values with 0
    df.fillna(0, inplace=True)

    # Set the starting and ending years for plotting
    start_year = 1990  # Change this to the desired start year
    end_year = 2024    # Change this to the desired end year

    # Filter the DataFrame to include only data between the start and end years (inclusive)
    df_filtered = df[(df["Year"] >= start_year) & (df["Year"] <= end_year)]

    # Set "Year" as the x-axis
    plt.figure(figsize=(10, 6))

    # Plot each category as a separate line
    for category in df_filtered.columns[1:]:  # Skip "Year" column
        # Plot data points
        plt.plot(df_filtered["Year"].values, df_filtered[category].values, marker="o", label=category)
        trendline = False

        if(trendline):
            # Calculate the trendline (linear fit) for the category
            x = df_filtered["Year"].values
            y = df_filtered[category].values
            
            # Perform linear regression (1st degree polynomial)
            coeffs = np.polyfit(x, y, 1)  # coeffs will contain the slope and intercept
            trendline = np.polyval(coeffs, x)  # Apply the polynomial to x

            # Plot the trendline
            plt.plot(x, trendline, linestyle="--", label=f"{category} Trendline")

    # Customize the plot
    plt.xlabel("Year")
    plt.ylabel("Number of Papers")
    plt.title(f"Publication Trends by Category (from {start_year} to {end_year})")
    plt.legend(title="Category", loc="upper left", bbox_to_anchor=(1, 1))
    plt.grid(True)

    # Set y-axis limits to avoid negative values
    plt.ylim(bottom=0)  # This ensures that the y-axis starts from 0 (no negative values)

    # Show the plot
    plt.tight_layout()  # Adjust layout to fit legend
    plt.show()

def main():
    
    # columns_to_keep = ["Title", "Year", "DOI"]
    # columns_to_keep = ["Article Title", "Publication Year", "DOI"]
    # input_file = "wos.csv"  # Path to your input CSV file
    # output_file = "f_wos.csv"  # Path for the output filtered CSV file

    # filterCSV(input_file, output_file, columns_to_keep)

    category = "task"

    # filtered_wos = filterWoS(category)
    # filtered_scopus = filterSCOPUS(category)

    # combineCSV(category)
    # count_papers_per_year(category)
    drawGraph()

if __name__ == "__main__":
    main()