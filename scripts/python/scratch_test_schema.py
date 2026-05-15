import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from test_db_conn import run_query

query = "SELECT latest_order_id FROM gbike.rich_user LIMIT 1"
df = run_query(query)
print("Query Success! latest_order_id exists.")
print(df.head())
