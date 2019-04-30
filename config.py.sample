# Airbnb login username, can be set here or as env var TOBOT_USERNAME
airbnb_username = ""
# Airbnb login password, can be set here or as env var TOBOT_PASSWORD
airbnb_password = ""
# Airbnb api key, can be set here or as env var TOBOT_APIKEY
airbnb_apikey = ""
# Airbnb OAUTH token, can be set here or as env var TOBOT_OAUTHTOKEN
airbnb_oauthtoken = ""
# training mode; gets last 50 messages (including read) and prompts user to teach Tobot from 
# past converations from guest and host replies
training = True
# testing mode; don't send replies, just ouput what would be done
testing = True
# confidence level required for Tobot to auto-reply and send messages
confidence_req = 0.21
# database weight multiplier (confidence %)
db_weight_mult = 1.3
# default browser user-agent for logging in to Airbnb; this should be set to the browser agent you use to login to Airbnb
# example Airbnb/17.50 iPad/11.2.1 Type/Tablet
useragent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
# mark messages as read
markread = False
# languages that Tobot does not send a reply asking to send messages in English
# only English (en) is processed, any other language is this list is skipped (no reply)
# example if you are co-hosting and one of your co-host understands Japanese (ja), you could add to this
# list and Tobot won't reply asking to send in English if you have a Japanese guest writing in ja
allowed_languages = ['en', 'ja']
# default responses
# message to send to guests who don't write messages in one or our allowed languages list
send_in_eng_msg = "Hello %s, I am sorry! I don't understand you, can you please send again in English?"
# send to new accepted guests that just booked
send_new_booking_msg = True
new_booking_reply = """Hello %s, Thank you so much for your message..."""
# goodbye message to send to guests on check out day at 11am
send_checkout_msg = True
checkout_message = """Good morning %s,

Thank you so much again for staying with us..."""
# end default responses