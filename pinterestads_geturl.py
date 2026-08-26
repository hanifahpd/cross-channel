'''
campaign and ad reporting from Pinterest Ads' site are sent to gmail
this script is used to get a download URL from gmail automatically
'''

import os
import base64
import time
import re
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import logging

# --- Setting & Custom Exceptions ---
BASE_DIR = r"A:path/to/directory"
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, 'credentials_gmail.json')
TOKEN_DIR = os.path.join(BASE_DIR, 'token_files')
DOWNLOAD_SAVE_LOCATION = r"A:path/to/directory"
url_path = os.path.join(BASE_DIR, 'url.txt')
log_path = os.path.join(BASE_DIR, 'url.log')

class GmailException(Exception):
    """Basic exception for error in gmail."""
    pass

class NoEmailFound(GmailException):
    """Pass/thrown when no email found."""
    pass

class ServiceCreationError(GmailException):
    """Pass when API service fail to be called."""
    pass

def setup_logging():
    """Mengatur logger untuk menyimpan ke file dan mencetak ke konsol."""
    # Get the main logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Atur level log minimum

    # Delete existing handler to avoid duplicating log
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create log format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Create Handler (save to file)
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # stream Handler 
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    
    return logger

def create_service(client_secret_file: str, api_name: str, api_version: str, *scopes: str) -> Optional[Resource]:
    """Create & authenticate Google API service."""
    token_file = f'token_{api_name}_{api_version}.json'
    token_path = os.path.join(TOKEN_DIR, token_file)

    if not os.path.exists(TOKEN_DIR):
        os.makedirs(TOKEN_DIR)

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception as e:
            logging.warning(f"Fail to load token, recreate... Error: {e}")
            os.remove(token_path)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.warning(f"Fail to refresh token, restrat... Error: {e}")
                if os.path.exists(token_path):
                    os.remove(token_path)
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                logging.critical(f"ERROR: Credentials not found {client_secret_file}")
                return None
            except Exception as flow_error:
                logging.error(f"Failed to run authentication's flow: {flow_error}")
                return None

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(api_name, api_version, credentials=creds, static_discovery=False)
        logging.info(f"{api_name} {api_version} service created successfully.")
        return service
    except Exception as e:
        logging.critical(f'Failed to create service instance for {api_name}: {e}')
        if os.path.exists(token_path):
            os.remove(token_path)
        raise ServiceCreationError(f"Service failed: {e}")


def search_emails(service: Resource, query_string: str, max_results: int = None) -> List[dict]:
    """Looking for emails match the queries"""
    try:
        message_list_response = service.users().messages().list(
            userId='me',
            q=query_string,
            maxResults=max_results
        ).execute()
        messages = message_list_response.get('messages', [])
        if not messages:
            logging.warning(f"No email found for the query: {query_string}")
            raise NoEmailFound(f"No email found for the query: {query_string}")
        return messages
    except HttpError as error:
        logging.warning(f"Failed to search: {error}")
        raise NoEmailFound(f"Failed to search: {error}")


def get_message_detail(service: Resource, message_id: str) -> dict:
    """Get complete details from one email"""
    try:
        return service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
    except HttpError as error:
        logging.error(f"Failed to fetch details in email {message_id}: {error}")
        return {}


def get_html_body(payload: dict) -> Optional[str]:
    """
    Recursively search for the ‘text/html’ 
    section of the email payload and decode the data
    """
    # 1. fundamental case: text/html part
    if payload.get('mimeType') == 'text/html':
        data = payload.get('body', {}).get('data')
        if data:
            return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
    
    # 2. recursive case: multiparts
    if 'parts' in payload:
        for part in payload['parts']:
            html_body = get_html_body(part)
            if html_body:
                return html_body # return to the first found html
    
    # 3. fundamental case: not found
    return None

