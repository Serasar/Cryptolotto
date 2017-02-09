from flask.ext.mongoengine import MongoEngine
from core import db, User, Round, Ticket

from ultrasimple_rpc import rpc

from time import sleep

from hashlib import sha256

def percentage(percent, whole):
	return (percent * whole) / 100.0

win_perc_list = [50, 25, 10, 5, 3, 2, 1, 1, 1]
BANK_ACCOUNT = 'bank'
PROFIT_ACCOUNT = 'profit'
BETWEEN_ROUNDS = 100

while True:
	sleep(2)
	current_block = rpc("getblockcount", [])
	current_round = Round.objects(round_is_current = True).first()
	if current_round.round_last_block <= current_block:
		winning_block_hash = rpc("getblockhash", [current_round.round_last_block]) # find hash of last block
		tickets = Ticket.objects(ticket_round = current_round)
		for i in tickets: # calculate win hashes
			number = i.ticket_number
			i.ticket_hash = (sha256(winning_block_hash.encode('utf-8') + number.encode('utf-8')).hexdigest())
			i.save()

		balance = rpc("getbalance", [BANK_ACCOUNT])
		payouts = [] # list of exact payouts

		for i in win_perc_list: # calculate how much to pay
			payouts.append(percentage(i, balance))

		tickets = Ticket.objects(ticket_round = current_round).order_by('ticket_hash')
		for tic, pay_perc, pay_exact in zip(tickets, win_perc_list, payouts): # payouts operations
			user = tic.ticket_user # selecting user of ticket
			tic.ticket_payout_perc = (pay_perc)
			tic.ticket_payout = (float(format(pay_exact, ".8f"))) # 8 numbers after dot
			tic.save()
			rpc("move", [BANK_ACCOUNT, user.user_code, pay_exact])
		balance = rpc("getbalance", [BANK_ACCOUNT])
		rpc("move", [BANK_ACCOUNT, PROFIT_ACCOUNT, balance])
		next_round = Round(round_number = current_round.round_number + 1, round_first_block = current_round.round_last_block, round_last_block = current_round.round_last_block + BETWEEN_ROUNDS, round_is_current = False)
		current_round.round_is_current = (False)
		current_round.save()
		next_round.round_is_current = (True)
		next_round.save()
	else:
		print("Not over.")