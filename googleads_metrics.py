import os
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime, timedelta

# Setup paths
base_folder = r'A:path/to/directory'
channel_folder = r'A:path/to/directory'
csv_folder = r'A:path/to/directory'
config_path = os.path.join(base_folder, 'googleads_config.yaml') #accessed through Google API
csv_path = os.path.join(csv_folder, 'gads_metrics.csv')
log_path = os.path.join(channel_folder, 'Campaign Metrics', 'gads_metrics.log')

# Initialize Google Ads client
client = GoogleAdsClient.load_from_storage(config_path)

# Dates
today = datetime.today().date()
start_date = datetime(2022, 1, 1).date()
last90days = today - timedelta(days=90)

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

def parse_campaign(rows):
    data = []
    for row in rows:
        c = row.campaign
        cb = row.campaign_budget
        s = row.segments
        m = row.metrics
        data.append({
                "customer_name": row.customer.descriptive_name,
                "customer_id": row.customer.id,
                "segments_date": s.date if s and s.date else None,
                "campaign_start_date": c.start_date_time if hasattr(c, 'start_date') else None,
                "campaign_end_date": c.end_date_time if hasattr(c, 'end_date') else None,
                "campaign_id": c.id,
                "campaign_name": c.name,
                "campaign_status": c.status if hasattr(c, 'status') else None,
                "customer_currency": row.customer.currency_code,
                "metrics_cost": (m.cost_micros / 1_000_000) if m and m.cost_micros is not None else None,
                "metrics_all_conversions_value": m.all_conversions_value if m else None,
                # "net_income": (m.all_conversions_value - (m.cost_micros / 1_000_000))
                # if m and m.all_conversions_value is not None and m.cost_micros is not None else None,
                # "ROAS": ((m.all_conversions_value / (m.cost_micros / 1_000_000))
                # if m and m.all_conversions_value is not None and m.cost_micros not in (None, 0) else None),
                "metrics_clicks": m.clicks if m else None,
                "metrics_impressions": m.impressions if m else None,
                "campaign_budget_amount": (cb.amount_micros / 1_000_000) if cb and cb.amount_micros is not None else None,
                "metrics_conversions": m.conversions if m else None,
                "metrics_all_conversions": m.all_conversions if m else None,
                "metrics_cost_per_conversion": m.cost_per_conversion if m else None,
                "metrics_video_views": m.video_trueview_views if m else None,
                "campaign_advertising_channel_type": c.advertising_channel_type if hasattr(c, 'advertising_channel_type') else None,
                "metrics_unique_users": m.unique_users if m else None,
                "metrics_freq": m.average_impression_frequency_per_user if m else None,
            })

    return pd.DataFrame(data)

def parse_last90days(rows):
    data = []
    for row in rows:
        c = row.campaign
        cb = row.campaign_budget
        s = row.segments
        m = row.metrics
        data.append({
                "segments_date": s.date if s and s.date else None,
                "campaign_id": c.id,
                "campaign_name": c.name,
                "metrics_unique_users": m.unique_users if m else None,
                "metrics_freq": m.average_impression_frequency_per_user if m else None,
            })

    return pd.DataFrame(data)

def main():
    customer_ids = ["111111111", "22222222", "33333333", ...
                    ]

    query_campaign = f"""
        SELECT
              customer.descriptive_name,
              customer.id,
              segments.date,
              campaign.start_date_time,
              campaign.end_date_time,
              campaign.id,
              campaign.name,
              campaign.status,
              customer.currency_code,
              metrics.cost_micros,
              metrics.conversions,
              metrics.all_conversions_value,
              metrics.clicks,
              metrics.impressions,
              metrics.unique_users,
              metrics.average_impression_frequency_per_user,
              campaign_budget.amount_micros,
              metrics.all_conversions,
              metrics.cost_per_conversion,
              metrics.video_trueview_views,
              campaign.advertising_channel_type
              
        FROM
              campaign
        WHERE
            segments.date between '{start_date}' and '{today}' AND
            campaign.status != 'REMOVED'
    """
    query_last90days = f"""
        SELECT
              segments.date,
              campaign.id,
              campaign.name,
              metrics.unique_users,
              metrics.average_impression_frequency_per_user
        FROM
              campaign
       WHERE
            segments.date between '{last90days}' and '{today}' AND
            campaign.status != 'REMOVED'
    """
    all_data = []

    for cust_id in customer_ids:
        try:
            rows_camp = run_query(client, cust_id, query_campaign)
            rows_last90 = run_query(client, cust_id, query_last90days)
                   
            df_camp = parse_campaign(rows_camp)
            df_last90 = parse_last90days(rows_last90)
                        
            df_final = pd.merge(df_last90, df_camp, on=["campaign_id", "campaign_name", "segments_date"], how="outer")
           
            if not df_final.empty:
                all_data.append(df_final)
            else:
                print(f"Empty data for customer {cust_id}")
        except Exception as e:
            print(f"Error processing customer {cust_id}: {e}")
            # append  data for all customers into a single list
            
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
        df_finally.to_csv("./gads_metrics.csv", index=False)

            # Get the country code from the df_ccg for a given cust_id
        customer_name = df_camp['customer_name'].iloc[0] if not df_camp.empty else f"UnknownCustomer_{cust_id}"
        country_abbrv = ""
        if '(' in customer_name and ')' in customer_name:
            start_index = customer_name.find('(') + 1
            end_index = customer_name.find(')', start_index)
            if start_index > 0 and end_index > start_index:
                country_abbrv = customer_name[start_index:end_index]
                # Ensure the country code is suitable for a filename
                country_abbrv = "".join([c for c in country_abbrv if c.isalnum() or c in ('_',)]).rstrip()
            
        print("Data '{}' successfully saved to gads_metrics.csv".format(country_abbrv))

if __name__ == "__main__":
    main()