def find_and_download_link(html_body: str, link_text: str) -> Optional[str]:
    """
    Searching for hyperlink with specific text in html and download the file.
    """
    try:
        soup = BeautifulSoup(html_body, 'html.parser')
        
        # search for  <a> (hyperlink) with the text intended to find
        # use lambda to match the text after strip & case-insensitive
        target_link = soup.find(
            'a', 
            href=True, 
            string=lambda t: t and t.strip().lower() == link_text.lower()
        )

        if not target_link:
            logging.warning(f"Link with text isn't found: '{link_text}'")
            return

        url = target_link['href']
        logging.info(f"URL found: {url}")
        with open("url.txt", "w") as file:
            file.write(url)
 
     
        # 2. Download detail of the url body in html/json format
        try:
            response = requests.get(url, allow_redirects=True, timeout=30)
            response.raise_for_status() 

            filename = url.split('/')[-1].split('?')[0] # try to get the name from file
            
            # If the URL doesn't have a file name (e.g., /download.php?id=123)
            # Try to retrieve it from the ‘content-disposition’ header
            if not filename or '.' not in filename:
                if 'content-disposition' in response.headers:
                    disp_header = response.headers['content-disposition']
                    fn = re.findall('filename="?(.+)"?', disp_header)
                    if fn:
                        filename = fn[0]
                if not filename or '.' not in filename: 
                     filename = "url_body_email.txt"

            clean_filename = filename.strip().replace('\r', '').replace('\n', '')
            
            if not os.path.exists(DOWNLOAD_SAVE_LOCATION):
                os.makedirs(DOWNLOAD_SAVE_LOCATION)
            
            save_path = os.path.join(DOWNLOAD_SAVE_LOCATION, clean_filename)

            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Download succeeded: {clean_filename} ke {DOWNLOAD_SAVE_LOCATION}")

        except requests.exceptions.RequestException as e:
            print(f"Failed to download the file {url}: {e}")
        
        return url
    except Exception as e:
        logging.error(f"Error while parsing html: {e}")
        return None
    

def main():
    logger = setup_logging()
    logger.info("--- Start running the script to find URL in email ---")
    
    API_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] 
    
    try: # create the service
        service = create_service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, *SCOPES)
        if not service:
            logger.critical("Service call has failed. Script stopped.")
            return

        sender = "pinbot@info.pinterest.com" # decide the query here
        LINK_TEXT_TO_FIND = 'Download "Cross channel 2026" report'
        
        query_string = f'from:{sender}'

        logger.info(f"Searching the newest email from {sender}...")
        email_messages = search_emails(service, query_string, max_results=1)
        
        if not email_messages:
            return

        latest_email_id = email_messages[0]['id']
        logger.info(f"The latest email found, ID: {latest_email_id}")

        message_detail = get_message_detail(service, latest_email_id)
        if not message_detail:
            logger.error("getting the detail of the email failed.")
            return

        # fetch HTML body from Email
        payload = message_detail.get('payload')
        if not payload:
            logger.warning("email has no contain of payload.")
            return

        html_body = get_html_body(payload)
        report_url = None
        
        if html_body:
            logger.info("Succeed to extract HTML body, find attachment...")
            report_url = find_and_download_link(html_body, LINK_TEXT_TO_FIND)
        else:
            logger.warning("Can't find the HTML body inside the email")

        if report_url:
            # Write & save URL into a txt file
            try:
                with open(url_path, "w", encoding="utf-8") as f:
                    f.write(report_url)
                logger.info(f"Great! URL has been saved to: {url_path}")
            except (IOError, PermissionError, OSError) as e:
                logger.critical(f"GAGAL MENULIS FILE URL! Path: {url_path}")
                logger.critical(f"Pastikan folder ada dan Anda memiliki izin tulis.")
                logger.critical(f"Error: {e}")
            except Exception as e:
                logger.error(f"Error tidak terduga saat menulis file: {e}")
        else:
            logger.warning("Fail to fetch URL from the email. No file created")
            
    except NoEmailFound as e:
        logger.warning(e)
    except ServiceCreationError as e:
        logger.critical(f"Execution is stopped due to service failure: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error is found in main: {e}")

    logger.info("--- The script to look up the link from Pinterest Ads has finished ---")

if __name__ == '__main__':
    main()
