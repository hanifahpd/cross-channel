# -*- coding: utf-8 -*-
"""based on GoogleAds.ipynb

Original file is located at
    https://colab.research.google.com/drive/12lUILLD2L4cKwRDVw6Qr-BDZl_rzvGdk

This code snippet is to fetch Google Ads through API with the main focus to get Conversion Goals in Conversion Action setting
    """

import os
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime, timedelta

# Setup paths
base_folder = r'G:/Reports/92_Google_ads/GA_API/'
csv_folder = r'G:/Source Reports/92_Google_ads/'
config_path = os.path.join(base_folder, 'googleads_config_2025.yaml')
csv_path = os.path.join(csv_folder, 'gads_convgoals.csv')
log_path = os.path.join(base_folder, 'gads_convgoals.log')

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

def parse_campaign_conversion_goal(rows):
    data = []
    for row in rows:
        ccg = row.campaign_conversion_goal
        c = row.campaign
        data.append({
            "customer_name": row.customer.descriptive_name,
            "campaign_id": c.id,
            "campaign_name": c.name,
            "campaign_type": c.advertising_channel_type,
            "campaign_conversion_goal_resource_name": ccg.resource_name,
            "campaign_conversion_goal_category": ccg.category,
            "campaign_conversion_goal_origin": ccg.origin,
            "campaign_conversion_goal_biddable": ccg.biddable,

        })
    return pd.DataFrame(data)

def parse_conversion_action(rows):
    data = []
    for row in rows:
        ca = row.conversion_action
        s = row.segments
        m = row.metrics
        data.append({
            "include_in_conversions_metric": ca.include_in_conversions_metric,
            "segments_date": s.date if s and s.date else None,
            })
    return pd.DataFrame(data)

def parse_campaign(rows):
    data = []
    for row in rows:
        c = row.campaign
        s = row.segments
        m = row.metrics
        data.append({
            "segments_date": s.date if s and s.date else None,
            "campaign_id": c.id,
            "campaign_name": c.name,
            "campaign_type": c.advertising_channel_type,
            "segments_conversion_action_name": s.conversion_action_name if s else None,
            "segments_conversion_action_category": s.conversion_action_category if s else None,
            "metrics_conversions": m.conversions if m else None,
            "metrics_all_conversions": m.all_conversions if m else None,
            "metrics_view_through_conversions": m.view_through_conversions if m else None,
            "metrics_all_conversions_value": m.all_conversions_value if m else None,
            "metrics_conversions_value": m.conversions_value if m else None,
            "metrics_conversions_value_by_conversion_date": m.conversions_value_by_conversion_date if m else None,
            })
    return pd.DataFrame(data)

def main():
    customer_ids = ["7798263573", "4129748388", "8255223189", "8181393760", "4903654018",
                    "9591862767", "9037951827", "4754830474", "2433792321", "9373069304",
                    "3443455271", "9678021940", "1476502829", "9370094416", "5872445404",
                    "3237965092", "8708204967", "4427721949", "8777571444", "8104899705", "4439852533"
                    ]

    query_conversion_goal = """
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
        """

    query_conversion_action = f"""
        SELECT
            conversion_action.resource_name,
            conversion_action.include_in_conversions_metric,
            segments.date
        FROM
            conversion_action
        WHERE
           segments.date between '{start_date}' and '{today}'
           and conversion_action.include_in_conversions_metric = true
    """

    query_campaign = f"""
        SELECT
            segments.date,
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,
            segments.conversion_action_name,
            segments.conversion_action_category,
            metrics.conversions,
            metrics.all_conversions,
            metrics.view_through_conversions,
            metrics.all_conversions_value,
            metrics.conversions_value,
            metrics.conversions_value_by_conversion_date
        FROM
            campaign
        WHERE
            segments.date between '{start_date}' and '{today}' AND
            campaign.status != 'REMOVED'
    """
    all_data = []

    for cust_id in customer_ids:
      try:
        # 1. Fetch Data
        rows_ccg = run_query(client, cust_id, query_conversion_goal)
        rows_ca = run_query(client, cust_id, query_conversion_action)
        rows_camp = run_query(client, cust_id, query_campaign)

        # 2. Parse Data
        df_ccg = parse_campaign_conversion_goal(rows_ccg)
        df_ca = parse_conversion_action(rows_ca)
        df_camp = parse_campaign(rows_camp)

        # 3. Safe Merge (Proteksi jika ada DF kosong)
        if not df_ccg.empty and not df_camp.empty:
            df_merged = pd.merge(df_ccg, df_camp, on=["campaign_id", "campaign_name", "campaign_type"],
            how="outer",)
        else:
            df_merged = df_ccg if not df_ccg.empty else df_camp

        if not df_merged.empty and not df_ca.empty:
            df_final = pd.merge(df_merged, df_ca, on=["segments_date"], how="outer")
        else:
            df_final = df_merged if not df_merged.empty else df_ca

      # 4. Tambahkan ke list jika ada data
        if not df_final.empty:
            all_data.append(df_final)
        else:
            print(f"Empty data for customer {cust_id}")
      except Exception as e:
        print(f"Error processing customer {cust_id}: {e}")
        # append  data for all customers into a single dataframe
          
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
        print("Data '{}' successfully saved to gads_convgoals.csv".format(country_abbrv))

if __name__ == "__main__":
    main()
