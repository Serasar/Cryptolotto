import requests
import json

SHAPESHIFT_URL = "https://shapeshift.io/"

def current_rate(input_coin, output_coin):
	r = requests.get(SHAPESHIFT_URL + "rate/" + input_coin + "_" + output_coin)
	return r.json()

def current_limit(input_coin, output_coin):
	r = requests.get(SHAPESHIFT_URL + "limit/" + input_coin + "_" + output_coin)
	return r.json()

def marketinfo(input_coin, output_coin):
	r = requests.get(SHAPESHIFT_URL + "marketinfo/" + input_coin + "_" + output_coin)
	return r.json()

def getcoins():
	r = requests.get(SHAPESHIFT_URL + "getcoins/")
	return r.json()

def shift(destination_address, return_address, input_coin, output_coin):
	pair = input_coin + "_" + output_coin
	json_header = {"Content-Type": "application/json"}
	payload = {"withdrawal":destination_address, "pair": pair,"returnAddress": return_address}
	r = requests.post(SHAPESHIFT_URL + "shift", headers=json_header, data = json.dumps(payload))
	return r.json()

def getcoins_form():
	x = getcoins()
	output = []
	for key, value in x.items():
		if value["status"] == "available" and key != "BTC":
			output.append((key, key + " " + value["name"]))

	return sorted(output, key=lambda output: output[1])