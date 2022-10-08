from re import L
from bs4 import BeautifulSoup
from selenium import webdriver
from bs4 import BeautifulSoup
import smtplib
import pandas as pd
from datetime import datetime, time, timedelta
from time import sleep, process_time
from config import FROM_ADDRESS, EMAIL_PASSWORD, TO_ADDRESSES, FREQUENCY

GOOGLE_CHROME_BIN = '/usr/bin/google-chrome'
CHROMEDRIVER_PATH = '/usr/bin/chromedriver'

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.binary_location = GOOGLE_CHROME_BIN
driver = webdriver.Chrome(
        executable_path=str(CHROMEDRIVER_PATH),
        chrome_options=chrome_options,
    )

driver.set_page_load_timeout(60)

def is_time_between(begin_time, end_time, check_time=None):
    check_time = check_time or datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:
        return check_time >= begin_time or check_time <= end_time

def sleepUntil(hour, minute):
    t = datetime.today()
    future = datetime(t.year, t.month, t.day, hour, minute)
    if t.timestamp() > future.timestamp():
        future += timedelta(days=1)
    if future.weekday() > 4:
            future += timedelta(days=7-future.weekday())
    sleep((future - t).seconds)

def scrape(url):
    try:
        driver.get(url)
        sleep(2)
        page = driver.page_source
        soup = BeautifulSoup(page, 'lxml')
        return soup
    except:
        print('Error: Could not scrape url: ' + url)

def check_announcements():
    df = pd.read_csv('stock_list.csv')
    body = ''
    for index, row in df.iterrows():
        if type(row[1]) == str: 
            soup = scrape(row[1])
            table = soup.find('div', attrs={'id':'news'})
            hasNew = False
            if table:
                links = table.find_all('a')
                try:
                    df = pd.read_csv('db/{}.csv'.format(row[1]))
                    for link in links:
                        if link.text and link.get('href') not in df['link'].values:
                            if not hasNew:
                                body += row[0] + ':\n'
                                hasNew = True
                            df_new_row = pd.DataFrame([[link.text, link.get('href')]], columns=['title', 'link'])
                            df = pd.concat([df, df_new_row])
                            body += link.text + ' - ' + "https://www.bseindia.com" + link.get('href') + '\n'
                            df.to_csv('db/{}.csv'.format(row[1]), index=False)
                except:
                    if links and len(links) > 0:
                        hasNew = True
                        body += row[0] + ':\n'
                        df = {
                            'title': [],
                            'link': []
                        }
                        for link in links:
                            if (link.text):
                                df['title'].append(link.text)
                                df['link'].append(link.get('href'))
                                body += link.text + ' - ' + "https://www.bseindia.com" + link.get('href') + '\n'
                        df = pd.DataFrame(df)
                        df.to_csv('db/{}.csv'.format(row[0]), index=False)
            if hasNew:
                body += '\n'
    if body:
        with open('report_num.txt', 'r') as f:
            num_text = f.read()
            num, date = num_text.split(',')
            num = int(num)
            if date != datetime.now().strftime('%d-%m-%Y'):
                num = 1
            with open('report_num.txt', 'w') as f:
                f.write(str(num+1) + ',' + datetime.now().strftime('%d-%m-%Y'))
            subject = 'Report {} - {}'.format(num, datetime.now().strftime('%d-%m-%Y'))
            send_mail(subject, body)

def send_mail(subject, body):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(FROM_ADDRESS, EMAIL_PASSWORD)
    msg = f'Subject: {subject}\n\n{body}'
    for address in TO_ADDRESSES:
        server.sendmail(FROM_ADDRESS, address, msg)
    print('Emails have been sent!')
    server.quit()

while True: 
    start_time = process_time()
    check_announcements()
    print('Execution time: {}\n'.format(process_time() - start_time))
    if is_time_between(time(9, 0), time(16, 0)):
        sleep(FREQUENCY)
    else:
        # sleep until 9:00 am and skip weekends
        sleepUntil(9, 0)