import tweepy
import configparser
import pandas as pd
import csv
import re
import os.path
from os import path
import random
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pyautogui
import shutil

def authenticate(): #establishing access to Tom's Twitter account 
    # read config files
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config['twitter']['api_key']
    api_key_secret = config['twitter']['api_key_secret']
    access_token = config['twitter']['access_token']
    access_token_secret = config['twitter']['access_token_secret']
    # authentication
    auth = tweepy.OAuthHandler(api_key, api_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    return api

def read_tweet_data(filename): #stores data from the input spreadsheet (including username, date, and Tweet text) into input_file
    input_file = []
    try: 
        with open(filename, 'r', encoding = 'latin-1') as tweetdata: #encode as latin-1 for any special characters
            reader = csv.DictReader(tweetdata)
            for row in reader:
                input_file += [row]
        return input_file
    except FileNotFoundError: 
        print('File does not exist')

def get_all_info(data, api): #scrapes all the relevant info from real users' accounts on Twitter
    #creating lists to store a user's 200 most recent tweets, and other to contain their vetted biographic data 
    tweets_list = [] 
    compiled_data = [] 
    #scraping process
    for name_num in range(len(data)):
        # If the user exists, pull all data from Twitter for the specified user:
        try: 
            user_info = api.get_user(screen_name = data[name_num]['Username'])
            username = data[name_num]['Username']
            name = user_info.name
        # If the user doesn't exist (because we often use fake characters), substitute the user analytics with a notable user
        except: 
            username = 'denzelcurry' #arbitrary selection of notable user
            user_info = api.get_user(screen_name = username)
            name = data[name_num]['Username']
        # For all users, collect specific information from profile
        if user_info.verified == True:
            verified = 1
        else:
            verified = 0
        # For all users, collect information from scraped tweets
        tweet_data = api.user_timeline(screen_name = username, count = 200, include_rts = False)
        for tweet in tweet_data:
            tweet_dict = {
                'Time':"{:d}:{:02d}".format(tweet.created_at.hour, tweet.created_at.minute), 
                'Favorites':tweet.favorite_count,
                'Retweets':tweet.retweet_count}
            tweets_list.append(tweet_dict)
        df = pd.DataFrame(tweets_list)
        means = dict(df.mean(numeric_only=True).round(0).astype(int))
        # for retweets, favorites, and time, ensure there are no list index errors given twitter-side problems
        r = 0
        f = 0
        t = 0
        engagement = [r, f, t]
        for i in engagement:
            while i == 0:
                try: # to get random but realistic engagement numbers, find the average number of favorites of the 200 most recent tweet, 
                # pull a random tweet's number of favorites, and then take the mean of those two numbers. 
                    retweets = int((means['Retweets'] + tweets_list[random.randint(0, len(tweets_list))]['Retweets'])/2)
                    favorites = int((means['Favorites'] + tweets_list[random.randint(0, len(tweets_list))]['Favorites'])/2)
                    time = tweets_list[random.randint(0, len(tweets_list))]['Time']
                    i += 1
                except:
                    i = 0
        # if the user is fictional, switch back their username to our chosen fictional handle or to the condensed form of their name
        fict_names = ['Adam Chung', 'Marshall Witherspoon', "Molly O'Ryan", 'Andrea Hastings', 'Melina Conley', 'Manuel Escondido']
        fict_chars = {
            'Adam Chung':'achung',
            'Marshall Witherspoon':'MWitherspoon',
            "Molly O'Ryan":'redheadMolly',
            'Andrea Hastings':'BattleofHastings',
            'Melina Conley':'MelConley',
            'Manuel Escondido':'beisbol_escondido',
            'Ellsworth Wickman': 'EWickman'
            }
        if username == 'denzelcurry':
                if data[name_num]['Username'] in fict_names:
                        username = fict_chars[data[name_num]['Username']]
                else: 
                    try:
                        username = re.sub(" ","", data[name_num]['Username'])
                    except:
                        pass
        # if retweets end up being greater than favorites, swap the values to ensure realism
        if retweets > favorites:
            retweets, favorites = favorites, retweets
        if retweets == 0:
            retweets = 1
        # reset the tweets list for new user 
        tweets_list = []
        # compiling the data
        user_info = {
            "Name":name,
            "Username":username,
            "Verified":verified,
            "Time":time, 
            "Retweets":retweets, 
            "Favorites":favorites, 
            "Day": data[name_num]['Day'], 
            "Month": data[name_num]['Month'],
            "Year": data[name_num]['Year'],
            "Text": data[name_num]['Text']}
        compiled_data.append(user_info)
    return compiled_data

def clean(data): #copying text from Google Docs leaves strange characters in .csv files, like "curly apostrophes." 
    # This fixes those characters
    symbols = ["Ò", "Ó", "Õ", "É", "&", "Ñ", "Ê", "Ô"] #list of symbols
    sym_replace = {"Ò":'"', "Ó":'"', "Õ":"'", "É":"...", "&":'and', "Ñ":"—", "Ê":"", "Ô":"'"} # corresponding values
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                      "]+", re.UNICODE)
    #replace in the tweet text
    for name_num in range(len(data)):
        for i in symbols: 
            if i in data[name_num]['Text']:
                data[name_num]['Text'] = re.sub(i,sym_replace[i], data[name_num]['Text'])
        for i in symbols: 
            if i in data[name_num]['Name']:
                data[name_num]['Name'] = re.sub(i,sym_replace[i], data[name_num]['Name'])
        data[name_num]['Name'] = emoji_pattern.sub(r'', data[name_num]['Name']) # no emoji
        if data[name_num]['Name'] == '':
            data[name_num]['Name'] = data[name_num]['Username']
    return data

