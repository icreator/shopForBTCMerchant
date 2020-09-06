#!/usr/bin/env python
# coding: utf8
from time import sleep
Test = None

## TODO - db.shops_draws.shop_id==202 data.now() - not defaul - request - constdnt

from decimal import Decimal
import datetime
#from gluon import *
import urllib, urllib2
import httplib
from gluon.tools import fetch

import json

from common import rnd_8
import db_common, db_client
import crypto_client
import rates_lib

def log(db, l2, mess='>'):
    m = 'shops_lib'
    mess = '%s' % mess
    print m, l2, mess
    db.logs.insert(label123456789 = m, label1234567890 = l2, mess = mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

# если счет создан по адресу кошелька а не магазину, зарегистрированному у нас
# то создаем новый магазин (или старый)
def make_simple_shop(db, name, vars, noseek=False, curr=None, xcurr=None):
    if not noseek: shop = db(db.shops.name==name).select().first()
    #print shop
    if noseek or not shop:
        if not curr and vars.get('conv_curr'):
            # найдем по абривиатуре
            curr, xcurr, _ = db_common.get_currs_by_abbrev(db, vars['conv_curr'])
        if not xcurr:
            return
        # проверим на слэш в конце УРЛ - он мешает при уведомлении - удалим
        url = vars.get('shop_url')
        # от / не зависит if url[-1:] == '/': url = url[:-1]
        shop_id = db.shops.insert(name = name,
                     simple_curr = curr.id,
                     url =        url,
                     show_text =  vars.get('show_text'),
                     note_url =   vars.get('note_url'),
                     back_url =   vars.get('back_url'),
                     note_on =    vars.get('note_on'),
                     icon_url =   vars.get('icon_url'),
                     email =      vars.get('email'),
                     not_listed = True,
                     )
        shop = db.shops[shop_id]
        # и добавим адрес кошелька
        db.shops_xwallets.insert( shop_id = shop_id, xcurr_id = xcurr.id, addr = name )

    return shop

# используется при создании счета оплаты в make
def is_simple_shop(db, vars, shop_id):
    shop = None
    if len(shop_id) > 30:
        # это адрес криптовалюты куда выводить - тут магазин неизвестен
        curr, xcurr, _ = db_common.get_currs_by_addr(db, shop_id)
        if not xcurr:
            return None, None
        cc = crypto_client.connect(curr, xcurr)
        if not cc or crypto_client.is_not_valid_addr(cc, shop_id):
            return None, None
        # поиска магазина еще не было - False
        shop = make_simple_shop(db, shop_id, vars, False, curr, xcurr)
        if not shop:
            # мгазин не найден и не создан
            return None, None
        shop_id = shop.id
    elif not shop_id.isdigit():
        return None, None
    shop = shop or db.shops[shop_id]
    return shop, shop_id

def get_trans(db, shop, order_id):
    return db((db.shops_trans.shop_id == shop.id)
              & (db.shops_trans.order_id == order_id)).select()
def get_bal(db, shop, curr):
    xw = db((db.shops_balances.shop_id == shop.id)
            & (db.shops_balances.curr_id == curr.id)).select().first()
    return xw and xw.bal or None

def update_bal(db, shop, curr, amo, keep=None, shop_bal=None):
    shop_bal = shop_bal or db((db.shops_balances.shop_id == shop.id)
            & (db.shops_balances.curr_id == curr.id)).select().first()
    if not shop_bal:
        id = db.shops_balances.insert(
                shop_id = shop.id,
                curr_id = curr.id,
                bal = 0,
                kept = 0.0,
                )
        shop_bal = db.shops_balances[id]

    amo_bal = Decimal(amo)
    amo_keep = Decimal(0)
    if keep and keep>0:
        if keep > 1: keep = Decimal(1)
        amo_keep = Decimal(amo) * Decimal(keep)
        amo_bal = Decimal(amo) - Decimal(amo_keep)
    shop_bal.update_record(bal = shop_bal.bal + Decimal(amo_bal), kept = shop_bal.kept + Decimal(amo_keep))
    db.commit() # гаче там потом берется неизмененый баланс

    print 'updated bal, kept:', shop.url or shop.name, shop_bal.bal, shop_bal.kept

    return shop_bal.bal

# счет с автовыплатами - создадим записи на выплаты по этому счету
# а на результате дадим остаток от KEEP для создания транзакции для магазина
# тоесть в автовыплатах учавствовать будет сумма не вся а та что в УДЕРЖАННЫЕ не входит
def bills_draw_insert(db, shop_order, curr, amo, desc):
    # сначала подсчет общего веса
    tab = shop_order.addrs
    vol = 0
    for (k,v) in tab.iteritems():
        v = float(v)
        vol += v
        tab[k] = v

    # теперь вычислим курсы обмена для данной крипты входа
    rates = rates_lib.get_best_rates(db, curr) # загодя возьмем курсы обмена для этой крипты
    amo = float(amo)

    # посмотрим что оставить магазину в резерв
    amo_keep = 0
    keep = shop_order.keep
    if keep and keep>0:
        if keep>1: keep = 1
        amo_keep = amo * float(keep)
        # новое АМО берем
        amo = amo - amo_keep

    for (addr, v) in tab.iteritems():
        amo_out = rnd_8( v/vol * amo)
        # найдем курс обмена
        curr2, x, e = db_common.get_currs_by_addr(db, addr)
        if curr2.id != curr.id:
            rate = rates_lib.get_best_rate(rates, curr2, amo_out)
            amo_out = rate * amo_out

        _id = db.bills_draws.insert(
            shop_order_id = shop_order.id,
            curr_id = curr2.id,
            addr = addr,
            amo = amo_out,
            )
    db.commit() # гаче там потом берется неизмененый баланс
    return Decimal(amo_keep)

# сюда приходит при смене статуса у заказа на выплату в баланс магазина
# amo - велична на которую надо увеличить баланс магазина
# но еслии у счета зананы дареса автовыплат - надо без изменения
# баланса у магазина сделать выплаты - как?
# тут нужен pay_in - все данные от входе на случай если
# для магазина не нужна конвертация входов - not_convert=1
# curr_pay_in=None, amo_pay_in=None - это неконвертированные значения входа и валюты
def insert_shop_trans_order(db, shop_order, amo, shop, curr, desc, curr_pay_in, amo_pay_in):
    if not shop:
        shop = db.shops[shop_order.shop_id]
    if not curr:
        curr = db.currs[shop_order.curr_id]

    log(db, 'insert_shop_trans_order for shop %s, amo: %s bill: %s' % (shop.id, amo, shop_order))

    # берем тут то что надо удержать - если будут автовыплаты то он станет = 1
    keep = shop_order.keep
    if shop_order.addrs:
        # если у счета есть адреса для авто выплат то создадим их
        # в транзакции магазина запишем результат транзакции
        # и остаток для удержания - keep, но для записи в балансы его сделаем keep =1
        # и баланс магазина  тоже не будем менять - там тогда баланс пересчитается с keep=1
        amo_keep = bills_draw_insert(db, shop_order, curr_pay_in, amo_pay_in, desc)
        desc = '%s: to auto send many' % desc
        # дальше баланс надо в остаток записать
        amo = amo_keep
        keep = 1
        #print 'shop_order.addrs is SET - new keep:', amo, keep, shop_order.addrs

    # продоложим с остатоком
    if amo and not shop_order.not_convert and shop_order.conv_curr_id:
        # если не запрещено конвертировать и есть валюта конвертации то
        conv_curr = db.currs[shop_order.conv_curr_id]
        conv_amo = rates_lib.conv_pow(db, curr, amo, conv_curr)
        #print 'convert to', conv_curr.abbrev, conv_amo
        curr = conv_curr
        amo = conv_amo

    shops_trans_id = db.shops_trans.insert(
        shop_order_id = shop_order and shop_order.id or None,
        curr_id = curr.id,
        amo = amo,
        desc_ = desc,
        )
    #print '%s[%s] inserted to SHOP %s' % (amo, curr.abbrev, shop.url or shop.id)
    shop.update_record( uses = (shop.uses or 0) + 1)
    # тут валюта и курс не понятен average = shop.average or Decimal

    # изменим баланс валют на счетах клиента
    # там же commit()
    print 'insert_shop_trans_order - ', shop.id, ' update_bal: amo, keep', amo, keep
    update_bal(db, shop, curr, amo or 0, keep)
    db_common.curr_update_bal(curr, amo)
    db.commit() # гаче там потом берется неизмененый баланс
    return shops_trans_id

# вызов из orders_lib.note_test
def insert_shop_trans_withdraw(db, shop, curr, amo, desc):
    shop_bal = None
    xcurr = db(db.xcurrs.curr_id == curr.id).select().first()
    xwallet = xcurr and db((db.shops_xwallets.shop_id == shop.id)
            & (db.shops_xwallets.xcurr_id == xcurr.id)).select().first()
    return insert_shop_trans_withdraw(db, shop, curr, xcurr, shop_bal, xwallet, desc, amo)

## вот тут вычтем комсу среды из баланса магазина так чтобы том минус нам ушел
def insert_shop_trans_withdraw(db, shop, curr, xcurr, shop_bal, xwallet, desc, amo=None):
    # изменим баланс валют на счетах клиента
    # причем так же вычтем за коммиссию среды
    amo = amo or shop_bal and shop_bal.bal or 0
    txfee = shop_bal.txfee or xcurr.txfee or Decimal(0.00005)
    bal = update_bal(db, shop, curr, -amo - txfee * 3, shop_bal)
    # а резерв с магазинов снимаем без процентов своих
    db_common.curr_update_bal(curr, -amo)

    shops_trans_id = db.shops_draws.insert(
        shop_id = shop.id,
        curr_id = curr.id,
        amo = amo,
        desc_ = desc,
        created_on = datetime.datetime.now(), # обязательно нужно указать время иначе по умолчанию request.now один и тот же
        )
    if xwallet:
        xwallet.update_record( payouted = xwallet.payouted + Decimal(amo) )

    db.commit()
    #print '%s[%s] withdrawed to SHOP %s' % (amo, curr.abbrev, shop.name or shop.url or shop.id)
    return shops_trans_id, bal

def try_make_note_url2(db, shop, shop_order, cmd, pars=None):
    note_url = shop.note_url
    if not note_url: return
    #print  shop_order, '\n', cmd
    try:
        #print note_url
        #if note_url[:0] == '/': note_url = note_url[1:]
        url_resp = '%s' % note_url
        #print url_resp

        if shop_order:
            pars0 = { 'bill': shop_order.id, 'order': shop_order.order_id }
        elif cmd:
            pars0 = { 'cmd': cmd.hash1 }
        else:
            pars0 = None
        #print pars0
        if pars:
            # добавим параметры еще к строке
            if pars0:
                pars0.update(pars)
            else:
                pars0 = pars
        url_resp = url_resp + urllib.urlencode(pars0)

        return url_resp
    except Exception as e:
        log(db, 'try_make_note_url2', 'ERROR make url_resp %s' % e)
        return

def try_make_note_url(db, shop, shop_order, cmd, pars=None):
    url_pars = try_make_note_url2(db, shop, shop_order, cmd, pars)
    if url_pars: return '%s%s' % (shop.url, url_pars)
    return

def notify_one_url(db, shop, shop_order, cmd=None):
    url_path = try_make_note_url2(db, shop, shop_order, cmd)
    if not url_path:
        return

    r = None
    timeout = 10
    host = shop.url
    try:
        #f = urllib2.urlopen(host + '/' + url_path , None, timeout)
        #r = f.getcode()
        #print 'resp_status:',r.status, r.reason
        ## на некоторых облаках защита стоит - если нет cookies - то запрос банится и не шлется дальше клиенту !
        #r = urllib.urlopen(host + '/' + url_path).read()
        r = fetch(host + '/' + url_path) # with cookies - unti-DDOS проходит через такие защиты серверов успешно
        print r
        return r
    except Exception as e:
        #log(db, 'notify_one', '%s/%s\n error: %s' % (host, url_path, e))
        print '%s/%s\n error: %s' % (host, url_path, e)
        pass
    return
#################################### OLD
'''
    #if host[-1:] == '/': host = host[:-1]
    #if host[-1:] != '/': host += '/'
    print 'try httplib.HTTPConnection(%s)' % host
    try:
        log(db, 'notify_one', '%s + %s' % (host, url_path))
        if host[0:7] == 'http://':
            host = host[7:]
            conn_ = httplib.HTTPConnection(host, None, None, timeout)
        elif host[0:8] == 'https://':
            host = host[8:]
            conn_ = httplib.HTTPSConnection(host, None, None, None, None, timeout)
        #print host, conn_
    except Exception as e:
        log(db, 'notify_one', 'ERROR: httplib.HTTPConnectio(%s) -> %s' % (host, e))
        return 'not connect - %s' % e
    #print 'try  conn_.request(%s)' % url_path
    try:
        # HTTPS апшет, а HTTP нет
        # error - 301, removed - значит там вместо HTTP HTTPS и надо задавать адрес магазина https://bitrent.in
        path = host + '/' + url_path
        print 'PATH:', path
        conn_.request('HEAD', path)
        r = conn_.getresponse()
        print 'resp_status:',r.status, r.reason
        #log(db, 'notify_one', 'conn res.status: %s  res.reason' % (r.status, r.reason))
        #print r
    except Exception as e:
        log(db, 'notify_one', 'ERROR: httplib.HTTPConnection(%s) -> %s' % (url_path, e))
        try:
            f = urllib.urlopen( shop.url + '/' + url_path)
            r = f.read()
            print 'resp_status:',r.status, r.reason, r.read()
        except Exception as e:
            log(db, 'notify_one', 'ERROR: urllib.urlopen(%s/%s) -> %s' % (host, url_path, e))
            pass
    conn_.close()
    return r
'''

def notify_one(db, note):
    #print note
    tries = note.tries or 0

    if tries > 6:
        # пусть сам магазин спрашивает если он не прочухался
        del db.shop_orders_notes[note.id]
        return
    if tries > 0:
        tmin = note.created_on
        dSec = 30 + 60*2**(tries - 1)
        dt_old = datetime.datetime.now() - datetime.timedelta(0, dSec )
        #print datetime.timedelta(0, 30 + dSec ), ' - ', dt_old
        if note.created_on > dt_old:
            #print 'till wail'
            return

    print 'note id:', note.id, 'tries:', tries
    # сюда пришло значит время пришло послать уведомление
    shop = shop_order = cmd = None
    if note.ref_id:
        # уведомление для счета
        shop_order = db.shop_orders[note.ref_id]
        shop = db.shops[shop_order.shop_id]
    elif note.cmd_id:
        # уведомление по выполненой команде
        cmd = db.shops_cmds[note.cmd_id]
        shop = db.shops[cmd.shop_id]

    if not(shop.url and len(shop.url)>5 and shop.note_url and len(shop.note_url)>1):
        # нету данных - удалим запись уведомления тогда
        del db.shop_orders_notes[note.id]
        return
    f = r = None

    r = notify_one_url(db, shop, shop_order, cmd)
    '''
    url_path = try_make_note_url2(db, shop, shop_order, cmd)
    if not url_path:
        # что-то не то с адресом - остави запись может адрес щас поменяем
        #del db.shop_orders_notes[note.id]
        #tries = 10
        #note.update_record(tries=tries)
        return

    r = None
    timeout = 2
    print 'try httplib.HTTPConnection(%s)' % shop.url
    try:
        #urllib.urlopen(url_resp)
        #f = urllib.urlopen(url_resp)
        #r = f.read()
        #log(db, 'notify_one', r)
        host = shop.url #'bitrent.in'
        #host = 'bitrent.in'
        if shop.url[0:7] == 'http://':
            host = shop.url[7:]
            conn_ = httplib.HTTPConnection(host, None, None, timeout)
        if shop.url[0:8] == 'https://':
            host = shop.url[8:]
            conn_ = httplib.HTTPSConnection(host, None, None, None, None, timeout)
        print host, conn_
    except Exception as e:
        log(db, 'notify_one', 'ERROR: httplib.HTTPConnectio(%s) -> %s' % (shop.url, e))
        return 'not connect - %s' % e
    print 'try  conn_.request(%s)' % url_path
    try:
        #url_path = '/index.php'
        #log(db, 'notify_one', 'url_path: %s' % url_path)
        #conn_.request('HEAD', url_path) # 'GET' не пашут почемуто?
        # HTTPS апшет, а HTTP нет
        # error - 301, removed - значит там вместо HTTP HTTPS и надо задавать адрес магазина https://bitrent.in
        conn_.request('HEAD', url_path)
        r = conn_.getresponse()
        print r.status, r.reason
        #print r
    except Exception as e:
        #log(db, 'notify_one', 'ERROR: urllib.urlopen(url_resp) -> %s' % e)
        pass
    conn_.close()
    '''
    tries = tries + 1
    note.update_record(tries=r and 99 or tries)
    return r

def notify(db):
    res = ''
    for note in db(db.shop_orders_notes).select():
        res = res + '%s<br>\n\n<br>' % notify_one(db, note)
    #db.commit()
    return res

#
# выплаты по отдельным счетам с автовыплатой
def bills_withdraw(db, curr, xcurr, cn):
    addrs = {}
    bills = {}
    amo_total = 0
    # возьмем резерв который для магазинов есть (за минусом моего резерва)
    bal_free = db_common.get_reserve(curr)
    # тут без учета что в магазинах есть - только свободные деньги db_common.get_shops_reserve( curr )
    print '\n bills_withdraw exclude shop_deposites, bal_free:', bal_free, curr.abbrev
    # берем заданные крипту и все балансы по ней
    for rec in db((db.bills_draws.curr_id == curr.id)
                  & (db.bills_draws.amo > 0)).select():
        amo = rnd_8(rec.amo) # за вычетом комиссии сети
        if amo <= 0: continue
        if False and amo_total + amo > bal_free:
            ## НЕЛЬЗЯ тут выходы делать так как ттам ниже все записи на взод удаляются
            ## и они не выполненые тоже ббудутт удалены
            ##log(db, 'bills_withdraw', 'ERROR: bal_free < amo_total : %s < %s' % (bal_free, amo_total + amo))
            ##break
            pass

        addr = rec.addr
        if not addr or len(addr) < 20:
            continue
        # тут может быть несколько выплат на один адрес - суммируем
        addrs[addr] = addrs.get(addr,0) + amo
        shop_order_ids = '%s' % rec.shop_order_id
        #print 'update', amo, rec.addr, shop_order_ids

        # накопим сумму для каждого счета отдельно
        bills[shop_order_ids] = bills.get(shop_order_ids, 0) + amo
        amo_total += amo

    #print addrs
    if len(addrs)==0: return # ничего не собрали
    #addrs_outs =

    bal_free = db_client.curr_free_bal(curr)
    print 'bal_free:', bal_free, ' amo_total to send:', amo_total, '\n *** BILLS out:', bills
    if amo_total >= bal_free:
        log(db, 'bills_withdraw', 'ERROR: bal_free < amo_total : %s < %s' % (bal_free, amo_total))
        return
    small_koeff = 100
    if amo_total < xcurr.txfee * small_koeff:
        log(db, 'bills_withdraw', 'amo_total so small : %s < %s' % (amo_total, xcurr.txfee * small_koeff))
        return
    # теперь надо выплату сделать разовую всем за раз
    # отлько таксу здесь повыше сделаем чтобы быстро перевелось
    #{ 'txid': res, 'tx_hex': tx_hex, 'txfee': transFEE }
    #print 'bills:', bills
    #print 'addrs', addrs
    #return
    #!!! вдруг база залочена - проверим это
    log(db,'*** bills_withdraw', 'try for addrs: %s' % addrs)
    res = crypto_client.send_to_many(db, curr, xcurr, addrs, float(xcurr.txfee or 0.0001), cn )
    if not res or 'txid' not in res:
        log(db, 'bills_withdraw', 'ERROR: crypto_client.send_to_many = %s' % res)
        return

    # удалим сразу
    db(db.bills_draws.curr_id == curr.id).delete()
    # деньги перевелись нужно зачесть это по счетам
    txid = res['txid']
    # а то вдруг база залочена - проверим это
    log(db,'bills_withdraw', 'txid:%s for addrs:%s' % (txid, addrs))
    # запоним а какой транзакции и сколько выплочено по этому счету
    for (bill_id, amo) in bills.iteritems():
        db.bills_draws_trans.insert(
                shop_order_id = bill_id,
                curr_id = curr.id,
                txid = txid,
                amo = amo,
                )

    #curr.update_record( balance - в serv_block_proc.run_once() один раз делается после блока
    # сохраним сразу данные!
    db.commit()


# сделать выплату если депозит магазинов больше withdraw_over или раз в сутки все
# withdraw_over - тогда не задаем
# запускается из serv_block_proc - когда найден новый блок
def withdraw(db, curr, xcurr, cn, withdraw_over=None):

    # обновим данные балансгв - онни в ордерах поменялиись в обход этой записи
    curr = db.currs[ curr.id ]
    print '\n WITHDRAW - ', curr.abbrev, 'bal:', curr.balance, 'dep:',curr.deposit, 'shops_dep:',curr.shops_deposit
    print '    withdraw_over:', withdraw_over

    # сделать выплаты по отдельным счетам с автоплатежами
    bills_withdraw(db, curr, xcurr, cn)

    print '  after bills_withdraw - bal:', curr.balance, 'dep:',curr.deposit, 'shops_dep:',curr.shops_deposit
    # если общий депозит всех магазинов достаточен то выплату им забабахаем
    txfee = xcurr.txfee
    tx_over = 500
    if not withdraw_over:
        # если превышение = 0 то по умолчанию берем превышение по коммисии сети
        withdraw_over = txfee * tx_over
    elif False and curr.shops_deposit <= 0:
        return
    elif False and curr.shops_deposit < withdraw_over:
        return

    addrs = {}
    shops_bals = [] # нужно потом разделить по разным магазинам у кого былл один и тот же адрес
    amo_sum = 0
    # возьмем резерв который для магазинов есть (за минусом моего резерва)
    #print 'withdraw - ', db_common.get_reserve(curr)
    shops_reserve = db_common.get_shops_reserve(curr)
    reserve_small = False # указывает на то что резервов в притык
    # берем заданные крипту и все балансы по ней
    for bal_rec in db((db.shops_balances.curr_id == curr.id)
            & (db.shops_balances.bal > 0 )).select():

        bal_txfee = bal_rec.txfee
        if bal_txfee and bal_txfee > txfee:
            # если у когото есть комса больше чем общая для всех, то ее берем
            txfee = bal_txfee

        ##### всем платим скопом!
        # shop_withdraw_over = bal_rec.withdraw_over or withdraw_over or 0
        # if bal_rec.bal < withdraw_over:
        #    continue

        ## без учета комиссии - нам и так больше сейчас должно приходить от покупателей
        ## вернее учет комсы делаем при вычите из баланса магазина
        ## amo = rnd_8(bal_rec.bal - 0*txfee) # за вычетом комиссии сети
        amo = float(bal_rec.bal)
        if amo < txfee * 30: continue

        # locket db
        shop = db.shops[bal_rec.shop_id]
        xwallet = db((db.shops_xwallets.shop_id == shop.id)
                        & (db.shops_xwallets.xcurr_id == xcurr.id)).select().first()
        if not xwallet: continue

        addr = xwallet.addr
        if not addr or len(addr) < 30:
            #print 'not valid addr:', addr
            continue

        valid = cn.validateaddress(addr)
        if not valid or 'isvalid' in valid and not valid['isvalid'] or 'ismine' in valid and valid['ismine']:
            #print 'not valid addr in withdraw:', addr, valid
            continue
        print 'add amo to withdraw poll:', amo

        if amo_sum + amo > shops_reserve - txfee:
            reserve_small = True # резервов впритык
            # баланс крипты смотрим - если ее не хватило - прерываем накопление пула на выплаты
            log(db, 'withdraw', 'amo_sum %s > shops_reserve %s [%s]' % (amo_sum + amo, shops_reserve, curr.abbrev))
            break
        shops_bals.append( [shop,  bal_rec, xwallet] )
        addrs[addr] = addrs.get(addr, 0.0) + amo
        amo_sum += amo
        print 'shop.id:', shop.id, 'add to list: ', addr, amo

    if len(addrs)==0:
        # ничего не собрали
        return
    print ' '
    print ' before witdraw poccess - bal:', amo, curr.abbrev
    print ' curr dep:',curr.deposit, 'shops_dep:',curr.shops_deposit
    print addrs

    # если резервов полно то проверим на мизерность суммы
    if not reserve_small and withdraw_over > amo_sum:
        # очень маленькая сумма - сейчас не будем выплачивать продолжим накопление
        print ' witdraw so small:', amo_sum, '< txfee * %s ' % tx_over, txfee * tx_over
        return

    # теперь надо выплату сделать разовую всем за раз
    # отлько таксу здесь повыше сделаем чтобы быстро перевелось
    #{ 'txid': res, 'tx_hex': tx_hex, 'txfee': transFEE }

    #!!! вдруг база залочена - проверим это
    log(db,'withdraw', 'try for addrs:%s' % addrs)
    res = crypto_client.send_to_many(db, curr, xcurr, addrs, float(txfee), cn )
    if not res or 'txid' not in res:
        log(db, 'withdraw', 'ERROR: crypto_client.send_to_many = %s' % res)
        return
    # деньги перевелись нужно зачесть это каждому
    txid = res['txid']
    # поидее надо запомнить что было перечисление
    log(db,'withdraw', 'txid:%s for addrs:%s' % (txid, addrs))

    ### запомним по каждому магазину теперь
    ti = cn.gettransaction(txid) # тут данные соттвествуют транзакции raw так как мы ее полностью сделали?
    ## tx_json = res['tx_json']
    '''
    {u'vout': [{u'scriptPubKey':
    {u'reqSigs': 1, u'hex': u'', u'addresses': [u'15ac2ZzFBi4TTZNZ6CgVGJAVT3TgKJCgy5'], u'asm': u'OP_DUP OP_HASH160  OP_EQUALVERIFY OP_CHECKSIG', u'type': u'pubkeyhash'},
        u'value': Decimal('0.00570923'), u'n': 0},
        {u'scriptPubKey': {u'reqSigs': 1, u'hex': u'', u'addresses': [u'1JGwfDSTJEz9qPwnhn1ce7RZz2yHj72KX7'], u'asm': u'CKSIG', u'type': u'pubkeyhash'}, u'value': Decimal('0.07180738'), u'n': 1}],
        u'vin': [
            {u'sequence': 4294967295L, u'scriptSig': {u'hex': u'', u'asm': u'[ALL] '},
        u'vout': 0, u'txid': u'dc8c803a4156866dd0e15ad6f39b12ac1663902c9681c1e090531cd3c44e9456'},
        {u'sequence': 4294967295L, u'scriptSig': {u'hex': u'', u'asm': u'[ALL] '},
        u'vout': 0, u'txid': u'341b77b505e60e102ac905d0c55669512898824fbb32da105be97c26808a6165'}],
        u'txid': u'3a7128c1f5d6e46955a7e0911fcf952223820079955e0d65fcc7753958048ecd', u'version': 1, u'locktime': 0, u'size': 374}
    '''
    trans_details = ti['details']
    for v in shops_bals:
        vout = 0
        for trans in trans_details:
            addr = trans[u'address']
            if addr == v[2].addr:
                break
            vout = vout + 1
        shop = v[0]
        shop_bal = v[1]
        xwallet = v[2]
        _, bal_new = insert_shop_trans_withdraw(db, shop, curr, xcurr, shop_bal, xwallet, '{"txid": "%s", "vout": %s}' % (txid, vout))
        log(db, 'withdraw', 'shop: %s bal_new: %s txid: %s : %s' % (shop.url or shop.name, bal_new, txid, vout))

    # сохраним сразу данные!
    db.commit()
    print '  *** result curr bal:', curr.balance, 'dep:',curr.deposit, 'shops_dep:',curr.shops_deposit
