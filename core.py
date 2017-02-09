from flask import Flask, flash, session, redirect, url_for, escape, request, render_template

from datetime import timedelta

from flask.ext.bootstrap import Bootstrap

from flask.ext.mongoengine import MongoEngine

from flask_wtf import Form

from flask.ext.wtf import Form
from flask.ext.wtf.recaptcha import RecaptchaField
from wtforms import StringField, SubmitField, FloatField, IntegerField, SelectField
from wtforms.validators import Required, Length, NumberRange

from os import urandom

from hashlib import sha256

import re

from ultrasimple_rpc import rpc

import shapeshift

import json

### Config start ###

app = Flask(__name__)
bootstrap = Bootstrap(app)

# set the secret key.  keep this really secret:
app.secret_key = ''

db = MongoEngine(app)

TICKET_PRICE = 0.00000001
BANK_ACCOUNT = 'bank'

RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''

app.config.from_object(__name__)

### Config end ###

class User(db.Document):
    user_code = db.StringField(max_length=64, required=True)
    pin = db.StringField(max_length=64)

class Round(db.Document):
    round_number = db.IntField(unique=True)
    round_first_block = db.IntField(unique=True)
    round_last_block = db.IntField(unique=True)
    round_is_current = db.BooleanField()

class Ticket(db.Document):
    ticket_hash = db.StringField(max_length=64)
    ticket_number = db.StringField(max_length=100, required=True, unique=True)
    ticket_round = db.ReferenceField(Round)
    ticket_user = db.ReferenceField(User)
    ticket_is_free = db.BooleanField()
    ticket_payout_perc = db.IntField()
    ticket_payout = db.FloatField()

class AddressForm(Form):
    addr = StringField('Address for withdrawal. Must be correct BTC address.', validators=[Required(), Length(26, 35)])
    amount_addr = FloatField('Amount to withdraw in BTC.', validators=[Required()])
    submit_addr = SubmitField('Withdraw')

class AddressFormAltcoin(Form):
    coin = SelectField('Choose altcoin for withdrawal.', validators=[Required()])
    addr = StringField('Address for withdrawal. Must be correct address of corresponding altcoin.', validators=[Required()])
    amount_addr = FloatField('Amount to withdraw in BTC. Will be converted to corresponding altcoin automatically.', validators=[Required()])
    submit_addr = SubmitField('Withdraw')

class TicketForm(Form):
    amount_tickets = IntegerField('Amount of tickets to buy. Ticket price is 0.00000001 BTC', validators=[Required(), NumberRange(1,5000)])
    submit_tickets = SubmitField('Buy tickets.')


class TicketFormFree(Form):
    recaptcha = RecaptchaField()
    submit_tickets = SubmitField('Get free ticket.')

pattern = re.compile('[a-zA-Z0-9]')

def create_tickets(number, user):
    current_round = Round.objects(round_is_current = True).first()
    for i in range(number):
        temp_number = (sha256(urandom(30)).hexdigest())
        temp = Ticket(ticket_number = temp_number, ticket_round = current_round, ticket_user = user)
        temp.save()

def create_ticket_free(user):
    current_round = Round.objects(round_is_current = True).first()
    temp_number = (sha256(urandom(30)).hexdigest())
    temp = Ticket(ticket_number = temp_number, ticket_round = current_round, ticket_user = user, ticket_is_free = True)
    temp.save()


def is_balance_enough(balance, total_charge):
    if balance - total_charge >=0:
        return True
    else:
        return False

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=9999)

@app.route('/')
def index():
    if 'name' in session:
        return redirect(url_for('user', name = session['name']))
    else:
        return redirect(url_for('create_user'))

