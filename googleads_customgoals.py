import os
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime, timedelta

# Setup paths
base_folder = r'A:path/to/directory'
channel_folder = r'A:path/to/directory'
csv_folder = r'A:path/to/directory'
config_path = os.path.join(base_folder, 'googleads_config.yaml')
csv_path = os.path.join(csv_folder, 'gads_customgoals.csv')
log_path = os.path.join(channel_folder, 'Custom Goals', 'gads_customgoals.log')

# Initialize Google Ads client
client = GoogleAdsClient.load_from_storage(config_path)

# Dates
today = datetime.today().date()
start_date = datetime(2022, 1, 1).date()

# Setup logging
def log_message(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {msg}")
    with open(log_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{timestamp} - {msg}\n")

# Load existing CSV data if exists
if os.path.exists(csv_path):
    df_existing = pd.read_csv(csv_path, low_memory=False)
    if 'Date' in df_existing.columns:
        df_existing['Date'] = pd.to_datetime(df_existing['Date'], errors='coerce').dt.date
    else:
        df_existing = pd.DataFrame()
else:
    df_existing = pd.DataFrame()
    

def run_query(client, customer_id, query):
    ga_service = client.get_service("GoogleAdsService")
    response = ga_service.search_stream(customer_id=customer_id, query=query)
    rows = []
    for batch in response:
        for row in batch.results:
            rows.append(row)
    return rows

''' def parse_campaign_conversion_goal(rows):
    data = []
    for row in rows:
        ccg = row.campaign_conversion_goal
        c = row.campaign
        data.append({
            "customer_id": row.customer.id,
            "customer_name": row.customer.descriptive_name,
            "campaign_id": c.id,
            "campaign_name": c.name,
            "campaign_type": c.advertising_channel_type,
            "resource_name": ccg.resource_name,
            "campaign_conversion_goal_category": ccg.category,
            "campaign_conversion_goal_origin": ccg.origin,
            "campaign_conversion_goal_biddable": ccg.biddable,

        })
    return pd.DataFrame(data) '''

def parse_conversion_action(rows):
    data = []
    for row in rows:
        ca = row.conversion_action
        c = row.customer
        s = row.segments
        m = row.metrics
        data.append({
            "segments_date": s.date if s and s.date else None,
            "customer_id": c.id,
            "customer_name": c.descriptive_name,
            "conversion_action_name": ca.name if ca and ca.name else None,
            })
    return pd.DataFrame(data)

def parse_custom_goal(rows):
    data = []
    for row in rows:
        camp = row.campaign
        ccg = row.custom_conversion_goal
        data.append({
            "customer_id": row.customer.id,
            "customer_name": row.customer.descriptive_name,
            "campaign_id": camp.id if hasattr(camp, 'id') else None,
            "campaign_name": camp.name if hasattr(camp, 'name') else None,
            "custom_goal_name": ccg.name if hasattr(ccg, 'name') else None,
            "custom_goal_status": ccg.status if hasattr(ccg, 'status') else None,
            "custom_goal_id": ccg.id if hasattr(ccg, 'id') else None,
        })
    return pd.DataFrame(data)

def main():
    customer_ids = ["11111111", "22222222", "33333333", "44444444", "55555555",
                    ...
                    ]
    '''
    query_conversion_goal =
        SELECT
            customer.descriptive_name,
            campaign_conversion_goal.category,
            campaign_conversion_goal.origin,
            campaign_conversion_goal.biddable,
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type

        FROM
            campaign_conversion_goal
        WHERE
            campaign.status != 'REMOVED' and
            campaign_conversion_goal.biddable = true

    '''

    query_conversion_action = f"""
       SELECT
            conversion_action.include_in_conversions_metric,
            conversion_action.name,
            segments.date,
            customer.id,
            customer.descriptive_name
        FROM conversion_action
        WHERE
            segments.date between '{start_date}' and '{today}'
            and conversion_action.include_in_conversions_metric = true
    """

    query_custom_goal = """
        SELECT
            campaign.id,
            campaign.name,
            custom_conversion_goal.name,
            custom_conversion_goal.status,
            custom_conversion_goal.id,
            customer.id,
            customer.descriptive_name
        FROM conversion_goal_campaign_config

    """
    all_data = []

    for cust_id in customer_ids:
        try:
            # rows_ccg = run_query(client, cust_id, query_conversion_goal)
            rows_ca = run_query(client, cust_id, query_conversion_action)
            rows_cg = run_query(client, cust_id, query_custom_goal)
        except Exception as e:
            print(f"Error fetching data for customer {cust_id}: {e}")

        #  df_ccg = parse_campaign_conversion_goal(rows_ccg)
        df_ca = parse_conversion_action(rows_ca)
        df_cg = parse_custom_goal(rows_cg)

        # Merge dataframes:
        # df_merged = pd.merge(df_ccg, df_cg, on=["campaign_id", "campaign_name", "resource_name","customer_id", "customer_name"], how="outer")
        df_final = pd.merge(df_cg, df_ca, on=["customer_id", "customer_name"], how="outer")
        all_data.append(df_final)

    if all_data:
            df_finally = pd.concat(all_data, ignore_index=True)
            if not df_existing.empty:
                df_finally = pd.concat([df_existing, df_finally], ignore_index=True)

            df_finally.to_csv(csv_path, index=False)
            log_message(f"Data saved successfully to {csv_path}. Total rows: {len(df_final)}")
    else:
        log_message("No new data to save.")

    # combine all data into a single dataframe
        df_finally = pd.concat(all_data, ignore_index=True)

        df_finally.to_csv("./gads_customgoals.csv", index=False)

if __name__ == "__main__":
    main()
