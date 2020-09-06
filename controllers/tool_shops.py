# coding: utf8
import common

# запустим сразу защиту от внешних вызов
#if request.function not in ['list', 'download'] and common.not_is_local(): raise HTTP(200, T('ERROR'))
if not request.is_local: raise HTTP(200, T('ERROR'))

import datetime
import json
from gluon.contrib import simplejson as js

import db_common
import db_client


def log(l2, mess):
    m = 'shops_lib'
    print m, mess
    db.logs.insert(label123456789 = m, label1234567890=l2, mess='%s' % mess)
def log_commit(db, l2, mess='>'):
    log(db, l2, mess)
    db.commit()

def stats():
    shop_id = request.args(0)
    if not shop_id: return 'shop_orders/shop_id/[1 - skip DB stats - only WALLET stats]'
    shop = db.shops[ shop_id ]
    if not shop: return 'shop not found'
    import crypto_client
    h = CAT(
            H3(shop.name),
        )
    for curr in db(db.currs.used).select():
        curr_id = curr.id
        xcurr = db(db.xcurrs.curr_id == curr_id).select().first()
        if not xcurr: continue
        xcurr_id = xcurr.id

        abbrev = curr.abbrev
        h += H3(abbrev)
        total = draws_trans = total_trans_order = total_shops_draws = 0
        cnt_orders = cnt_filled = cnt_closed = 0
        if request.args(0) != '1':
            for order in db((db.shop_orders.shop_id == shop_id)
                        & (db.shop_orders.curr_id == curr_id)
                        ).select():
                cnt_orders += 1
                payed_true = order.payed_true
                if order.price:
                    if order.status == 'CLOSED':
                        total += payed_true
                        cnt_closed += 1
                        #closed.append('%s - %s' % (order.created_on, payed_true))
                        ## returned auto - автоучтены возвраты тут в цене закрытия if
                else:
                    if payed_true:
                        total += payed_true
                        cnt_filled += 1
                        #filled.append('%s - %s' % (order.created_on, payed_true))

                # транзакции входящие в ордера
                for tr in db(
                    (db.shops_trans.shop_order_id == order.id)
                    & (db.shops_trans.curr_id == curr_id)).select():
                    total_trans_order += tr.amo

            h += H3('in db.shops_trans.amo: ', total_trans_order)

            for tr_out in db(
                (db.shops_draws.shop_id == shop_id)
                & (db.shops_draws.curr_id == curr_id)).select():
                total_shops_draws += tr_out.amo
            h += H3('total_shops_draws: ', total_shops_draws)

            for out in db(
                (db.bills_draws_trans.curr_id == curr_id)
                & (db.shop_orders.shop_id == shop_id)
                & (db.bills_draws_trans.shop_order_id == db.shop_orders.id)
                ).select():
                draws_trans += out.bills_draws_trans.amo
            h += H3('TOTAL by ORDERS: ', total, ', DRAWED by trans: ', draws_trans, '  = ', total - draws_trans)

            shop_bal = db((db.shops_balances.shop_id == shop_id )
                & (db.shops_balances.curr_id == curr_id )).select().first()
            if shop_bal:
                h += H3('shops_balances_kept= ',shop_bal.kept,', shops_balances_bal= ', shop_bal.bal)

            payouted = 0
            for xwall in db((db.shops_xwallets.shop_id == shop_id )
                    & (db.shops_xwallets.xcurr_id == xcurr_id )).select():
                payouted += xwall.payouted
            if payouted:
                h += H3('shops_xwallets.payouted %s' % payouted)

            h += DIV('total orders: ', cnt_orders, ', closed: ', cnt_closed, ', filled: ', cnt_filled)

        h + H3('*** XWALLET ***')

        to_conf = xcurr.conf_true
        conn = crypto_client.connect(curr, xcurr)
        print 'connected CONN for get stats by wallets'
        in_addr_summ = in_addr_summ_trans = pay_ins_summ = pay_ins_summ_ret = 0
        ## по всем адресам все счетов для данного магазина по данной валюте
        for rec in db(
                        (db.shop_order_addrs.xcurr_id == xcurr_id)
                        & (db.shop_order_addrs.shop_order_id == db.shop_orders.id)
                        & (db.shop_orders.shop_id == shop_id)).select():
            addr = rec.shop_order_addrs.addr
            acct = conn.getaccount(addr)
            trans = conn.listtransactions(acct) ## только входящие дает (( и только ля своих адресов
            for tr in trans:
                if tr['category'] == 'receive':
                    in_addr_summ_trans += tr['amount']
                else:
                    in_addr_summ_trans -= tr['amount']
            ##print trans
            in_vol = conn.getreceivedbyaddress(addr, to_conf) ## выдает только приходы на наши адреса - чуже и и уходы не дает
            if in_vol == 0: continue
            #print addr, in_vol
            in_addr_summ += in_vol

            # теперь пов сем входящим трнзакциям на этот адрес
            for pay_in in db(db.pay_ins.shop_order_addr_id == rec.shop_order_addrs.id).select():
                pay_ins_summ_ret -= (pay_in.amo_ret or 0)
                pay_ins_summ += pay_in.amount

        h += H4('total by order address incomes from wallet: ', in_addr_summ, ' == by  getreceivedbyaddress:', in_addr_summ_trans)
        h += H4('total by order address pay_ins.amount %s - amo_ret %s = %s ' % (pay_ins_summ, pay_ins_summ_ret, pay_ins_summ - pay_ins_summ_ret))
        ## теперь надо посчитать сколько было возвратов
        ##
        ##
        out_addr_withdraw = 0
        for rec in db((db.shops_xwallets.shop_id == shop_id)
                      & (db.shops_xwallets.xcurr_id == xcurr_id)).select():
            addr = rec.addr
            acc = conn.getaccount(addr)
            vol = 0 ##conn.listtransactions(acc, 1)
            if in_vol == 0: continue
            print addr, vol
            out_addr_withdraw += vol
            h += H4('withdravwd to address: ', addr, ' ', vol)
        h += H3('TOTAL withdrawed to shop: ', out_addr_withdraw)

        ##



    return dict( h = h)


