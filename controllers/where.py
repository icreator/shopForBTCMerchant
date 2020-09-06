# coding: utf8

import datetime
import json

import common
import db_common
import where
import recl

response.title=T("Просмотр платежей сервиса")
response.logo2 = IMG(_src=URL('static','images/7P-302.png'), _width=156)

# если нет адреса значит для всего заказа выводим только суммы
def for_addr():
    session.forget(response)
    if session.lang:
        #T.set_current_languages(session.lang)
        T.force(session.lang)
        pass

    #TT = { 'Всего оплачено':  T('Всего оплачено')}
    #print TT
    addr = request.vars and request.vars.get('addr')
    shop_order_id = request.vars and request.vars.get('shop_order')
    pays = where.found_pay_ins_addr(T, db, addr, shop_order_id)
    return dict(pays=pays, mess = T('Поиск поступивших платежей...'))
    
# попробовать что-либо вида
def index():
    common.page_stats(db, response['view'])

    addr = request.post_vars and ('addr' in request.post_vars) and request.post_vars['addr'] or None
    addr = addr or request.get_vars and ('addr' in request.get_vars) and request.get_vars['addr'] or None
    #if not addr: return dict(pays=None)

    _, reclams = recl.get(db,3)
    payed_month = None
    MAX = None
    payed = price = order_id = amo_rest_url = None

    pays = where.found_buys(db, addr)
    if len(pays)>0:
        return dict(reclams=reclams, pays=pays, payed_month=payed_month, MAX=MAX, addr=addr, payed=payed, price=price, order_id=order_id, amo_rest_url=amo_rest_url )

    if addr and len(addr)>20:
        deal_acc_addr = db(db.deal_acc_addrs.addr == addr).select().first()
        deal_acc = deal_acc_addr and db(db.deal_accs.id == deal_acc_addr.deal_acc_id).select().first()
        if deal_acc:
            payed_month = deal_acc.payed_month
            deal = db(db.deals.id == deal_acc.deal_id).select().first()
            MAX = deal.MAX or 777
            payed = deal_acc.payed or Decimal(0)
            price = deal_acc.price
            order_id = deal_acc.acc
            client = db(db.clients.deal_id == deal.id).select().first()
            if client:
                curr_out = db.currs[deal_acc.curr_id]
                vvv = {'order':order_id, 'curr_out':curr_out.abbrev}
                
                if price and price >0 and price - payed > 0:
                    # еще надо доплатить
                    vvv['sum'] = price - payed
                amo_rest_url=A(T('Доплатить'), _href=URL('to_shop','index', args=[client.id],
                    vars=vvv))


    pays=[]
    # все еще не подтвержденные
    for xcurr in db(db.xcurrs).select():
        #print xcurr
        curr = db.currs[xcurr.curr_id]
        #print curr
        if not curr or not curr.used: continue
        where.found_unconfirmed(db, curr, xcurr, addr, pays)


    where.found_pay_ins(db, None, None, addr, pays, price and (price - (payed or Decimal(0)) ))
    #print pays
    if len(pays)==0: pays = T('Входов не найдено...')

    return dict(reclams=reclams, pays=pays, payed_month=payed_month, MAX=MAX, addr=addr, payed=payed, price=price, order_id=order_id, amo_rest_url=amo_rest_url )
