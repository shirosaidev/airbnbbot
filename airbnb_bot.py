#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""airbnb_bot.py - Airbnb Messaging Bot (TOBOT)
See README.md or https://github.com/shirosaidev/airbnbbot
for more information.

Copyright (C) Chris Park 2019
airbnbbot is released under the Apache 2.0 license. See
LICENSE for the full license text.
"""

from __future__ import print_function, unicode_literals
import requests
from bs4 import BeautifulSoup
import json
from textblob import TextBlob
import nltk
import random
import logging
import os
import sys
import time
#import re
import sqlite3
from sqlite3 import Error
from collections import Counter
from math import sqrt
import string
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import *

TOBOT_VERSION = '0.1-b.1'
__version__ = TOBOT_VERSION

# set up logging
#logging.basicConfig()
logger = logging.getLogger(name='TOBOT')
logger.setLevel(logging.DEBUG)
logging.addLevelName(
        logging.INFO, "\033[1;32m%s\033[1;0m"
                      % logging.getLevelName(logging.INFO))
logging.addLevelName(
    logging.WARNING, "\033[1;31m%s\033[1;0m"
                        % logging.getLevelName(logging.WARNING))
logging.addLevelName(
    logging.ERROR, "\033[1;41m%s\033[1;0m"
                    % logging.getLevelName(logging.ERROR))
logging.addLevelName(
    logging.DEBUG, "\033[1;33m%s\033[1;0m"
                    % logging.getLevelName(logging.DEBUG))
logformatter = '%(asctime)s [%(levelname)s][%(name)s] %(message)s'
loglevel = logging.DEBUG
logging.basicConfig(format=logformatter, level=loglevel)


# Tobot "brain" data functions

def read_corpus():
    """open corpus file and create word and sentence tokens
    corpus file is the base brain for Tobot which contains words/sentences
    used by nltk and sklearn to help Tobot respond to questions"""
    f = open('tobot_corpus.txt', 'r', errors='ignore')
    raw = f.read()
    f.close()
    raw = raw.lower()
    #nltk.download('punkt')
    #nltk.download('wordnet')
    #nltk.download('stopwords')
    sent_tokens = nltk.sent_tokenize(raw)
    word_tokens = nltk.word_tokenize(raw)

    return sent_tokens, word_tokens


def db_connect():
    """initialize the connection to the database and 
    create required tables."""
    try:
        connection = sqlite3.connect('tobot_db.sqlite')
    except Error as e:
        print("Error! cannot create the database connection. %s" % e)
        sys.exit(1)

    cursor = connection.cursor()

    # create the tables needed by TOBOT to store what it learns
    create_table_request_list = [
        'CREATE TABLE IF NOT EXISTS words(word TEXT UNIQUE)',
        'CREATE TABLE IF NOT EXISTS sentences(sentence TEXT UNIQUE, used INT NOT NULL DEFAULT 0)',
        'CREATE TABLE IF NOT EXISTS associations (word_id INT NOT NULL, sentence_id INT NOT NULL, weight REAL NOT NULL)',
    ]
    for create_table_request in create_table_request_list:
        try:
            cursor.execute(create_table_request)
        except Error as e:
            print(e)

    return connection, cursor


# end data functions

connection, cursor = db_connect()
sent_tokens, word_tokens = read_corpus()


class airbnbBot():
    def __init__(self, username=None, password=None, apikey='', oauthtoken=''):
        self.username = username
        self.password = password
        self.useragent = useragent
        self.session = requests.Session()
        self.cookies = None
        self.loggedin = False
        self.apikey = apikey
        self.oauthtoken = oauthtoken
        self.message_ids = []
        self.message_count = 0
        self.message_count_processed = 0
        self.reply_count_response = 0
        self.reply_count_noresponse = 0

        self.set_headers_default()


    def set_headers_default(self):
        if not self.useragent:
            self.useragent = 'Airbnb/17.50 iPad/11.2.1 Type/Tablet'
        self.session.headers = {
            'User-Agent': self.useragent, 
            'Accept-Encoding': 'gzip, deflate', 
            'Accept': '*/*', 
            'Connection': 'keep-alive'
            }

    def set_headers(self):
        self.session.headers.update({
                'cache-control': 'no-cache',
                'user-agent': self.useragent,
                'content-type': 'application/json',
                'accept': 'application/json',
                'accept-encoding': 'br, gzip, deflate',
                'accept-language': 'en-us',
                'x-airbnb-oauth-token': self.oauthtoken,
                'x-airbnb-api-key': self.apikey,
                'x-airbnb-locale': 'en',
                'x-airbnb-currency': 'USD'
                })

    def login(self):
        if not self.loggedin:
            src = self.session.get('https://www.airbnb.com/login').text
            soup = BeautifulSoup(src, features="html.parser")
            hidden_tags = soup.findAll("input", type="hidden")
            payload = {
                'email': self.username,
                'password': self.password
            }
            for tag in hidden_tags:
                payload[tag.attrs['name']] = tag.attrs['value']
            r = self.session.post('https://www.airbnb.com/authenticate', data=payload)
            if r.status_code in [200, 302]:
                self.cookies = self.session.cookies
                self.loggedin = True
                return 'login success'
            else:
                print(color.RED + 'login failed ' + str(r.status_code) + color.END)
                sys.exit(1)

    def oauth_token(self):
        payload = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password
        }
        self.session.headers.update({'Content-Type': 'application/x-www-form-urlencoded', 'x-airbnb-api-key': self.apikey})
        src = self.session.post('https://api.airbnb.com/v1/authorize', data=payload).text
        body = json.loads(src)
        try:
            if body['error_code']:
                return None
        except KeyError:
            pass
        try:
            token = body['access_token']
        except KeyError:
            token = None
        return token

    def api_key(self):
        self.login()
        src = self.session.get('https://www.airbnb.com/hosting/inbox').text
        soup = BeautifulSoup(src, features="html.parser")
        body = soup.find(id='_bootstrap-layout-init')
        body = json.loads(body['content'])
        key = body['api_config']['key']
        return key

    def get_message_threads(self, limit=50, offset=0, archived=False, unread=False):
        self.set_headers()
        qs = {
            '_limit': limit,
            '_offset': offset,
            'selected_inbox_type': 'host',
            '_format': 'for_messaging_sync',
            'include_support_messaging_threads': 'false'
            }
        if archived:
            qs['role'] = "hidden"
        if unread:
            qs['role'] = "unread"
        src = self.session.get('https://api.airbnb.com/v2/threads/', params=qs).text
        body = json.loads(src)
        try:
            if body['error_code']:
                return None
        except KeyError:
            pass
        try:
            messages = body['threads']
        except KeyError:
            messages = None
        return messages

    def get_message_thread(self, thread_id, limit=50, offset=0):
        self.set_headers()
        qs = {
            '_limit': limit,
            '_offset': offset,
            'selected_inbox_type': 'host',
            '_format': 'for_messaging_sync_with_posts'
            }
        src = self.session.get('https://api.airbnb.com/v2/threads/' + str(thread_id), params=qs).text
        body = json.loads(src)
        try:
            if body['error_code']:
                return None
        except KeyError:
            pass
        try:
            messages = body['thread']
        except KeyError:
            messages = None
        return messages

    def get_reservations(self, confirmation_code):
        self.set_headers()
        qs = {
            '_format': 'for_mobile_host'
            }
        src = self.session.get('https://api.airbnb.com/v2/reservations/' + str(confirmation_code), params=qs).text
        body = json.loads(src)
        try:
            if body['error_code']:
                return None
        except KeyError:
            pass
        try:
            reservation = body['reservation']
        except KeyError:
            reservation = None
        return reservation

    def send_message(self, thread_id, message):
        self.set_headers()
        payload = {
            'message': message,
            'thread_id': thread_id
        }
        src = self.session.post('https://api.airbnb.com/v2/messages', data=payload).text
        body = json.loads(src)
        try:
            if body['error_code']:
                return None
        except KeyError:
            pass
        try:
            result = body
        except KeyError:
            result = None
        return result

    def mark_message_read(self, thread_id):
        self.set_headers_default()
        self.login()
        r = self.session.get('https://www.airbnb.com/z/q/' + str(thread_id))
        if r.status_code == 200:
            return 'message marked read'
        else:
            return 'message not marked read'

    def send_reply(self, thread_id, message):
        if testing:
            return
        pass
        #send_message(thread_id, message)


class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


# language functions

# standard question start words
QUESTION_START_WORDS = (
    'who', 'what', 'when', 'where', 'why', 'how', 'is', 'can', 'does', 'do',
    'which', 'am', 'are', 'was', 'were', 'may', 'might', 'could', 'will', 'shall',
    'would', 'should', 'has', 'have', 'had', 'did',
)

def is_question(text):
    sentences = get_sentences(text)
    isquestion = False
    for sent in sentences:
        words = nltk.word_tokenize(sent)
        if words[-1] == '?' or words[0].lower() in QUESTION_START_WORDS:
            isquestion = True
            break
    return isquestion

# end language function


# text cleaning functions

def get_sentences(text):
    """Retrieve the sentences present in a given string of text.
    The return value is a list of sentences."""
    text = text.split('.')
    text = '. '.join(text).strip()
    sentList = nltk.sent_tokenize(text)
    return sentList

def get_words(text):
    """Retrieve the words present in a given string of text.
    Filter out the most common and stop words.
    The return value is a list of tuples where the first member is a lowercase word,
    and the second member the number of time it is present in the text."""
    wordsList = nltk.word_tokenize(text)
    # remove most common words
    fdist = nltk.probability.FreqDist(wordsList)
    most_common_words = fdist.most_common(2)
    for word, count in most_common_words:
        word = word.lower()
        if word in wordsList:
            wordsList.remove(word)
    # remove stop words
    stop_words = nltk.corpus.stopwords.words("english")
    filtered_wordsList = []
    for word in wordsList:
        word = word.lower()
        if word not in stop_words:
            filtered_wordsList.append(word)
    wordsList = filtered_wordsList[:]
    del filtered_wordsList[:]
    # perform lemmatization
    text = " ".join(wordsList)
    filtered_wordsList = lem_normalize(text)
    return Counter(filtered_wordsList).items()

def clean_words(text):
    """Simple text cleaner that removes all tokens that are not alphabetic
    Returns list of clean words."""
    text = text.split('.')
    text = '. '.join(text).strip()
    words = nltk.word_tokenize(text)
    words_clean = [word for word in words if word.isalpha()]
    return words_clean

def lem_tokens(tokens):
    lemmer = nltk.stem.WordNetLemmatizer()
    return [lemmer.lemmatize(token) for token in tokens]

def lem_normalize(text):
    remove_punct_dict = dict((ord(punct), None) for punct in string.punctuation)
    return lem_tokens(nltk.word_tokenize(text.lower().translate(remove_punct_dict)))

# end text cleaning


# database functions

def get_id(entityName, text):
    """Retrieve an entity's unique ID from the database, given its associated text.
    If the row is not already present, it is inserted.
    The entity can either be a sentence or a word."""
    tableName = entityName + 's'
    columnName = entityName
    cursor.execute('SELECT rowid FROM ' + tableName + ' WHERE ' + columnName + ' = ?', (text,))
    row = cursor.fetchone()
    if row:
        return row[0], True
    else:
        cursor.execute('INSERT INTO ' + tableName + ' (' + columnName + ') VALUES (?)', (text,))
        return cursor.lastrowid, False

def in_database(response):
    """Check if Tobot has the response stored in database."""
    cursor.execute('SELECT rowid FROM sentences WHERE sentence = ?', (response,))
    row = cursor.fetchone()
    if row:
        return True
    else:
        return False

def train_bot(H, B):
    """Train Tobot by adding human question and bot response into the database.
    Store the association between the user's message words and Tobot's response"""
    if H is None and B is None:  # cli
        H = input("Human question: ")
        H = H.strip()
        if H == '':
            return None
        B = input("Bot response: ")
        B = B.strip()
        if B == '':
            return None
    words = get_words(H)
    words_length = sum([n * len(word) for word, n in words])
    sentence_id, in_db = get_id('sentence', B)
    if in_db:
        return 'already in db'
    for word, n in words:
        word_id, in_db = get_id('word', word)
        weight = sqrt(n / float(words_length))
        cursor.execute('INSERT INTO associations VALUES (?, ?, ?)', (word_id, sentence_id, weight))
    connection.commit()
    return 'success'

def brain_dump(sizeonly=False):
    """Print what's in bot's brain (db)."""
    cursor.execute('SELECT * FROM sentences')
    rows_sent = cursor.fetchall()
    cursor.execute('SELECT * FROM words')
    rows_words = cursor.fetchall()
    cursor.execute('SELECT * FROM associations')
    rows_assoc = cursor.fetchall()
    if sizeonly:
        return 'TOBOT: BRAIN(db) (sentences: %s, words: %s)' % (len(rows_sent), len(rows_words))
    else:
        if not rows_sent:
            print("sentences empty")
        else:
            print("sentences: ")
            for row in rows_sent:
                print(row)
        if not rows_words:
            print("words empty")
        else:
            print("words: ")
            for row in rows_words:
                print(row)
        if not rows_assoc:
            print("associations empty")
        else:
            print("associations: ")
            for row in rows_assoc:
                print(row)

def db_lookup(H):
    """Check if there are any matching words in the database.
    Returns None if there is no match else a tuple with 
    response text and confidence percent."""
    words = get_words(H)
    wordsfound = None
    for word, n in words:
        cursor.execute('SELECT word FROM words WHERE word=?', (word,))
        row = cursor.fetchone()
        if row:
            wordsfound = True
            break
    if wordsfound is None:
        return None
    # retrieve the most likely answer from the database
    cursor.execute('CREATE TEMPORARY TABLE results(sentence_id INT, sentence TEXT, weight REAL)')
    words_length = sum([n * len(word) for word, n in words])
    for word, n in words:
        weight = sqrt(n / float(words_length))
        #cursor.execute('INSERT INTO results SELECT associations.sentence_id, sentences.sentence, ?*associations.weight/(4+sentences.used) FROM words INNER JOIN associations ON associations.word_id=words.rowid INNER JOIN sentences ON sentences.rowid=associations.sentence_id WHERE words.word=?', (weight, word,))
        cursor.execute('INSERT INTO results SELECT associations.sentence_id, sentences.sentence, ?*associations.weight FROM words INNER JOIN associations ON associations.word_id=words.rowid INNER JOIN sentences ON sentences.rowid=associations.sentence_id WHERE words.word=?', (weight, word,))
    # if matches were found, give the best one
    cursor.execute('SELECT sentence_id, sentence, SUM(weight) AS sum_weight FROM results GROUP BY sentence_id ORDER BY sum_weight DESC LIMIT 1')
    row = cursor.fetchone()
    cursor.execute('DROP TABLE results')
    # otherwise, just randomly pick one of the least used sentences
    #if row is None:
    #    cursor.execute('SELECT rowid, sentence FROM sentences WHERE used = (SELECT MIN(used) FROM sentences) ORDER BY RANDOM() LIMIT 1')
    #    row = cursor.fetchone()
    # tell the database the sentence has been used once more, and prepare the sentence
    # otherwise, just return None
    if row is None:
        return None
    B = row[1]
    weight = row[2]
    confidence = weight * db_weight_mult
    #cursor.execute('UPDATE sentences SET used=used+1 WHERE rowid=?', (row[0],))
    #connection.commit()
    # return bot's message
    return B, confidence

# end database functions


# message reply functions

def format_response(response):
    response_formatted = []
    lines = response.split('\n')
    if len(lines) > 1:
        lines.pop(0)
    for line in lines:
        response_formatted.append(line)
    return " ".join(response_formatted)

def response(user_response):
    """Try to get best response to question using corpus file and database.
    Returns None if confidence is 0 else returns a tuple with 
    response text, confidence percent and which source (file/db)."""
    res_file = file_lookup(user_response)
    res_db = db_lookup(user_response)
    if res_file is not None and res_db is not None:
        resp_file, confidence_file = res_file
        resp_db, confidence_db = res_db
        # pick best using confidence percent
        if confidence_file > confidence_db:
            return format_response(resp_file), confidence_file, 'file'
        else:
            return format_response(resp_db), confidence_db, 'db'
    elif res_file is not None and res_db is None:
        resp, confidence = res_file
        return format_response(resp), confidence, 'file'
    elif res_file is None and res_db is not None:
        resp, confidence = res_db
        return format_response(resp), confidence, 'db'
    else:
        return None

def file_lookup(user_response):
    """Try to get response to question using nltk and sklearn from text in corpus file.
    Returns None if confidence is 0 else returns a tuple with 
    response text and confidence percent."""
    tobo_response=''
    sent_tokens.append(user_response)
    TfidfVec = TfidfVectorizer(tokenizer=lem_normalize, stop_words='english')
    tfidf = TfidfVec.fit_transform(sent_tokens)
    vals = cosine_similarity(tfidf[-1], tfidf)
    idx=vals.argsort()[0][-2]
    flat = vals.flatten()
    flat.sort()
    req_tfidf = flat[-2]  # confidence percent
    sent_tokens.remove(user_response)
    if req_tfidf == 0:
        return None
    else:
        tobo_response = tobo_response+sent_tokens[idx]
        return tobo_response, req_tfidf

# standard greetings and responses
GREETING_INPUTS = ("hello", "hi", "greetings", "sup", "what's up", "hey",)
GREETING_RESPONSES = ["Hi", "Hey", "Hi there", "Hello"]

def greeting(text):
    words = clean_words(text)
    word_count = len(words)
    if word_count > 0 and word_count < 3:
        if words[0].lower() in GREETING_INPUTS:
            return random.choice(GREETING_RESPONSES) + " %s, do you have any questions?"

THANKS_INPUTS = ("thanks", "thank", "appreciated", "thankyou",)
THANKS_RESPONSES = ["No problem", "Happy to help"]

def thanks(text):
    words = clean_words(text)
    word_count = len(words)
    if word_count > 0 and word_count < 5:
        for word in words:
            if word.lower() in THANKS_INPUTS:
                return random.choice(THANKS_RESPONSES) + " %s, you are welcome."

# end message reply functions

def teach_tobot_user_prompt(message, resp, host_reply):
    # train tobot by adding into database if not already
    #if not in_database(resp) or not in_database(host_reply):
    user_response = input(color.BOLD + 'Teach TOBOT? (y/n) ' + color.END).strip()
    user_response = user_response.lower()

    def teach(m, r):
        r = train_bot(m, r)
        if r is not None:
            logger.info(color.BOLD + r + color.END)
    
    if user_response == 'y':
        if host_reply is not None and resp is not None:
            user_response = input(color.BOLD + 'Host reply (h) or found response (f)? (h/f) ' + color.END).strip()
            if user_response == 'h':
                teach(message, host_reply)
            elif user_response == 'f':
                teach(message, resp)
        elif host_reply is not None and resp is None:
            teach(message, host_reply)
        elif host_reply is None and resp is not None:
            teach(message, resp)


def process_message(msg, new_booking):
    host_replied = False
    message_oneline = msg['message'].replace('\n', ' ')
    logger.info(color.BOLD + color.CYAN + msg['guest_name'] + " wrote " + message_oneline + color.END + color.END)
    if msg['host_reply'] is not None:
        host_replied = True
        host_reply_oneline = msg['host_reply'].replace('\n', ' ')
        logger.info(color.BOLD + color.DARKCYAN + "host replied " + host_reply_oneline + color.END + color.END)
    # check if this is the first message from guest (new accepted booking)
    # and send them new booking reply
    if not training and send_new_booking_msg and new_booking and msg['status'] == 'accepted':
        logger.info(color.BOLD + color.YELLOW + "New accepted booking, first message from guest." + color.END + color.END)
        reply = new_booking_reply % msg['guest_name']
        logger.info(color.BOLD + color.DARKCYAN + "Sending reply " + reply + color.END + color.END)
        bot.send_reply(reply, msg['thread_id'])
        bot.reply_count_response += 1
        return
    # send standard greeting reply and check if the guest
    # is sending a very short message like "hello"
    elif greeting(msg['message']) is not None:
        reply = greeting(msg['message']) % msg['guest_name']
        logger.info(color.BOLD + color.DARKCYAN + "Sending reply " + reply + color.END + color.END)
        bot.send_reply(reply, msg['thread_id'])
        bot.reply_count_response += 1
        return
    # send standard polite response message when the guest
    # is just sending a "thanks"
    elif thanks(msg['message']) is not None and not is_question(msg['message']):
        reply = thanks(msg['message']) % msg['guest_name']
        logger.info(color.BOLD + color.DARKCYAN + "Sending reply " + reply + color.END + color.END)
        bot.send_reply(reply, msg['thread_id'])
        bot.reply_count_response += 1
        return
    # check if the message is not in a language we understand
    elif msg['translate']:
        b = TextBlob(msg['message'])
        lang = b.detect_language()
        if lang not in allowed_languages:
            logger.info(color.BOLD + color.YELLOW + "Message needs translation but is in a language I don't understand (" + lang + ")." + color.END + color.END)
            reply = send_in_eng_msg % msg['guest_name']
            logger.info(color.BOLD + color.DARKCYAN + "Sending reply " + reply + color.END + color.END)
            bot.send_reply(reply, msg['thread_id'])
            bot.reply_count_response += 1
            return
        else:
            logger.info(color.BOLD + color.YELLOW + "Message needs translation but is in allowed language list (" + lang + ")" + color.END + color.END)
            if lang != 'en':
                logger.info(color.BOLD + color.YELLOW + "Message not in English (en), skipping.." + color.END + color.END)
                return
    # check if this is a question or statement
    if not is_question(msg['message']):
        logger.info(color.BOLD + color.YELLOW + "The message doesn't seem to be a question, skipping.." + color.END + color.END)
        return
    # try to send an appropriate reply to the guest
    res = response(msg['message'])
    if res is None:
        logger.info(color.BOLD + color.YELLOW + "Sorry I don't know how to answer, please train me more." + color.END + color.END)
        # TOBOT doesn't know how to answer, so send a generic message
        #reply = "Hello %s, I'll get back to you shortly." % msg['guest_name']
        #logger.info("Sending reply " + reply)
        #bot.send_reply(reply, msg['thread_id'])
        bot.reply_count_noresponse += 1
        if training and host_replied:
            teach_tobot_user_prompt(msg['message'], None, msg['host_reply'])
        # TOBOT could not find a response so continue
        return
    resp, confidence, source = res
    # TOBOT found a response
    logger.info(color.BOLD + 'I found a response! (confidence: ' + str(confidence) + ' (' + source + '))' + color.END)
    if confidence < confidence_req:
        # confidence of response too low so continue
        reply = "Hello %s, regarding %s" % (msg['guest_name'], resp)
        logger.info(color.BOLD + color.DARKCYAN + "Reply " + reply + color.END + color.END)
        logger.info(color.BOLD + color.YELLOW + 'Sorry my confidence is too low to send reply. Please train me more.' + color.END + color.END)
        bot.reply_count_noresponse += 1
        if training and host_replied:
            teach_tobot_user_prompt(msg['message'], resp, msg['host_reply'])
        elif training:
            teach_tobot_user_prompt(msg['message'], resp, None)
        return
    # format reply and send
    reply = "Hello %s, %s" % (msg['guest_name'], resp)
    logger.info(color.BOLD + color.DARKCYAN + "Sending reply " + reply + color.END + color.END)
    bot.send_reply(reply, msg['thread_id'])
    bot.reply_count_response += 1
    # mark message as read
    if not testing and markread:
        logger.info('Marking message %s as read' % message['id'])
        res = bot.mark_message_read(message['id'])
        logger.info(res)
        bot.message_count_processed += 1


def output_banner():
    c = random.choice((color.PURPLE, color.CYAN, color.YELLOW, color.RED))
    banner = """%s

     .===./`
    /.n n.\\      __________  ____  ____  ______     
    "\\_=_/"     /_  __/ __ \/ __ )/ __ \/_  __/    
  (m9\\:::/\\      / / / / / / __  / / / / / / 
     /___\\6     / / / /_/ / /_/ / /_/ / / /  
     [] []     /_/  \____/_____/\____/ /_/ v%s  
    /:] [:\\        Airbnb Messaging Bot

    %s""" % (c, TOBOT_VERSION, color.END)
    print(banner)


if __name__ == '__main__':
    output_banner()

    logger.info('Starting up.. (training: %s, testing: %s)' % (training, testing))

    # check env vars
    try:
        USERNAME = os.environ['TOBOT_USERNAME']
    except KeyError:
        USERNAME = airbnb_username
    if USERNAME is None or USERNAME == '':
        logger.info('No TOBOT_USERNAME in env or config, exiting..')
        sys.exit(0)
    try:
        PASSWORD = os.environ['TOBOT_PASSWORD']
    except KeyError:
        PASSWORD = airbnb_password
    if PASSWORD is None or PASSWORD == '':
        logger.info('No TOBOT_PASSWORD in env or config, exiting..')
        sys.exit(0)
    try:
        APIKEY = os.environ['TOBOT_APIKEY']
    except KeyError:
        APIKEY = airbnb_apikey
    if APIKEY == '':
        APIKEY = None
    try:
        OAUTHTOKEN = os.environ['TOBOT_OAUTHTOKEN']
    except KeyError:
        OAUTHTOKEN = airbnb_oauthtoken
    if OAUTHTOKEN == '':
        OAUTHTOKEN = None

    if APIKEY is None:
        logger.info('No TOBOT_APIKEY in env, do you want me to get it?')
        user_response = input('(y/n) ').strip()
        user_response = user_response.lower()
        if user_response == 'y':
            bot = airbnbBot(
            username=USERNAME,
            password=PASSWORD
            )
            APIKEY = bot.api_key()
            os.environ['TOBOT_APIKEY'] = APIKEY
        else:
            logger.info('No TOBOT_APIKEY in env or config, exiting..')
            sys.exit(0)

    if OAUTHTOKEN is None:
        logger.info('No TOBOT_OAUTHTOKEN in env, do you want me to get it?')
        user_response = input('(y/n) ').strip()
        user_response = user_response.lower()
        if user_response == 'y':
            print(color.BOLD + color.YELLOW + "WARNING: DON'T GET OAUTHTOKEN TOO OFTEN!" + color.END + color.END)
            bot = airbnbBot(
            username=USERNAME,
            password=PASSWORD,
            apikey=APIKEY
            )
            OAUTHTOKEN = bot.oauth_token()
            os.environ['TOBOT_OAUTHTOKEN'] = OAUTHTOKEN
        else:
            logger.info('No TOBOT_OAUTHTOKEN in env or config, exiting..')
            sys.exit(0)

    logger.info('APIKEY: ' + APIKEY)
    logger.info('OAUTHTOKEN: ' + OAUTHTOKEN)

    bot = airbnbBot(
        username=USERNAME,
        password=PASSWORD,
        apikey=APIKEY,
        oauthtoken=OAUTHTOKEN
        )

    # output size of bot's brain
    print(color.BOLD + color.PURPLE + 'TOBOT: BRAIN(file) (sentences: ' + str(len(sent_tokens)) + ', words: ' + str(len(word_tokens)) + ')' + color.END + color.END)
    print(color.BOLD + color.PURPLE + brain_dump(sizeonly=True) + color.END + color.END)
    
    print(color.BOLD + color.DARKCYAN + "TOBOT: My name is Tobot. I will answer your guest's questions and help send messages for you. If you want to exit press ctrl+c.." + color.END + color.END)
    while True:
        try:
            logger.info(color.BOLD + 'Checking for messages in hosting inbox..' + color.END)
            # get message threads in hosting inbox
            messages = bot.get_message_threads()
            if messages is None:
                logger.info(color.BOLD + color.RED + 'Error getting messages' + color.END + color.END)
                break
            # check which message are unread and remove any support messages
            messages_unread = []
            messages_read = []
            for message in messages:
                if message['unread'] == True and message['thread_sub_type'] != 'support_messaging_thread':
                    messages_unread.append(message)
                elif message['unread'] == False:
                    messages_read.append(message)
            if training:
                # combine all messages if in training mode
                messages_unread += messages_read
            message_count = len(messages_unread)
            logger.info(color.BOLD + 'I found ' + str(message_count) + ' unread messages' + color.END)
            if message_count > 0:
                logger.info(color.BOLD + 'I will process any new messages and try to send reply..' + color.END)
            for message in messages_unread:
                #print(message)
                # parse message
                try:
                    msg = {
                        'thread_id': message['id'],
                        'checkin_date': message['inquiry_checkin_date'],
                        'checkout_date': message['inquiry_checkout_date'],
                        'listing_name': message['inquiry_listing']['name'],
                        'posts_count': message['posts_count'],
                        'requires_response': message['requires_response'],
                        'responded': message['responded'],
                        'status': message['status'],  # accepted, pending, cancelled
                        'guest_name': message['other_user']['first_name'],
                        'guest_id': message['other_user']['id'],
                        'translate': message['should_translate']
                    }
                except TypeError:
                    print(message)
                    raise
                try:
                    msg['num_guests'] = message['inquiry_number_of_guests']
                except KeyError:
                    msg['num_guests'] = message['inquiry_listing']['inquiry_number_of_guests']
                # end parse message
                # check if message has already been processed
                if msg['thread_id'] in bot.message_ids:
                    continue
                logger.debug(msg)
                # check if this is a new pending booking request or cancelled booking and 
                # skip message since we want to review
                if msg['status'] == 'pending' or msg['status'] == 'cancelled':
                    logger.info(color.BOLD + color.YELLOW + "This is a " + msg['status'] + " booking request, skipping.." + color.END + color.END)
                    bot.message_count += 1
                    bot.message_ids.append(msg['thread_id'])
                    continue
                # check if this is the guest's check out day and send check out message
                date_today = datetime.strftime(datetime.now(), '%Y-%m-%d')
                if not training and send_checkout_msg and msg['checkout_date'] == date_today and datetime.now().hour >= 11:
                    logger.info(color.BOLD + color.YELLOW + "Guest checks out today, sending checkout message" + color.END + color.END)
                    reply = checkout_message % msg['guest_name']
                    logger.info(color.BOLD + color.DARKCYAN + "Sending reply " + reply + color.END + color.END)
                    bot.send_reply(reply, msg['thread_id'])
                    bot.message_count += 1
                    bot.message_ids.append(message['id'])
                    continue
                bot.message_count += 1
                bot.message_ids.append(msg['thread_id'])
                # get message thread for guest
                mt = bot.get_message_thread(msg['thread_id'])
                if mt is None:
                    logger.info(color.BOLD + color.RED + 'Error getting message thread' + color.END + color.END)
                    continue
                posts_count = len(mt['posts'])
                # build a conversation list which cotains lists with any guest questions
                # and corresponding host responses
                new_booking = False
                guest_post_count = 0
                host_post_count = 0
                conversations = []
                pg = []
                ph = []
                n = posts_count - 1
                while n >= 0:
                    last_post = mt['posts'][n]
                    if last_post['user_id'] == msg['guest_id'] and last_post['message'] != '':
                        pg.append(last_post['message'])
                        guest_post_count += 1
                    elif last_post['user_id'] != msg['guest_id'] and last_post['message'] != '':
                        ph.append(last_post['message'])
                        host_post_count += 1
                    if (len(pg) > 0 and len(ph) > 0) or n==0:
                        conversations.append([pg[:], ph[:]])
                        del pg[:]
                        del ph[:]
                    n -= 1
                if guest_post_count == 0:
                    continue
                if host_post_count == 0:
                    new_booking = True
                if not training:
                    #print(conversations)
                    guest_post = ' '.join(conversations[-1][0])
                    msg['message'] = guest_post.lower()
                    if len(conversations[-1][1]) > 0:
                        host_reply = ' '.join(conversations[-1][1])
                        msg['host_reply'] = host_reply.lower()
                    else:
                        msg['host_reply'] = None
                    if msg['message']:
                        process_message(msg, new_booking)
                else:
                    # remove beginning conversation with guest greeting and host check in instructions
                    conversations.pop(0)
                    if len(conversations) == 0:
                        continue
                    # remove ending conversation if checkout day has passed
                    checkout_date = msg['checkout_date'].split('-')
                    checkout_date = datetime(int(checkout_date[0]), int(checkout_date[1]), int(checkout_date[2]))
                    if datetime.now() >= checkout_date:
                        conversations.pop()
                    if len(conversations) == 0:
                        continue
                    #print(conversations)
                    # loop through all the conversations to train Tobot from past discussions
                    # with guest and host reply
                    for conv in conversations:
                        guest_post = ' '.join(conv[0])
                        msg['message'] = guest_post.lower()
                        host_reply = ' '.join(conv[1])
                        msg['host_reply'] = host_reply.lower()
                        if msg['message']:
                            process_message(msg, new_booking)
            logger.info(color.BOLD + 'Sleeping for 2 min..' + color.END)
            time.sleep(120)
            continue
        except KeyboardInterrupt:
            break
    print(color.BOLD + "TOBOT: Sayonara! take care.." + color.END)