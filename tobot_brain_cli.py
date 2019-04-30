#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tobot_brain_cli.py - Airbnb Messaging Bot (TOBOT)
See README.md or https://github.com/shirosaidev/airbnbbot
for more information.

Copyright (C) Chris Park 2019
airbnbbot is released under the Apache 2.0 license. See
LICENSE for the full license text.
"""

import sqlite3
from airbnb_bot import read_corpus, db_connect, brain_dump, output_banner, train_bot, response, color
from config import confidence_req

output_banner()

def output_commands():
    print("""
    help|?           prints help
    quit|bye|exit    exit program
    braindump        dumps database
    brainsize        shows size of database
    trainbot         add new question and reply to database
    testbot          looks up response in database to question
    """)

# simple cli for Tobot's brain
print("Loading TOBOT's brain..")
sent_tokens, word_tokens = read_corpus()
connection, cursor = db_connect()
print("Done.")
print("TOBOT CLI; type ? or help for commands, quit or bye to exit.")
while True:
    try:
        user_response = input(color.DARKCYAN + 'TOBOT> ' + color.END).strip()
        if user_response in ['quit', 'bye', 'exit']:
            break
        elif user_response in ['?', 'help']:
            output_commands()
        elif user_response == 'braindump':
            brain_dump()
        elif user_response == 'brainsize':
            res = brain_dump(sizeonly=True)
            print(res)
        elif user_response == 'trainbot':
            res = train_bot(None, None)
            if res is not None:
                print(res)
        elif user_response == 'testbot':
            h = input("Question: ")
            h = h.lower()
            if h == '':
                continue
            res = response(h)
            if res is not None:
                resp, confidence, source = res
                print("TOBOT Reply: " + resp + " (confidence: %s (%s))" % (confidence, source))
                if confidence < confidence_req:
                    print("TOBOT: confidence too low to send reply, need more training")
            else:
                print("TOBOT Reply: no response found, need more training")
        else:
            print("Sorry, I don't understand, type help or ? to see all commands")
    except KeyboardInterrupt:
        break
print("Sayonara..")