import pandas as pd

# Define file paths
country_file = r"E:\LiuWei\country.csv"
data_file = r"E:\LiuWei\data.csv"
output_file = r"E:\LiuWei\total_production_by_country_and_product.csv"

# Read the list of countries
try:
    countries = pd.read_csv(country_file)
    country_list = countries.iloc[:, 0].tolist()  # Assuming country names are in the first column
    print(f"Successfully read {len(country_list)} countries")
except Exception as e:
    print(f"Error reading the country file: {e}")
    exit()

# Define the list of products to calculate total production for
products = [
    "Cotton seed", "Sesame seed", "Barley", "Buckwheat", "Maize (corn)", "Millet",
    "Mixed grain", "Oats", "Rice", "Rye", "Sorghum", "Wheat", "Green corn (maize)",
    "Cassava, fresh", "Olives", "Potatoes", "Sweet potatoes", "Soya beans",
    "Other beans, green", "Other fruits, n.e.c.", "Other vegetables, fresh n.e.c.",
    "Sugar beet", "Sugar cane"
]

# Read the production data
try:
    data = pd.read_csv(data_file)
    print("Successfully read production data")
except Exception as e:
    print(f"Error reading the production data file: {e}")
    exit()

# Filter the data: by country, product, and year range
try:
    # Filter by country
    filtered_data = data[data.iloc[:, 0].isin(country_list)]  # First column is the country name
    # Filter by product
    filtered_data = filtered_data[filtered_data.iloc[:, 2].isin(products)]  # Third column is the product name
    # Filter by year range
    filtered_data = filtered_data[(filtered_data.iloc[:, 3] >= 1961) & (filtered_data.iloc[:, 3] <= 2022)]  # Fourth column is the year
    print(f"Filtered data contains {len(filtered_data)} records")
except Exception as e:
    print(f"Error filtering the data: {e}")
    exit()

# Group data by country and product, then calculate total production
try:
    # The sixth column contains the production value
    grouped_data = filtered_data.groupby([filtered_data.columns[0], filtered_data.columns[2]])[filtered_data.columns[5]].sum().reset_index()
    grouped_data.columns = ["Country", "Product", "Total Production"]  # Rename columns for clarity
    print("Successfully grouped and calculated total production")
except Exception as e:
    print(f"Error during grouping and aggregation: {e}")
    exit()

# Pivot the data: rows are countries, columns are products, values are total production
try:
    # Use pivot to reshape the data into the desired format
    pivot_data = grouped_data.pivot(index="Country", columns="Product", values="Total Production").fillna(0)
    pivot_data = pivot_data[products]  # Ensure the columns are in the specified product order
    print("Successfully pivoted the data")
except Exception as e:
    print(f"Error during data pivoting: {e}")
    exit()

# Save the result to a CSV file
try:
    pivot_data.to_csv(output_file, index=True, encoding="utf-8-sig")
    print(f"Results saved to: {output_file}")
except Exception as e:
    print(f"Error saving the results: {e}")