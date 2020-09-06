#!/usr/bin/env python
# coding: utf8

from time import sleep
from datetime import datetime
try:
    import json
except ImportError:
    from gluon.contrib import simplejson as json
from gluon.tools import fetch

Test = None

# запуск опроса бирж и получение от них цен
import exch_client
import rates_lib
import rates_yahoo
import rates_paypal
import db_client
import db_common
import serv_block_proc

def log(db, l2, mess='>'):
    print mess
    db.logs.insert(label123456789='s_rates', label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()



# курсы фиатных валют взять с разных источников
def form_fiats(db, exchg, curr2):
    currs_in = []
    for pair in db_client.get_exchg_pairs(db, exchg.id):
        if not pair.used: continue
        curr1 = db.currs[pair.curr1_id]
        if not curr1.used: continue

        # возьмем базовое количество
        pair_base = db((db.exchg_pair_bases.curr1_id == curr1.id)
            & (db.exchg_pair_bases.curr2_id == curr2.id)).select().first()
        #print pair_base
        pair_amo = pair_base and int(pair_base.base_vol	or 1000)
        currs_in.append(curr1.abbrev)

    if len(currs_in) == 0: return
    if exchg.name == 'PayPal':
        err, rates = rates_paypal.get_currs(currs_in)
    elif exchg.name == 'Yahoo':
        err, rates = rates_yahoo.get_currs(currs_in)
    if err:
        print '%s' % err
        return
    #print rates
    for abbr, rate in rates.iteritems():
        curr1 = db(db.currs.abbrev==abbr).select().first()
        err, pair_base = rates_lib.set_rate_base_ecurr(db, abbr, curr1, rate, 'USD', exchg.name, 0.5, curr2, exchg)
        if err: print err
        else: print abbr, 1/pair_base.base_vol*100 ## база = 100 умножает курс

#
def get_ticker(db, exchg_id, curr_id):
    curr = db.currs[curr_id]
    if curr.used:
        limits = db_client.get_limits(db, exchg_id, curr_id)
        return limits and limits.ticker or curr.abbrev.lower()
def get_curr(db, exchg_id, ticker):
    limit = db((db.exchg_limits.exchg_id==exchg_id) & (db.exchg_limits.ticker==ticker)).select().first()
    return limit and db.currs[limit.curr_id] or db(db.currs.abbrev==ticker.upper()).select().first()

def from_cryptsy(db, exchg):
    exchg_id = exchg.id
    ##print conn
    for pair in db_client.get_exchg_pairs(db, exchg_id):
        if not pair.used: continue
        t1 = get_ticker(db, exchg_id, pair.curr1_id)
        t2 = get_ticker(db, exchg_id, pair.curr2_id)

        '''
        http://pubapi.cryptsy.com/api.php?method=singlemarketdata&marketid=132
        DOGE - 132
        {"success":1,"return":{"markets":{"DOGE":{"marketid":"132","label":"DOGE\/BTC","lasttradeprice":"0.00000071","volume":"102058604.42108892","lasttradetime":"2015-07-07 09:30:31","primaryname":"Dogecoin","primarycode":"DOGE","secondaryname":"BitCoin","secondarycode":"BTC","recenttrades":[{"id":"98009366","time":"2015-07-07
        '''
        print t1, t2, 'pair.ticker:', pair.ticker,
        if Test: continue

        #try:
        if True:
            params = {'method': 'singlemarketdata', 'marketid': pair.ticker }

            res = fetch('http://' + exchg.url + '/api.php', params)
            res = json.loads(res)
            if type(res) != dict:
                continue
            if not res.get('success'): continue

            rr = res['return']['markets'].get('DOGE')
            if not rr:
                continue
            ll = rr['label']
            pair_ll = t1 + '/' + t2
            if ll.lower() != pair_ll.lower():
                print 'll.lower() != pair_ll.lower()', ll.lower(), pair_ll.lower()
                continue

            buy = rr['buyorders'][0]['price']
            sell = rr['sellorders'][0]['price']
            #return dict(buy= buy, sell= sell)
            print buy, sell
            db_common.store_rates(db, pair, sell, buy)
        #except Exception as e:
        else:
            msg = "serv_rates %s :: %s" % (exchg.url, e)
            print msg
            continue
    db.commit()

#  с биржи BTC-e.com
## api/3/ticker/btc_usd-btc_rur...
def from_btc_e_3(db,exchg):
    exchg_id = exchg.id
    pairs = []
    for pair in db_client.get_exchg_pairs(db, exchg_id):
        if not pair.used: continue
        t1 = get_ticker(db, exchg_id, pair.curr1_id)
        t2 = get_ticker(db, exchg_id, pair.curr2_id)
        if t1 and t2:
            pairs.append(t1+'_'+t2)
    pairs = '-'.join(pairs)
    url = 'http://btc-e.com/api/3/ticker/' + pairs
    print url
    resp = fetch(url)
    res = json.loads(resp)
    for k,v in res.iteritems():
        print k[:3], k[4:],  # v
        curr1 = get_curr(db, exchg_id, k[:3])
        curr2 = get_curr(db, exchg_id, k[4:])
        if not curr1 or not curr2:
            print 'not curr found for serv rate'
            continue
        pair = db((db.exchg_pairs.curr1_id == curr1.id)
              & (db.exchg_pairs.curr2_id == curr2.id)).select().first()
        if not pair:
            print 'pair nor found in get_exchg_pairs'
            continue
        db_common.store_rates(db, pair, v['sell'], v['buy'])
        print 'updates:', v['sell'], v['buy']
    db.commit()

#  с биржи BTC-e.com
def from_btc_e(db, exchg):
    from_btc_e_3(db, exchg)
    return

    for pair in db_client.get_exchg_pairs(db, exchg.id):
        if not pair.used: continue
        curr1 = db.currs[pair.curr1_id]
        if not curr1.used: continue
        curr2 = db.currs[pair.curr2_id]
        if not curr2.used: continue

        #print pair
        limits1 = db_client.get_limits(db, exchg.id, pair.curr1_id)
        limits2 = db_client.get_limits(db, exchg.id, pair.curr2_id)
        #if not limits1 or not limits2: continue
        # если нет лимитов то берем мелкие буквы
        #print pair.curr1_id, pair.curr2_id
        t1 = limits1 and limits1.ticker or None
        if not t1:
            t1 = curr1.abbrev.lower()
        t2 = limits2 and limits2.ticker or None
        if not t2:
            t2 = curr2.abbrev.lower()
        print "   ", t1, t2
        if Test: continue
        #if True:
        try:
            tab = exch_client.getDept(exchg.name, t1, t2)
            pass
        #else:
        except Exception as e:
            msg = "serv_rates %s :: %s" % (exchg.url, e)
            print msg
            continue

        db_common.store_depts(db, pair, tab)

def get_all(db, turn3):
    curr_usd = db(db.currs.abbrev == 'USD').select().first()
    if not curr_usd:
        print 'can\'t find USD currency'
        return

    for exchg in db(db.exchgs).select():
        #print exchg
        if not exchg.used: continue

        print exchg.name
        if exchg.name == 'BTC-e ic':
            #exch_client.conn(exchg)
            from_btc_e_3(db,exchg)
            #exch_client.conn_close(exchg)
        elif exchg.API_type=='fiat':
            if turn3: form_fiats(db, exchg, curr_usd)
        else:
            print 'unknowm exchange TYPE'

def get(db, not_local, interval=None):
    interval = interval or 55
    print __name__, 'not_local:',not_local, ' interval:', interval
    not_local = not_local == 'True'

    i_p3 = period3 = interval * 3
    while True:
        i_p3 += interval
        #print '\n', datetime.now()
        get_all(db, i_p3 >= period3)
        # по всем биржам

        db.commit()
        print '\n', datetime.now()

        if False and not_local:
            pass
        else:
            print 'local use - skeep serv_to_buy.proc_history and clients_lib.notify'

        if Test: break
        print 'sleep',interval,'sec'
        db.commit() # перед сном созраним все
        if i_p3 >= period3:
            i_p3=0
        sleep(interval)

if Test: get(db)

# если делать вызов как модуля то нужно убрать это иначе неизвестный db
import sys
#print sys.argv
if len(sys.argv)>1:
    get(db, sys.argv[1], float(sys.argv[2]))
