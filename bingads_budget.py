from get_started import *
from bingads.v13.reporting import *
from bingads import ServiceClient

# The report file extension type.
REPORT_FILE_FORMAT='Csv'

# The directory for the report files.
FILE_DIRECTORY= r'A:path/to/directory'

# The maximum amount of time (in milliseconds) that you want to wait for the report download.
# TIMEOUT_IN_MILLISECONDS=3600000

def main(authorization_data):
    try:
        # You can submit one of the example reports, or build your own.

        report_request=get_report_request(authorization_data.account_id)
        
        reporting_download_parameters = ReportingDownloadParameters(
            report_request=report_request,
            result_file_directory = FILE_DIRECTORY, 
            result_file_name = RESULT_FILE_NAME, 
            overwrite_result_file = True )

        #The download_report helper function downloads the report and summarizes results.
        output_status_message("-----\nAwaiting download_report...")
        download_report(reporting_download_parameters)

    except WebFault as ex:
        output_webfault_errors(ex)
    except Exception as ex:
        output_status_message(ex)


def download_report(reporting_download_parameters):
    global reporting_service_manager
    report_container = reporting_service_manager.download_report(reporting_download_parameters)

    if(report_container == None):
        output_status_message("There is no report data for the submitted report request parameters.")
        sys.exit(0)

    #Once you have a Report object via either workflow above, you can access the metadata and report records. 

    record_count = report_container.record_count
    output_status_message("ReportName: {0}".format(report_container.report_name))
    output_status_message("ReportTimeStart: {0}".format(report_container.report_time_start))
    output_status_message("ReportTimeEnd: {0}".format(report_container.report_time_end))
    output_status_message("LastCompletedAvailableDate: {0}".format(report_container.last_completed_available_date))
    output_status_message("ReportAggregation: {0}".format(report_container.report_aggregation))
    output_status_message("ReportColumns: {0}".format("; ".join(str(column) for column in report_container.report_columns)))
    output_status_message("ReportRecordCount: {0}".format(record_count))

    #Analyze and output performance statistics

    if "Impressions" in report_container.report_columns and \
        "Clicks" in report_container.report_columns and \
        "Spend" in report_container.report_columns:

        report_record_iterable = report_container.report_records

        total_impressions = 0
        total_clicks = 0
        total_spend = 0
        for record in report_record_iterable:
            total_impressions += record.int_value("Impressions")
            total_clicks += record.int_value("Clicks")
            total_spend += record.int_value("Spend")
            
        output_status_message("Total Impressions: {0}".format(total_impressions))
        output_status_message("Total Clicks: {0}".format(total_clicks))
        output_status_message("Total Spend: {0}".format(total_spend))
        output_status_message("Average Impressions: {0}".format(total_impressions * 1.0 / record_count))
        output_status_message("Average Clicks: {0}".format(total_clicks * 1.0 / record_count))
        
    #Be sure to close the report.
    report_container.close()

def get_report_request(account_id):
    """ 
    Use a sample report request or build your own. 
    """
    exclude_column_headers=False
    exclude_report_footer=True
    exclude_report_header=True
    time=reporting_service.factory.create('ReportTime')
    time.PredefinedTime=None
    time.ReportTimeZone='SarajevoSkopjeWarsawZagreb'
    
    # Create Date objects for custom range
    time.CustomDateRangeStart = reporting_service.factory.create('Date')
    time.CustomDateRangeEnd = reporting_service.factory.create('Date')
    
    time.CustomDateRangeStart.Day = 1
    time.CustomDateRangeStart.Month = 1
    time.CustomDateRangeStart.Year = 2023
    #setting today as end range
    from datetime import timedelta
    today = datetime.now()
    time.CustomDateRangeEnd.Day = today.day
    time.CustomDateRangeEnd.Month = today.month
    time.CustomDateRangeEnd.Year = today.year
  
    return_only_complete_data=False

    #BudgetSummaryReportRequest does not contain a definition for Aggregation.
    budget_summary_report_request=get_budget_summary_report_request(
        account_id=account_id,
        exclude_column_headers=exclude_column_headers,
        exclude_report_footer=exclude_report_footer,
        exclude_report_header=exclude_report_header,
        report_file_format=REPORT_FILE_FORMAT,
        return_only_complete_data=return_only_complete_data,
        time=time)

    return budget_summary_report_request

