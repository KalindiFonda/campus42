from django.shortcuts import render

from website.map import school_map

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from collections import defaultdict
import threading
import requests
import copy
import json
import sched, time
requests.packages.urllib3.disable_warnings()

INTRA_API_ROUTE = "https://api.intra.42.fr/v2/"
token = None
token_expires_at = int(time.time())
active_users = None
client_id = "Insert 42 application id here"
client_secret = "Insert 42 application secret here"

def get_token():
	global token
	global token_expires_at
	response = requests.post("https://api.intra.42.fr/oauth/token",
		data = {'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret},
		verify = False)
	print(response.text)
	token_data = response.json()
	token = token_data["access_token"]
	token_expires_at = int(time.time()) + token_data["expires_in"]

def parse_users(users):
	return [{"host": user["host"], "login": user["user"]["login"], "value": user["user"]["login"]} for user in users]

def update_users():
	print("Updating Active Users...")
	global active_users
	if not token or token_expires_at < int(time.time()):
		get_token()
	url = INTRA_API_ROUTE + "campus/7/locations?access_token=%s&filter[active]=true" % (token)
	response = requests.get(url)
	if response.ok:
		result = response.json()
		while("next" in response.links):
			url = response.links["next"]["url"]
			response = requests.get(url)
			result += response.json()
		active_users = parse_users(result)
		print("finished updating Active Users...")
	else:
		print("error updating Active Users...")

def index(request):
	return render(request, 'map.html', {'map': school_map})


def show_hostnames(request):
	return render(request, 'hostnames.html', {'map': school_map})

def get_active_users(request):
	return HttpResponse(json.dumps(active_users), content_type="application/json")

import csv

def edit_map(request):
	return render(request, 'edit_map.html', {'map': school_map})

@csrf_exempt
def save_map(request):
	global school_map
	school_map = json.loads(request.body)
	with open('website/new.csv', 'w') as csvfile:
		mapwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
		for row in school_map:
			mapwriter.writerow(row)
	print(school_map)
	return HttpResponse()

def active_users_job():
	while True:
		try:
			update_users()
		except Exception as e:
			print(e)
		time.sleep(60)

#read_map()
threading.Thread(target=active_users_job, args=()).start()
