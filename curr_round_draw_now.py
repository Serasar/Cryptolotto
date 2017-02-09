from flask.ext.mongoengine import MongoEngine
from core import db, User, Round, Ticket

from ultrasimple_rpc import rpc

current_block = rpc("getblockcount", [])

current_round = Round.objects(round_is_current = True).first()
current_round.round_last_block = current_block
current_round.save()