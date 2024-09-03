import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Function to generate date strings for today, yesterday, and the day before yesterday
def generate_date_strings():
    date_strings = []
    for i in range(3):  # Check for the last 3 days
        date = datetime.now() - timedelta(days=i)
        day = date.strftime('%d')  # Get the day as a string
        if day.startswith('0'):  # Check if it starts with a zero
            day = day[1:]  # Remove the leading zero
        date_strings.append(f'{day} {date.strftime("%B %Y")}')
    return date_strings

# Function to scrape the webpage and extract the latest ODS file URL
def get_latest_visa_decision_url():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get("https://www.ireland.ie/en/india/newdelhi/services/visas/processing-times-and-decisions/#Decisions", headers=headers)  # Replace with actual page URL
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            date_strings = generate_date_strings()
            for date_str in date_strings:
                print(date_str)
                link_text = f'Visa decisions made from 1 January 2024 to {date_str}'
                latest_link = soup.find('a', href=True, text=link_text)
                
                if latest_link:
                    file_url = latest_link['href']
                    logging.info(f"Found latest visa decision file URL: {file_url} for date {date_str}")
                    return "https://www.ireland.ie" + file_url
            
            logging.error("Could not find the visa decision link for the last 3 days.")
            return None
        else:
            logging.error(f"Failed to access the webpage. Status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"An error occurred while scraping the page: {e}")
        return None

# Function to download and check the visa status
def check_visa_status():
    url = get_latest_visa_decision_url()
    if url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                # Save the file locally
                with open('Visa_Decision.ods', 'wb') as file:
                    file.write(response.content)
                logging.info("File downloaded successfully.")
                
                # Read the ODS file using pandas
                df = pd.read_excel('Visa_Decision.ods', engine='odf', skiprows=6)
                
                # Clean the DataFrame to extract relevant columns
                df_cleaned = df.iloc[4:, [2, 3]].dropna().reset_index(drop=True)
                df_cleaned.columns = ['Application Number', 'Decision']
                
                # Check the status of the application number
                #application_number = 69321552  # Replace with your actual application number
                application_number = 69587592 #testingS
                application_status = df_cleaned[df_cleaned['Application Number'] == application_number]
                logging.info(f"Available Application Numbers: {df_cleaned['Application Number'].unique()[:10]}")  # Log the first 10 unique application numbers
                logging.info(f"{application_status}")
                
                if application_status.empty:
                    message = f"Application Number {application_number}: Not Found"
                else:
                    decision = application_status.iloc[0]['Decision']
                    message = f"Application Number {application_number}: {decision}"
                
                # Send WhatsApp message
                send_whatsapp_message(message)
                
            else:
                logging.error(f"Failed to download the file. Status code: {response.status_code}")
                send_whatsapp_message("Failed to download the Visa Decision file.")
                
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            send_whatsapp_message(f"An error occurred: {e}")
    else:
        send_whatsapp_message("Could not find the latest Visa Decision file URL.")

# Dummy function for WhatsApp messaging (replace with your actual API integration)
def send_whatsapp_message(message):
    url = "https://panel.rapiwha.com/send_message.php"
    querystring = {"apikey":"7DSIVLYJC9QVCVH06SVQ","number":"917798121777","text": { datetime.date , message}}
    response = requests.request("GET", url, params=querystring)
    logging.info(f"Respones from RAPIWHA API : {response}")
    logging.info(f"WhatsApp message sent: {message}")

# Initialize scheduler
scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
scheduler.add_job(func=check_visa_status, trigger='cron', hour=12, minute=00)
scheduler.start()

@app.route('/')
def index():
    return "Visa Status Checker is running."

if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    app.run(host='0.0.0.0', port=5000)
