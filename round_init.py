from flask.ext.mongoengine import MongoEngine
from core import db, User, Round, Ticket

from ultrasimple_rpc import rpc

current_block = rpc("getblockcount", [])
last_block = current_block + 100

init_round = Round(round_number = 1, round_first_block = current_block, round_last_block = last_block, round_is_current = True)
init_round.save()