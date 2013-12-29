#!/usr/bin/env python
import time
import praw
import sys
from ConfigParser import SafeConfigParser
import traceback
import codecs
from random import randint

# Reddit will sometimes give ratelimit errors. This will delay posting a comment until the wait time is over.
def handle_ratelimit(func, *args, **kwargs):
    while True:
        try:
            func(*args, **kwargs)
            break
        except praw.errors.RateLimitExceeded as error:
            print("Rate limit exceeded. Sleeping for %d seconds" % (error.sleep_time))
            time.sleep(error.sleep_time)

# Get an integer from a specified upper or lower value.
def num(val):
    try:
        return int(val)
    except ValueError:
        return 1

# Post a reddit comment about proper usage when someone uses this bot incorrectly.
def reply_usage(submission):
    reply = "You may be doing something incorrectly. Please enter the following command to use this bot: \"%s x y\" (where x and y are integers)." % triggers[0]
    handle_ratelimit(submission.reply, reply)

# Parse config file
parser = SafeConfigParser()
with codecs.open("bot.ini", "r", encoding="utf-8") as f:
    parser.readfp(f)
url = parser.get("General", "url")
summary = parser.get("General", "summary")
username = parser.get("General", "reddit_username")
password = parser.get("General", "reddit_password")
triggers = tuple(parser.get("General", "triggers").split(","))
subreddits = tuple(parser.get("General", "subreddits").split(","))

# Setup reddit api object
user_agent = "%s %s" % (summary, url)
r = praw.Reddit(user_agent=user_agent)
r.login(username, password)

already_done = [] # keeps track of what comments have been seen so we don't repost comments

# The main loop of the daemon, needs to be broken up.
while True:
    for subreddit_name in subreddits:
        subreddit = r.get_subreddit(subreddit_name)
        print("Getting comments for subreddit: %s" % (subreddit_name))
        for submission in subreddit.get_comments():
            print("Checking submission: %s" % (str(submission.id)))
            current_id = 0
            try:
                if submission.id not in already_done:
                    comment_text = submission.body.lower()
                    comment_text_lines = comment_text.split("\n")
                    results = []
                    for line in comment_text_lines:
                        if line.startswith(triggers):
                            current_id = submission.id
                            print("Found line, '%s'" % line)
                            try:
                                user,x,y = line.split()
                            except:
                                already_done.append(submission.id)
                                print("Invalid syntax. Skipped.")
                                reply_usage(submission)
                                continue 
                            if x is None or y is None: 
                                already_done.append(submission.id)
                                print("Invalid syntax. Skipped.")
                                reply_usage(submission)
                                continue 
                            print("Found parts: %s, %s, %s" % (user, x, y))
                            try:
                                if not x is None and x.lower() == "moon":
                                    x = 384400 # distance to the moon in kms
                                if not y is None and y.lower() == "moon":
                                    y = 384400 # distance to the moon in kms
                            except:
                                print "Error finding moon: ", sys.exc_info()[0]
                            print "x, y = %s, %s" % (str(x), str(y)) 
                            xInt = num(x)
                            yInt = num(y)
                            if xInt > yInt:
                                tmpInt = xInt
                                xInt = yInt
                                yInt = tmpInt
                            randnum = randint(xInt, yInt)
                            reply = "Random Number between %d and %d is %d." % (xInt, yInt, randnum)
                            print(reply)
                            results.append(reply)
                            already_done.append(submission.id)
                            continue
                    if len(results) > 0:
                        reply = "   \n".join(results)
                        results = []
                        print("Posting comment for %s:\n%s" % (submission.id, reply))
                        handle_ratelimit(submission.reply, reply)

            except:
                print "Unknown exception: ", sys.exc_info()[0]
                print traceback.format_exc()
                already_done.append(current_id)
                reply_usage(submission)
                continue
    time.sleep(30)