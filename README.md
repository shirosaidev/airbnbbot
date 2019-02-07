```
     .===./`
    /.n n.\      __________  ____  ____  ______     
    "\_=_/"     /_  __/ __ \/ __ )/ __ \/_  __/    
  (m9\:::/\      / / / / / / __  / / / / / / 
     /___\6     / / / /_/ / /_/ / /_/ / / /  
     [] []     /_/  \____/_____/\____/ /_/   
    /:] [:\        Airbnb Messaging Bot
```

# Airbnb Messaging Bot (TOBOT)
Hi, I'm TOBOT.
I'll respond to all your guest requests, so you don't have to.
I'm an intelligent property manager for Airbnb Hosts.
I make you more productive by managing your short term rentals.
My goal is to get you more guests and make you more money.
Download my beta software (coming soon), I'm ready to help.

<img src="https://github.com/shirosaidev/airbnbbot/blob/master/docs/tobot_terminal.png?raw=true" alt="TOBOT terminal" />

## Requirements
- Python 3. (tested with Python 3.6.5)
- nltk python module
- requests python module
- beautifulsoup4 python module
- textblob python module
- sklearn python module

### Download

```shell
$ git clone https://github.com/airbnbbot/airbnbbot.git
$ cd airbnbbot
```
[Download latest version](https://github.com/shirosaidev/airbnbbot/releases/latest)

## How to use

Install python requirements using pip

`$ pip install -r requirements.txt`

Copy config.py.sample to config.py and edit.

Set environment variables for Airbnb login username and password.

```sh
$ export TOBOT_LOGIN=<airbnb_login_username>
$ export TOBOT_PASSWORD=<airbnb_login_password>
```

Set environment variables for Airbnb api key and oauth token. (if you don't know these, don't set now and TOBOT will ask you if you want to look them up)

```sh
$ export TOBOT_APIKEY=<airbnb_apikey>
$ export TOBOT_OAUTHTOKEN=<airbnb_oauthtoken>
```

Start up TOBOT:

```sh
$ python airbnb_bot.py
```