def char_count(data):
    # stops the program if there are more than 280 characters in any tweet
    for name_num in range(len(data)):
          if len(data[name_num]['Text']) > 280:
            print('The tweet text for ' + data[name_num]['Name'] + ' is too long. It is currently ' + str(len(data[name_num]['Text'])) + ' characters out of 280.')
            return False
            
def profpic_dl(filename): #downloading the profile pictures of users whose photo is not already in my "profpics" folder
    api = authenticate()
    data = process_data(filename)
    warmup()
    for name_num in range(len(data)):
        if  path.exists('/Users/tomplant/Desktop/profpics/' + data[name_num]['Username'] + '.jpeg') == False:
            try: # if the user is real
                profpic_generator(data, name_num, api)
            except: # if the user is fictional
                print('You need a profile photo for the fictional character '+data[name_num]['Name']+' with the username '+data[name_num]['Username'])
                
def profpic_generator(data, name_num, api): #navigating to the twitter link that allows you to download profile pictures
                user_info = api.get_user(screen_name = data[name_num]['Username'])
                url = re.sub("_normal","", user_info.profile_image_url_https) # change the url to get the bigger image by taking out "normal" from the web address
                driver = webdriver.Chrome(executable_path='/Users/tomplant/Desktop/Valens/Drivers/chromedriver')
                driver.get(url)
                driver.maximize_window()
                time.sleep(.25)
                pyautogui.moveTo(715,450) #coordinates specific to Tom's computer. Had trouble locating the object with selenium
                pyautogui.click(button='right')
                pyautogui.press('down')
                pyautogui.press('down')
                pyautogui.press('enter')
                time.sleep(1)
                #save profile photo as the user's name and move to the "profpics" folder on my machine
                pyautogui.write(data[name_num]['Username']) 
                time.sleep(.5)
                pyautogui.press('enter')
                time.sleep(1)
                shutil.move('/Users/tomplant/Downloads/' + data[name_num]['Username'] + '.jpeg', '/Users/tomplant/Desktop/profpics/' + data[name_num]['Username'] + '.jpeg')

def profpic_exists(data):
    # stops the program if any twitter user doesn't have a corresponding profile picture 
    for name_num in range(len(data)):
        if  path.exists('/Users/tomplant/Desktop/profpics/' + data[name_num]['Username'] + '.jpeg') == False:
            print('Profile picture does not exist for ' + data[name_num]['Username'])
            return False

def repeated(data): #identifying if there are multiple tweets from the same person in the dataset and naming the files differently
    counter = {}
    for name_num in range(len(data)):
        #we've seen it before 
        if data[name_num]['Name'] in counter:
            cur_value = counter.get(data[name_num]['Name'])
            cur_value += 1
            counter[data[name_num]['Name']] = cur_value
            data[name_num]['Repeated'] = counter[data[name_num]['Name']]
        else: #first time we've seen it
            counter[data[name_num]['Name']] = 1
    print(data)
    return data

def process_data(filename): #running the entire data collection process
    api = authenticate()
    print('Authenticated')
    data = read_tweet_data(filename)
    print('Reading and generating user data from Twitter...')
    print('This may take a few seconds...')
    compiled_data = get_all_info(data, api)
    clean_data = clean(compiled_data)
    final_data = repeated(clean_data)
    try:
        if char_count(final_data) != False:
            return final_data
    except:
        print('Fix the error above to proceed.')