def list():
    h = CAT()
    for r in db(db.shops).select():

        h += DIV(
            A(r.id, _href=URL('appadmin','update', args=['db','shops',r.id]), _target='_blank'),'. ',
            '--' if r.not_used else '',
            B(r.uses),' ',
            A(r.simple_curr and (r.url or '???') or r.name, _href=r.url, _target='_blank') if r.url else r.name,
            ' ', r.email,' ', r.descr,
            _class='row')

    return dict(h=h)

def resum_currs_deposit():
    import crypto_client
    sum = 0
    for curr in db(db.currs).select():
        sum1 = db.shops_balances.bal.sum()
        sum2 = db(db.shops_balances.curr_id==curr.id).select(sum1).first()[sum1]
        #print  curr.abbrev, summ2
        curr.update_record(shops_deposit = sum2)
        xcurr = db(db.xcurrs.curr_id==curr.id).select().first()
        if xcurr:
            try:
                cn = crypto_client.connect(curr, xcurr)
                #print cn
                if cn:
                    bal = cn.getbalance()
                    print curr.abbev, bal
            except:
                pass


#############################################
def show(r):
    print r
def edit_bals():
    res=[]
    '''
    res.append( SQLFORM(ShBals, fields=['shop_id'], formstyle='divs',
              )
        )
    if res[0].process().accepted:
        res.append( SQLFORM.grid(ShBals, formstyle='divs') )
        pass
    '''
    res.append( SQLFORM.grid(ShBals,
         selectable = [('Change ballance', lambda r: show(r)),('button label2',lambda r:  r)],
         formstyle='divs') )
    rid = request.args(0)
    if rid:
        res[0].buttons.append(BUTTON())
    return locals()

