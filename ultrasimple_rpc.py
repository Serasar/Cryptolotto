import json
import random
import requests

RPC_URL     = "http://127.0.0.1:18332"
RPC_USER    = "user"
RPC_PASS    = "password"

def rpc(method, params=None):
    rpc_id = random.getrandbits(32) # random for id

    callstr = json.dumps({"id": rpc_id, "method": method, "params": params}) # string with what we calling

    json_header = {"Content-Type": "application/json", 'user-agent': 'bitcoin-json-rpc/v.0.11.1'}

    request = requests.get(RPC_URL, headers=json_header, auth=(RPC_USER, RPC_PASS), data=callstr) # connection, auth and sending our callstr
    response = request.json() # save request as JSON

    if response['id'] != rpc_id:
        raise ValueError("invalid response id!") # error if wrong id
    elif response['error'] != None:
        raise ValueError("rpc error: %s" % json.dumps(response['error'])) # error if returned some error

    return response['result'] # our response

# Example usage
# print(rpc("walletpassphrase", ['fgtn3Q6D5sYWwXs8qpAY', 9999]))
# print(rpc("getaccountaddress", ['bank']))
# print(rpc("getaccountaddress", ['profit']))