def get_budget_summary_report_request(
        account_id,
        exclude_column_headers,
        exclude_report_footer,
        exclude_report_header,
        report_file_format,
        return_only_complete_data,
        time):

    report_request=reporting_service.factory.create('BudgetSummaryReportRequest')
    report_request.ExcludeColumnHeaders=exclude_column_headers
    report_request.ExcludeReportFooter=exclude_report_footer
    report_request.ExcludeReportHeader=exclude_report_header
    report_request.Format=report_file_format
    report_request.ReturnOnlyCompleteData=return_only_complete_data
    report_request.Time=time    
    report_request.ReportName="Beliani Global Budget Summary Report"
    scope=reporting_service.factory.create('AccountThroughCampaignReportScope')
    scope.AccountIds={'long': [account_id] }
    scope.Campaigns=None
    report_request.Scope=scope     

    report_columns=reporting_service.factory.create('ArrayOfBudgetSummaryReportColumn')
    report_columns.BudgetSummaryReportColumn.append([
        'Date',
        'AccountName',
        'AccountId',
        'CampaignName',
        'CampaignId',
        'CurrencyCode',
        'MonthlyBudget',
        'DailySpend',
        'MonthToDateSpend'
    ])
    report_request.Columns=report_columns

    return report_request

def get_active_accounts(file_path):
    """
    Get all account IDs accessible with the current credentials
    """
    account_ids = {}
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                 # Parse lines like: "47013130 #AT"
                parts = line.split('#')
                if len(parts) >= 2:
                    account_id_str = parts[0].strip()
                    country_code = parts[1].strip()
                    
                    try:
                        account_id = int(account_id_str)
                        account_ids[account_id] = country_code
                    except ValueError:
                        print(f"Line {line_num}: Could not parse '{parts[0]}' as integer")
        
        print(f"\n Loaded {len(account_ids)} account IDs from {file_path}")
        return account_ids
        
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as ex:
        print(f"Error reading file: {ex}")
        return []

if __name__ == '__main__':
    import os
    from datetime import datetime
    
    print("Loading the web service client proxies...")
  
# MORE DETAIL ABOUT AUTH, TOKENS see 01_codewalkthrough.png
    authorization_data = AuthorizationData(
        account_id=None,
        customer_id=None,
        developer_token=DEVELOPER_TOKEN,
        authentication=None,
    )

    reporting_service_manager = ReportingServiceManager(
        authorization_data=authorization_data, 
        poll_interval_in_milliseconds=5000, 
        environment=ENVIRONMENT,
    )

    reporting_service = ServiceClient(
        service='ReportingService', 
        version=13,
        authorization_data=authorization_data, 
        environment=ENVIRONMENT,
    )

    # Authenticate first
    authenticate(authorization_data)
    
    # Define path to account IDs file
    ACCOUNT_IDS_FILE = r'A:path\to\directory\active_account_ids.txt'
    active_account_ids = get_active_accounts(ACCOUNT_IDS_FILE)
    if not active_account_ids:
        print("No account IDs to process. Exiting.")
        sys.exit(1)
    
    print(f"\nWill process {len(active_account_ids)} accounts")
        
    # Loop through each account and generate reports
    for idx, account_id in enumerate(active_account_ids, 1):
        country_code = active_account_ids[account_id]
        print(f"\n{'='*60}")
        print(f"Processing Account {idx}/{len(active_account_ids)}: ID {account_id}")
        print(f"{'='*60}")
        
        # Set the current account ID
        authorization_data.account_id = account_id
        
        # Create filename with account ID
        RESULT_FILE_NAME = f"{country_code}.{REPORT_FILE_FORMAT.lower()}"
        
        # Run main for this account
        try:
            report_request = get_report_request(account_id)
            
            reporting_download_parameters = ReportingDownloadParameters(
                report_request=report_request,
                result_file_directory=FILE_DIRECTORY, 
                result_file_name=RESULT_FILE_NAME, 
                overwrite_result_file=True
            )

            output_status_message(f"Downloading report for account {account_id}...")
            download_report(reporting_download_parameters)
            print(f"Successfully downloaded report for account {account_id}")
            
        except Exception as ex:
            print(f"Error processing account {account_id}: {ex}")
            continue
    
    print(f"\n{'='*60}")
    print(f"All {len(active_account_ids)} accounts processed!")
    print(f"Reports saved to: {FILE_DIRECTORY}")
