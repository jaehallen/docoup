import os
os.system('apt update')
os.system('apt install chromium-chromedriver')
os.system('pip install selenium')

import requests
import subprocess
from time import sleep
import re

from getpass import getpass
from google.colab import output
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse, unquote

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

LOGIN_URL = 'https://ntehub.com/Account/Login'
PROJECT_INDEX = 'https://ntehub.com/Project/Index'

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome('chromedriver',options=options)

def ntehub_login(driver):
    wait = WebDriverWait(driver, 10)
    def nteInputs(username=True):
        inputStr = ''
        with output.use_tags('inputs'):
            if username:
                inputStr = input('Email/Username: ')
            else:
                inputStr = getpass('Password: ')

        output.clear(output_tags='inputs')
        return inputStr

    try:
        input_user = wait.until(EC.presence_of_element_located((By.ID,"Username")))
        input_user.send_keys(nteInputs())
        input_pass = wait.until(EC.presence_of_element_located((By.ID,"Password")))
        input_pass.send_keys(nteInputs(False))
        submit = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="frmLogin"]/div[3]/div[2]/div[2]/button')))
        submit.click()
    except:
        print("Failed to Login, Try Again")
    else:
        return driver

def get_link_info(src):
    print('Downloading ...', end='\n')
    try:
        r = requests.get(src)
    except:
        print('Failed to download')
        print(src)
        raise SystemExit(0)
    else:
        if r.headers.get('content-disposition'):
            basename = r.headers.get('content-disposition').split('filename=')[1]
        else:
            basename = os.path.basename(unquote(urlparse(src).path))

    return r, basename

def download_link(link, wd):
    label = ''
    media_src = ''
    if PROJECT_INDEX in link:
        for _ in range(3):
            try:
                wd.get(link)
            except:
                sleep(1)
                wd = get_driver()
            else:
                if link in wd.current_url:
                    break
                elif LOGIN_URL in wd.current_url:
                    print('Ntehub Login...')
                    wd = ntehub_login(wd)
                    output.clear()
        else:
            print('Failed to connect')
            wd.quit()
            raise SystemExit(0)

        soup = bs(wd.page_source, "html.parser")
        media_src = soup.find('source', {"id": "main_track_media"}).get('src')
        label = soup.find('span', {"id": "user_project_title_label"}).get_text().strip()
    else:
        media_src = link

    r, basename = get_link_info(media_src)
    base_ext = ''.join(basename.rpartition('.')[1:])
    base_file = basename if not label else label.replace('/','-')+base_ext


    with open(base_file, 'wb') as f:
        f.write(r.content)

    return base_file, wd

def download_link_by_gdown(link):
    re_id = re.search('file/d/([^"]+)/', link)
    id = re_id.group(1)
    o = subprocess.run(['gdown', '--id', id], check=True, stderr=subprocess.PIPE, encoding='UTF-8').stderr
    to = re.search('To:\s*([^"].*)', o)
    return to.group(1).strip()