@app.route('/user/<name>', methods=['GET', 'POST'])
def user(name):
    valid = re.match(pattern, name)


    form_addr = AddressForm(request.form, prefix='form_addr_1')
    form_addr_altcoin = AddressFormAltcoin(request.form, prefix='form_addr_altcoin_1')
    form_addr_altcoin.coin.choices = shapeshift.getcoins_form()
    form_ticket = TicketForm(request.form, prefix='form_ticket_1')
    form_ticket_free = TicketFormFree(request.form, prefix='form_ticket_free_1')
    user_curr = User.objects(user_code = name).first()
    if len(name) == 64 and valid and user_curr:
        balance = rpc("getbalance", [name])
        # balance = ("{0:.8f}".format(balance))
        address = rpc("getaccountaddress", [name]) # address for deposit

        current_round = Round.objects(round_is_current = True).first()

        previous_round = Round.objects(round_number = current_round.round_number - 1).first()

        if previous_round is None:
            prev_last_block = None
        else:
            prev_last_block = previous_round.round_last_block

        total_bank = rpc("getbalance", [BANK_ACCOUNT])

        current_block = rpc("getblockcount", [])

        if request.args.get('user_curr_page') is None: # page of current round user tickets
            user_curr_page = 1
        else:
            user_curr_page = int(request.args.get('user_curr_page'))

        if request.args.get('user_curr_page_prev') is None: # page of previous round user tickets
            user_curr_page_prev = 1
        else:
            user_curr_page_prev = int(request.args.get('user_curr_page_prev'))

        if request.args.get('all_tickets_page') is None: # page of all tickets
            user_curr_page_prev = 1
        else:
            user_curr_page_prev = int(request.args.get('all_tickets_page'))

        if request.args.get('all_tickets_page_prev') is None: # page of all tickets
            user_curr_page_prev = 1
        else:
            user_curr_page_prev = int(request.args.get('all_tickets_page_prev'))

        paginated_tickets_user = Ticket.objects(ticket_user = user_curr, ticket_round = current_round).order_by('ticket_number').paginate(page=user_curr_page, per_page = 100)

        paginated_tickets_user_prev = Ticket.objects(ticket_user = user_curr, ticket_round = previous_round).order_by('ticket_hash').paginate(page=user_curr_page_prev, per_page = 100)

        paginated_tickets_all = Ticket.objects(ticket_round = current_round).order_by('ticket_number').paginate(page=user_curr_page_prev, per_page = 100)

        paginated_tickets_all_prev = Ticket.objects(ticket_round = previous_round).order_by('ticket_hash').paginate(page=user_curr_page_prev, per_page = 100)

        total_your_tickets = len(Ticket.objects(ticket_user = user_curr, ticket_round = current_round))

        free_ticket = Ticket.objects(ticket_user = user_curr, ticket_round = current_round, ticket_is_free = True).first()

        if form_addr_altcoin.addr.data and form_addr_altcoin.validate_on_submit(): # form for altcoin withdrawal
                if is_balance_enough(rpc("getbalance", [name]), form_addr_altcoin.amount_addr.data) is True:
                    address_to_send = form_addr_altcoin.addr.data
                    amount_to_send = form_addr_altcoin.amount_addr.data
                    temp = shapeshift.shift(address_to_send, address, "btc", form_addr_altcoin.coin.id)
                    rpc("sendmany", [name, {temp["deposit"]:amount_to_send}, 1, '', [address_to_send]])
                    flash('Successuflly sent Bitcoins.', 'success')
                else:
                    flash('Operation failed, not enough balance.', 'danger')

        if form_addr.addr.data and form_addr.validate_on_submit(): # form for btc withdrawal
            if is_balance_enough(rpc("getbalance", [name]), form_addr.amount_addr.data) is True:
                address_to_send = form_addr.addr.data
                amount_to_send = form_addr.amount_addr.data
                rpc("sendmany", [name, {address_to_send:amount_to_send}, 1, '', [address_to_send]])
                flash('Successuflly withdrawed. Refresh page to see updated balance.', 'success')
            else:
                flash('Operation failed, not enough balance.', 'danger')

        if form_ticket.amount_tickets.data and form_ticket.validate_on_submit(): # form for buying tickets
            if is_balance_enough(rpc("getbalance", [name]), form_ticket.amount_tickets.data * TICKET_PRICE) is True:
            # if is_balance_enough(rpc("getbalance", [name]), form_ticket.amount_tickets.data * TICKET_PRICE) is True and Round.objects(round_is_current = True).first().round_last_block <= rpc("getblockcount", []):
                amount_of_tickets = form_ticket.amount_tickets.data
                create_tickets(amount_of_tickets, user_curr)
                rpc("move", [name, BANK_ACCOUNT, amount_of_tickets * TICKET_PRICE])
                flash('Bought ticket(s). Refresh page to see ticket(s) and updated balance.', 'success')
            else:
                flash('Operation failed, not enough balance.', 'danger')

        if form_ticket_free.validate_on_submit() and Ticket.objects(ticket_user = user_curr, ticket_round = current_round, ticket_is_free = True).first() is None:
            create_ticket_free(user_curr)
            return redirect(url_for('user', name = name))

        return render_template('index.html',
        # user specific definitions 
        name = name,
        balance = balance,
        address = address,
        form_addr = form_addr,
        form_addr_altcoin = form_addr_altcoin,
        form_ticket = form_ticket,
        form_ticket_free = form_ticket_free,
        # for curr round
        user_tickets = paginated_tickets_user,
        total_your_tickets = total_your_tickets,
        free_ticket = free_ticket,
        # for prev round
        paginated_tickets_user_prev = paginated_tickets_user_prev,
        # global definitions
        paginated_tickets_all = paginated_tickets_all,
        paginated_tickets_all_prev = paginated_tickets_all_prev,
        current_block = current_block,
        current_round = current_round.round_number,
        draw_on_block = current_round.round_last_block,
        draw_on_block_prev = prev_last_block,
        total_bank = total_bank,
        blocks_to_draw = current_round.round_last_block - current_block,
        )
    else:
        return "User doesn't exist." # return page with error

@app.route('/create_user')
def create_user():
    temp_user = sha256(urandom(30)).hexdigest()

    temp_user_db = User(user_code = temp_user)
    temp_user_db.save()

    rpc("getnewaddress", [temp_user])
    session['name'] = temp_user

    return redirect(url_for('user', name=temp_user))

if __name__ == '__main__':
    app.run(debug=True)