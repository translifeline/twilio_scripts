import csv
import os
import threading
from datetime import date, timedelta
from queue import Queue

import requests
from requests.auth import HTTPBasicAuth
from twilio.rest import Client

from dotenv import load_dotenv
load_dotenv()

# Ensure your environmental variables have these configured
acct = os.environ["TWILIO_ACCOUNT_SID"]
auth = os.environ["TWILIO_AUTH_TOKEN"]
n_days = os.environ["RECORDINGS_TIME_DELTA"]

# Calculate the date n days ago for 
n_days_ago = date.today() - timedelta(days=n_days)

# Flags for toggling functionality
DELETE = True
DOWNLOAD = False

# Initialize Twilio Client
client = Client(acct, auth)

# Create a lock to serialize console output
lock = threading.Lock()


# The work method includes a print statement to indicate progress
def do_work(recording):
    if DOWNLOAD == True:
        # Recordings might be big, so stream and write straight to file
        data = requests.get(recording.uri, auth=HTTPBasicAuth(acct, auth),
                            stream=True)
        with open(recording.sid + '.wav', 'wb') as fd:
            for chunk in data.iter_content(1):
                fd.write(chunk)
        with lock:
            print(threading.current_thread().name, recording.sid, "has downloaded")
    if DELETE == True:
        result = client.recordings(recording.sid).delete()
        with lock:
            print(threading.current_thread().name, "has deleted", recording.sid)


# The worker thread pulls an item from the queue and processes it
def worker():
    while True:
        item = que.get()
        do_work(item)
        que.task_done()


# Create the queue and thread pool. The range value controls number of threads.
que = Queue()
for idx in range(20):
    thread = threading.Thread(target=worker)
    # thread dies when main thread (only non-daemon thread) exits.
    thread.daemon = True
    thread.start()

# Open up a CSV file to dump the results of deleted recordings into
with open('recordings.csv', 'w') as csvfile:
    record_writer = csv.writer(csvfile, delimiter=',')
    # Let's create the header row
    record_writer.writerow(["Recording SID", "Duration", "Date", "Call SID"])
    
    for recording in client.recordings.list(date_created_before=n_days_ago):
        record_writer.writerow([recording.sid, recording.duration,
                                recording.date_updated, recording.call_sid])
        que.put(recording)
    que.join()  # block until all tasks are done

print("All done!")