import os
import sys
import pandas as pd

# Add the utils directory to the Python path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
utils_dir = os.path.join(base_dir, 'scripts/python/utils')
sys.path.append(utils_dir)

from test_mysql_conn import get_engine

def main():
    # Define paths
    sql_path = os.path.join(base_dir, 'scripts/sql/busan3camp_yoy_extract/busan3camp_yoy.sql')
    output_path = os.path.join(base_dir, 'base_data/primary_data/busan3camp_yoy_extract/busan3camp_raw.xlsx')
    
    # Read SQL query template
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            query_template = f.read()
            # Escape '%' characters to prevent SQLAlchemy parameter formatting errors
            query_template = query_template.replace('%', '%%')
    except Exception as e:
        print(f"Error reading SQL file: {e}")
        sys.exit(1)
        
    date_ranges = [
        # 2025 chunks
        ('2025-01-01', '2025-02-01'),
        ('2025-02-01', '2025-03-01'),
        ('2025-03-01', '2025-04-01'),
        ('2025-04-01', '2025-05-01'),
        ('2025-05-01', '2025-05-21'),
        # 2026 chunks
        ('2026-01-01', '2026-02-01'),
        ('2026-02-01', '2026-03-01'),
        ('2026-03-01', '2026-04-01'),
        ('2026-04-01', '2026-05-01'),
        ('2026-05-01', '2026-05-21')
    ]

    print("Executing chunked extraction...")
    engine = get_engine()
    all_dfs = []
    
    for start, end in date_ranges:
        print(f"Extracting: {start} ~ {end}...")
        
        # Format the query with start and end dates
        query = query_template.format(start=start, end=end)
        
        try:
            with engine.connect() as connection:
                df_chunk = pd.read_sql(query, connection)
                if not df_chunk.empty:
                    all_dfs.append(df_chunk)
                print(f"Chunk complete: {len(df_chunk)} rows fetched.")
        except Exception as e:
            print(f"Error during chunk extraction ({start} ~ {end}): {e}")
            sys.exit(1)

    if all_dfs:
        print("Concatenating all chunks...")
        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as xlsx
        print(f"Total rows fetched: {len(final_df)}. Saving to Excel...")
        final_df.to_excel(output_path, index=False)
        print(f"Data saved to: {output_path}")
    else:
        print("No data extracted.")

if __name__ == '__main__':
    main()
