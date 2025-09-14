# from dotenv import load_dotenv
# import requests
# import xbrl_client 
# import os

# def main():
#     print("Current working directory:", os.getcwd())
#     load_dotenv(dotenv_path='./.env')

# # get xbrl api token
#     client_id = os.environ.get('CLIENT_ID')
#     client_secret = os.environ.get('CLIENT_SECRET')
#     username = os.environ.get('XBRL_USERNAME')
#     password = os.environ.get('XBRL_PASSWORD')

#     xbrlClient= xbrl_client.XBRLClient(client_id= client_id, client_secret= client_secret, 
#                             username= username, password= password, platform= 'python')

    
#     l_tickers = ['BA']
#     int_count_tickers = len(l_tickers) 
#     l_report_years = ['2024','2023']
#     int_num_years = len(l_report_years)
#     int_num_results = int_count_tickers * int_num_years
#     str_report_doc_type = '10-K'

#     fact_fields= [
#                 'report.entity-name',
#                 'entity.cik.sort(ASC)',
#                 'report.base-taxonomy',
#                 'report.filing-date',
#                 'report.period-end',
#                 'report.year-focus',
#                 'report.period-focus',
#                 'report.is-most-current',
#                 'report.period-index.sort(ASC)',
#                 'entity.ticker.sort(ASC)',
#                 'report.document-type',
#                 'report.id',
#                 'dts.id',
#                 'report.entry-url ',
#                 'report.is-most-current',
#                 'report.filing-date',
#                 f'report.limit({int_num_results})'
#                 ]

#     params = { 
#             'entity.ticker':','.join(l_tickers),
#             'report.document-type': str_report_doc_type,
#             'report.year-focus': ','.join(l_report_years),
#             #'report.period-index': ','.join(l_report_period_index),
#             #'report.is-most-current': 'false',
#             'fields': ','.join(fact_fields)
#             }

#     endpoint = 'report/search'

#     print('hello')
#     response= xbrlClient.query(endpoint=endpoint, params=params)

#     print(response)


# if __name__ == '__main__':
#     main()



#The main application logic

import os
from dotenv import load_dotenv
import pandas as pd
from xbrl_client import XBRLClient
from financial_classes import Company, Report, FinancialStatement

# 1. Load configuration and initialize client
load_dotenv()
XBRL_USERNAME = os.getenv("XBRL_USERNAME")
XBRL_PASSWORD = os.getenv("XBRL_PASSWORD")
if not XBRL_USERNAME or not XBRL_PASSWORD:
    raise ValueError("Username and/or password not found in environment variables.")

XBRL_CLIENT_ID = os.environ.get('CLIENT_ID')
XBRL_CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
if not XBRL_CLIENT_ID or not XBRL_CLIENT_SECRET: 
    raise ValueError("Client ID and/or Client Secret not found in environment variables")

xbrlClient = XBRLClient(client_id= XBRL_CLIENT_ID, client_secret= XBRL_CLIENT_SECRET, 
                             username= XBRL_USERNAME, password= XBRL_PASSWORD, platform= 'python')

# 2. Define your list of tickers and years
######l_tickers = ['BA']
l_report_years = ['2024'] # Example year

# 3. Create a Company object and load its reports
boeing = Company(ticker='BA')
boeing.load_10k_reports(xbrlClient, l_report_years)


# 4. Process the data for each report
for year, report in boeing.reports.items():
    print(f"\nProcessing income statement for {report.entity_name} ({year})...")
    # This single call now handles the entire workflow:
    # 1. Finding the network ID
    # 2. Loading concepts and relationships
    # 3. Loading facts
    # 4. Storing all of it in a FinancialStatement object
    report.load_income_statement_data(xbrlClient)

    # 5. Combine the data and print to a DataFrame, just like your final code block
    if 'Income Statement' in report.statements:
        statement = report.statements['Income Statement']
        if statement.concepts and statement.facts:
            df_combined = statement.combine_to_dataframe()
            print("\nCombined DataFrame:")
            print(df_combined.head())
            print("\nDataFrame Shape:", df_combined.shape)
            df_combined.to_csv('output/data.csv')
        else:
            print(f"Could not combine data for {year}. Missing concepts or facts.")
    else:
        print(f"No income statement data found for {year}.")