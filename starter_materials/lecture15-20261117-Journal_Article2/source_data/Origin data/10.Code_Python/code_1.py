import os
import pandas as pd

def merge_csv_files(folder_path):

    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    

    merged_df = pd.DataFrame()
    

    for file in csv_files:
        file_path = os.path.join(folder_path, file)

        df = pd.read_csv(file_path)

        merged_df = pd.concat([merged_df, df], ignore_index=True)
    

    return merged_df


folder_path = 'C://Users//zal//Desktop//global//trade//simpledata and result//merge'

merged_data = merge_csv_files(folder_path)


output_file = 'merged_data.csv'
merged_data.to_csv(output_file, index=False)
print(f"Merged CSV files saved to {output_file}")