# шлем рассылку в скрытых копиях
def send_email_to_descr(to_addrs, subj, mess=None, rec=None, templ=None):
    from gluon.tools import Mail
    mail = Mail()
    #mail.settings.server = 'smtp.yandex.ru' #:25'
    mail.settings.server = 'smtp.sendgrid.net'
    mail.settings.sender = 'support@cryptoPay.in'
    #mail.settings.login = 'support@7pay.in:huliuli'
    mail.settings.login = 'azure_90ebc94457b0e6a1c4c920993753f5a6@azure.com:7xirv1rc'
    mess = mess or ''
    if rec and templ:
        context = dict( rec = rec )
        #mess = response.render('add_shop_mail.html', context)
        mess = response.render(templ, context)
    #print mess
    #to_addrs = ['kentrt@yandex.ru','icreator@mail.ru']
    mail.send(
          #to=to_addrs[0],
          to=to_addrs,
          #cc=len(to_addrs)>1 and to_addrs[1:] or None, - как спам коипии делает (
          #bcc=len(to_addrs)>1 and to_addrs[1:] or None,
          subject=subj,
          message=mess)

def mail_to_clients1():
    subj = 'Новости от биллинга cryptoPay.in - 2'
    mess = '''
    Здравствуйте!

    Появился модуль (плагин) биллинга поатежей для магазинов, созданных на PrestaShop http://cryptopay.in/shop/default/plugins
    Подключение свободное и бесплатное. Просьба тех кто хочет установить на свой сайт этот плагин, откликнуться.

    С Уважением, Ермолаев Дмитрий
    '''
    mess = mess + '%s.' % A('cryptoPay.in', _href='http://cryptoPay.in')
    #send_email_to_descr('icreator@mail.ru',subj,mess)
    return mess
    to_addrs = []
    for r in db(db.startup).select():
        to_addrs.append(r.email)
        if len( to_addrs ) > 5:
            send_email_to_descr(to_addrs, subj, mess)
            to_addrs = []
    if len(to_addrs)>0: send_email_to_descr(to_addrs, subj, mess)

def mail_to_polza1():
    subj = 'cryptoPay.in - СТАРТАП: сообщение 7'
    return 'stopped'
    mess = '''
    Здравствуйте!

    И так нас зарегистрировали. Название выбрано нейтральное что бы не привлекать внимание на начальных этапах и при регистрации:
    Инновационное Постребительское Общество "Польза"

    Открыт расчетный счет в СберБанке, теперь можно вносить взносы.

    Запущен сайт ipo-polza.ru
    На нем можно регистрироваться и оплачивать вступительные взносы

    Созданы программы:
    1. "получи 500 рублей приведя своих друзей"
    2. вклад 37,77% за 777 дней (или 18% годовых)

    Для получения новостей, подключайтесь в социальной сети google+ к пользователю ipo.polza@gmail.com


    С Уважением, Дмитрий Ермолаев
    http://ipo-polza.ru
'''
    #mess = mess + '%s.' % A('cryptoPay.in Стартап', _href='http://cryptopay.in/shop/default/startup')
    #send_email_to_descr('icreator@mail.ru',subj,mess)
    to_addrs = []
    if True:
        for r in db(db.startup).select():
            to_addrs.append(r.email)
            if len( to_addrs ) > 5:
                send_email_to_descr(to_addrs, subj, mess)
                to_addrs = []
        if len (to_addrs) > 0: send_email_to_descr(to_addrs, subj, mess)
    else:
        send_email_to_descr(['icreator@mail.ru'], subj, mess)

    return 'sended'

def withdraw():
    if len(request.args) == 0:
        mess = 'len(request.args)==0 - [BTC]'
        return mess
    import db_common
    import shops_lib
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    conn = crypto_client.connect(curr,xcurr)
    shops_lib.withdraw(db, curr, xcurr, conn, curr.withdraw_over) # тут может крипты не хватить так как обмен нужен еще

