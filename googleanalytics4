import os
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    FilterExpression,
    Filter,
    RunReportRequest,
)

# 1. Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "G:/Reports/103_Cross_Channel/GA4/datasource API/GA4CrossChannel_ServiceAccount-2df690656289.json"
PROPERTY_IDS = ['1111111111', '2222222222', '3333333333'] 
OUTPUT_CSV = 'H:/path/to/directory/filename.csv'

def get_ga4_data(property_id):
    client = BetaAnalyticsDataClient()
    target_channels = [ # set based on whats needed
        "facebook / cpc", 
        "google / cpc", 
        "pinterest / cpc", 
        "bing / cpc", 
        "google / organic", 
        "bing / organic", 
        "(direct) / (none)", 
        "sklik / cpc"
    ]
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[ #check the keyword in google analytics query
            Dimension(name="date"),
            Dimension(name="sessionCampaignName"),
            Dimension(name="sessionManualAdContent"),
            Dimension(name="sessionManualTerm"),
            Dimension(name="sessionSourceMedium")
        ],
        metrics=[ #check the keyword in google analytics query
            Metric(name="keyEvents:purchase"),
            Metric(name="ecommercePurchases"),
            Metric(name="totalRevenue"),
            Metric(name="sessions"),
            Metric(name="userEngagementDuration"),
            Metric(name="newUsers"),
            Metric(name="engagedSessions"),
            Metric(name="addToCarts"),
            Metric(name="totalUsers")
        ],
        date_ranges=[DateRange(start_date="2022-01-01", end_date="today")], #set the date range here
        #filter is opotional, but help in getting just the necessary data
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionSourceMedium",
                in_list_filter=Filter.InListFilter(
                    values=target_channels
                ),
            )
        ),
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"), desc=True)]
    )

    return client.run_report(request)

def main():
    all_data = []

    for pid in PROPERTY_IDS:
        print(f"Requesting data for Property: {pid}...")
        try:
            response = get_ga4_data(pid)
            
            # Extract headers (once)
            dim_headers = [header.name for header in response.dimension_headers]
            met_headers = [header.name for header in response.metric_headers]
            
            # Parse rows
            for row in response.rows:
                row_dict = {"property_id": pid}
                
                # Map dimensions
                for i, val in enumerate(row.dimension_values):
                    row_dict[dim_headers[i]] = val.value
                
                # Map metrics
                for i, val in enumerate(row.metric_values):
                    row_dict[met_headers[i]] = val.value
                
                all_data.append(row_dict)

        except Exception as e:
            print(f"Error for property {pid}: {e}")

    # 2. Save to CSV
    if all_data:
        df = pd.DataFrame(all_data)
        df['Type'] = 'Device'
        # Format the date column if it exists
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        df = df.sort_values(by=['property_id', 'date'], ascending=[True, True])  
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"\nSUCCESS! File saved to {OUTPUT_CSV}")
        print(f"Total rows collected: {len(df)}")
    else:
        print("No data collected.")

if __name__ == "__main__":
    main()