def warmup(): 
# when copy/pasting with selenium for the first time, my computer is painfully slow and misses letters. This function gives my laptop a trial run
    driver = webdriver.Chrome(executable_path='/Users/tomplant/Desktop/Valens/Drivers/chromedriver')
    driver.get('https://www.tweetgen.com/create/tweet-classic.html')
    driver.maximize_window()
    item = driver.find_element('id', 'tweetTextInput')
    item.send_keys('warm up')
    item = driver.find_element('id', 'downloadButton')
    item.click()
    time.sleep(1.5)
    pyautogui.moveTo(950,630)
    pyautogui.click(button='right')
    pyautogui.press('down')
    pyautogui.press('down')
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.write('warm up')  
    pyautogui.press('enter')
    time.sleep(.5)

def generator(data, name_num): #interacting with the Tweet Generator website
    driver = webdriver.Chrome(executable_path='/Users/tomplant/Desktop/Valens/Drivers/chromedriver')
    driver.get('https://www.tweetgen.com/create/tweet-classic.html')
    driver.maximize_window()
    # Profile Picture
    pfp_file = '/Users/tomplant/Desktop/profpics/' + data[name_num]['Username'] + '.jpeg'
    item = driver.find_element('xpath', "//input[@type='file']")
    item.send_keys(pfp_file)
    # Name
    item = driver.find_element('id', 'nameInput')
    item.send_keys(data[name_num]['Name']) 
    # Twitter Username (Handle)
    item = driver.find_element('id', 'usernameInput')
    item.send_keys(data[name_num]['Username'])
    # Verified 
    if data[name_num]['Verified'] == 1:
        item = driver.find_element('id', 'verifiedInput')
        driver.execute_script("arguments[0].click();", item)
    # Tweet Text
    item = driver.find_element('id', 'tweetTextInput')
    item.send_keys(data[name_num]['Text'])
    # Time
    item = driver.find_element('id', 'timeInput')
    item.send_keys(data[name_num]['Time'])
    # Day
    item = driver.find_element('id', 'dayInput')
    item.send_keys(data[name_num]['Day'])
    #Month
    item = driver.find_element('id', 'monthInput')
    item.send_keys(data[name_num]['Month'])
    #Year 
    item = driver.find_element('id', 'yearInput')
    item.send_keys(data[name_num]['Year'])
    # Retweets
    item = driver.find_element('id', 'retweetInput')
    item.send_keys(data[name_num]['Retweets'])
    # Favorites
    item = driver.find_element('id', 'likeInput')
    item.send_keys(data[name_num]['Favorites'])
    # Generate Image # Once all data has been inserted
    item = driver.find_element('id', 'downloadButton')
    item.click()
    time.sleep(1.5)
    # Download image
    if len(data[name_num]['Text']) <= 60:
        pyautogui.moveTo(950,630)
    if 60 < len(data[name_num]['Text']) <= 105:
        pyautogui.moveTo(950,730)
    if 105 < len(data[name_num]['Text']) <= 200:
        pyautogui.moveTo(950,760)
    if len(data[name_num]['Text']) > 200:
        pyautogui.moveTo(950,775)
    pyautogui.click(button='right')
    pyautogui.press('down')
    pyautogui.press('down')
    pyautogui.press('enter')
    time.sleep(1)
    if 'Repeated' in data[name_num]:
        pyautogui.write(data[name_num]['Name'] + " " + str(data[name_num]['Repeated']))
        pyautogui.press('enter')
        time.sleep(1.5)
    else:
        pyautogui.write(data[name_num]['Name']) 
        pyautogui.press('enter')
        time.sleep(1.5)

def tweets_by_name(filename): # checks for profile pictures and tweet length before generating for a specific account
    data = process_data(filename)
    name = input("Enter the user's Twitter handle (case sensitive) ")
    if profpic_exists(data) != False and char_count(data) != False:
        warmup()
        for i in range(len(data)):
            if data[i]['Username'] == name:
                name_num = data.index(data[i]) 
        generator(data, name_num)

def profpics_by_name(filename): #allows generation of a tweet from a single person rather than the whole file
    api = authenticate()
    data = process_data(filename)
    name = input("Enter the user's Twitter handle (case sensitive) ")
    for i in range(len(data)):
        if data[i]['Username'] == name:
            name_num = data.index(data[i])
    warmup()
    profpic_generator(data, name_num, api)
        
def all_tweets(filename):
    # checks for profile pictures and tweet length before generating all
    data = process_data(filename)
    if profpic_exists(data) != False and char_count(data) != False:
        warmup()
        for i in range(len(data)):
            name_num = i
            generator(data, name_num)

if __name__ == '__main__':
    # offering options for generation
    selection = input('Would you like to (1) Generate All Tweets, (2) Download Profile Photos, (3) Generate Tweets by Name, or (4) Generate Profile Photos by Name? ')
    if selection == '1':
        all_tweets('new.csv')
    if selection == '2':
        profpic_dl('new.csv')
    if selection == '3':
        tweets_by_name('new.csv')
    if selection == '4':
        profpics_by_name('new.csv')