# test all ophranet transactions
def ophrans():
    if len(request.args) == 0:
        mess = 'len(request.args)==0 - [BTC]'
        return mess
    import db_common
    import crypto_client
    curr, xcurr, e = db_common.get_currs_by_abbrev(db,request.args[0])
    conn = crypto_client.connect(curr,xcurr)
    h = CAT()
    cnt = 0
    for r in db((db.shop_order_addrs.xcurr_id == xcurr.id)
                & (db.pay_ins.shop_order_addr_id == db.shop_order_addrs.id)).select():
        cnt += 1
        txid = r.pay_ins.txid
        #print txid
        if len(txid) > 60 and len(txid) < 70 and r.pay_ins.status !='SOFT':
            res = conn.gettransaction(txid) # выдает только для кошелька
            if res:
                conf = res.get('confirmations')
                #print conf
                if conf > 2:
                    continue
            h += P(BEAUTIFY(r.pay_ins))
            h += P(BEAUTIFY(res))
            h += HR()
    return dict(h=CAT(H3('counter:', cnt),h))

def update_payouts_todo():
    currs = []
    for curr in db(db.currs).select():
        currs.append(curr.id)

    for shop in db(db.shops).select():
        summs = {}
        for bill in db(db.shop_orders.shop_id == shop.id).select():
            for addr in db(db.shop_order_addrs.shop_order_id == bill.id).select():
                pass

    return 'TODO'

def update_payouts():
    shops = db(db.shops).select()
    for xcurr in db(db.xcurrs).select():
        curr = db.currs[ xcurr.curr_id ]
        for shop in shops:
            amo = 0
            xwall_exist = False
            for xwall in db((db.shops_xwallets.shop_id == shop.id)
                            & (db.shops_xwallets.xcurr_id == xcurr.id)).select():
                amo += (xwall.payouted or 0)
                xwall_exist = True
            if xwall_exist:
                bal = db((db.shops_balances.shop_id == shop.id)
                     & (db.shops_balances.curr_id == curr.id)).select().first()
                if not bal:
                    print 'added for:', shop.name, curr.name, amo
                    rec_id = db.shops_balances.insert(shop_id = shop.id, curr_id = curr.id, bal = 0, payouted = amo)
                else:
                    print 'updated for:', shop.name, curr.name, amo
                    bal.update_record(payouted = amo)
    return 'OK'

def tx_json():
    _id = request.args(0)
    if _id:
        rec = db.xcurrs_raw_trans[ _id ]
        if not rec: return 'not found in xcurrs_raw_trans'
        #print rec.tx_hex
        tx_json = js.loads(rec.tx_hex.decode('utf8'))
    else:
        tx_json = {
       u'vout': [
            {u'scriptPubKey':
                {u'reqSigs': 1, u'hex': u'',
                 u'addresses': [u'15ac2ZzFBi4TTZNZ6CgVGJAVT3TgKJCgy5'],
                 u'asm': u'OIG', u'type': u'pubkeyhash'},
             u'value': Decimal('0.00570923'), u'n': 0},
            {u'scriptPubKey':
                {u'reqSigs': 1, u'hex': u'',
                 u'addresses': [u'1JGwfDSTJEz9qPwnhn1ce7RZz2yHj72KX7'],
                 u'asm': u'', u'type': u'pubkeyhash'},
             u'value': Decimal('0.07180738'), u'n': 1}
            ],
       u'vin': [{u'sequence': 4294967295L, u'scriptSig': {u'hex': u'', u'asm': u'[ALL] '},
                    u'vout': 0, u'txid': u'dc8c803a4156866dd0e15ad6f39b12ac1663902c9681c1e090531cd3c44e9456'},
                {u'sequence': 4294967295L, u'scriptSig': {u'hex': u'', u'asm': u'[ALL] '},
                    u'vout': 0, u'txid': u'341b77b505e60e102ac905d0c55669512898824fbb32da105be97c26808a6165'}],
       u'txid': u'3a7128c1f5d6e46955a7e0911fcf952223820079955e0d65fcc7753958048ecd', u'version': 1, u'locktime': 0, u'size': 374}
    txid = tx_json['txid']
    addrs = {}
    for vout in tx_json['vout']:
        addr = vout['scriptPubKey']['addresses'][0]
        amo = vout['value']
        n = vout['n']
        print n, addr, amo

    return BEAUTIFY(tx_json)
