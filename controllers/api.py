# coding: utf8

import time

# разрешить использовать виды generic.*
# в локальном режиме все - в том числе и .html - который дает доступ к статистике
# не в локальном только .json и .xml
##response.generic_patterns = ['*'] if request.is_local else ['*.json','*.xml']
# там в генерик-файле стоит проверка на локальный вызов - так что можно разрешить
response.generic_patterns = ['*']

# здесь вызовы могут быть в 3-х форматах;
# .html
# .json
# .xml
# у каждого надо создать свовй вид со своим расшириением задать response.generic_patterns
# http://127.0.0.1:8000/shop2/api/get_reserves.json

import db_common
import crypto_client

def register_simple():
    session.forget(response)
    import time
    time.sleep(1)
    addr = request.args(0)
    if not addr or len(addr) < 30:
        time.sleep(3)
        return 'len(addr) < 30'
    from db_common import get_currs_by_addr
    curr, xcurr, _ = get_currs_by_addr(db, addr)
    if not curr:
        time.sleep(3)
        return 'addr[1] not valid'
    
    from crypto_client import is_not_valid_addr, connect
    cc = connect(curr, xcurr)
    if not cc:
        return curr.abbrev + ' not connected, try again!'
    if is_not_valid_addr(cc, addr):
        time.sleep(3)
        return 'addr is not valid for [' + curr.abbrev + ']'

    url = request.vars['shop_url']
    if url and url == 'http://localhost':
        time.sleep(2)
        return 'http://localhost !'
    
    shop = db(db.shops.name==addr).select().first()
    if shop:
        time.sleep(2)
        return 'that addr is registered already'

    # жестко зададим валюту конвертации
    from shops_lib import make_simple_shop
    shop = make_simple_shop(db, addr, request.vars, True, curr, xcurr)
    if not shop:
        time.sleep(1)
        return 'error'
    
    return 'success'
    
    
# проверить статус заказа
# для продолженных заказв параметр status =
# # http://127.0.0.1:8000/shop/api/check_note.json/278
def check_note():
    session.forget(response)
    import time
    time.sleep(3)
    import orders_lib
    err, _, _, shop_order = orders_lib.check_args(db, request)
    if err or not shop_order:
        return err or 'biil not exist'
    shop = db.shops[shop_order.shop_id]
    if not shop.url: return 'shop url empty'
    import shops_lib
    url_path = shops_lib.try_make_note_url2(db, shop, shop_order, None)
    res = url_path and shops_lib.notify_one_url(db, shop, shop_order)
    return { 'result_note_url': shop.url + (url_path or 'None'), 'response_status': res and res.status, 'response_text': res and res.read() }


########################################################################
########################################################################
def get_reserves():
    session.forget(response)

    bals = dict()
    for curr in db(db.currs).select():
        if not curr.used: continue
        b = db_common.get_reserve( curr )
        bals[curr.abbrev] = float(b)

    return bals
def get_shops_reserves():
    time.sleep(1)
    bals = dict()
    from applications.shop.modules.db_common import get_shops_reserve
    for curr in db(db.currs).select():
        if not curr.used: continue
        b = get_shops_reserve( curr )
        bals[curr.abbrev] = float(b)

    return bals


# api/tx_info.json/BTC/ee4ddc65d5e3bf133922cbdd9d616f89fc9b6ed11abbe9a040dac60eb260df23
# api/tx_info.html/BTC/ee4ddc65d5e3bf133922cbdd9d616f89fc9b6ed11abbe9a040dac60eb260df23
def tx_info():
    session.forget(response)

    txid = request.args(1)
    if not txid:
        return {'error':"need txid: /tx_info.json/[curr]/[txid]"}
    curr_abbrev = request.args(0)
    import db_common
    curr,xcurr,e = db_common.get_currs_by_abbrev(db, curr_abbrev)
    if not xcurr:
        return {"error": "invalid curr:  /tx_info.json/[curr]/[txid]"}
    import crypto_client
    conn = crypto_client.connect(curr, xcurr)
    if not conn:
        return {"error": "not connected to wallet"}
    res = crypto_client.get_tx_info(conn, txid, request.vars)
    return res

# api/tx_senders/BTC/ee4ddc65d5e3bf133922cbdd9d616f89fc9b6ed11abbe9a040dac60eb260df23
def tx_senders():
    session.forget(response)
    txid = request.args(1)
    if not txid:
        #raise HTTP(501, {"error": "empty pars"})
        return {'error':"need txid: /tx_senders.json/[curr]/[txid]"}
    curr_abbrev = request.args(0)
    import db_common
    curr,xcurr,e = db_common.get_currs_by_abbrev(db, curr_abbrev)
    if not xcurr:
        return {"error": "invalid curr"}
    import crypto_client
    conn = crypto_client.connect(curr, xcurr)
    if not conn:
        return {"error": "not connected to wallet"}
    res = dict(result=crypto_client.sender_addrs(conn, txid))
    return res


# http://127.0.0.1:8000/shop/api/validate_addr.json/14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt
def validate_addr():
    session.forget(response)
    addr = len(request.args)>0 and request.args[0] or request.vars.get('addr')
    if not addr:
        return {'error':"need addr: /validate_addr.json/[addr]"}
    curr, xcurr, _ = db_common.get_currs_by_addr(db, addr)
    if not xcurr:
        return {"error": "invalid"}
    conn = crypto_client.connect(curr, xcurr)
    if not conn:
        return {"error": "not connected to wallet [%s]" % curr.abbrev}
    valid = conn.validateaddress(addr)
    #print valid
    if not valid or 'isvalid' in valid and not valid['isvalid']:
        if 'ismine' in valid and valid['ismine']:
            return dict( result = curr.abbrev + " - is mine" )
        return {"error": "invalid for [%s]" % curr.abbrev}
    return dict( result = curr.abbrev)

# а может нельзя это делать? так как можно со стороны мешать получать уведомления
#def stop_note(shop_order_id):
#    session.forget(response)
#    for tr in db(db.shops_trans.shop_order_id==shop_order_id).select():
#        note = db(db.shops_notifies.shops_tran_id==tr.id).select().first()
#        if note: del db.shops_notifies[note.id]


##https://7pay.in/ipay/to_shop/get_balances/[shop_id]
# http://127.0.0.1:8000/shop/api/get_balances.json/2
# http://127.0.0.1:8000/shop/api/get_balances.html/2
def get_balances():
    time.sleep(1)
    session.forget(response)
    if not request.args or len(request.args)==0:
        return { "error": "args is empty" }

    shop_id = request.args[0]
    if not shop_id:
        time.sleep(5)
        return { "error": "shop_id empty"}

    if len(shop_id)>30:
        shop = db(db.shops.name == shop_id).select().first()
        shop_id = shop and shop.id
        if not shop_id:
            time.sleep(5)
            return { "error": "shop [%s] not found" % request.args[0]}
    else:
        try:
            shop_id = int(shop_id)
        except:
            time.sleep(5)
            return { "error": "shop_id invalid"}

    if not db.shops[shop_id]:
        time.sleep(5)
        return { "error": "shop [%s] not found" % request.args[0]}
    
    bals = {}
    for rec in db(db.shops_balances.shop_id == shop_id).select():
        curr = db.currs[rec.curr_id]
        if curr:
            bals[curr.abbrev] = round(float(rec.bal),9)
    return bals

# api/rates/BTC
def rates():
    if len(request.args) == 0:
        mess = 'ERROR: - use api/rates/BTC'
        return mess
    curr_in = db(db.currs.abbrev==request.args[0]).select().first()
    if not curr_in: return 'curr not found'

    import rates_lib
    best_rates = rates_lib.get_best_rates(db, curr_in)
    res = {}
    for v in best_rates:
        if v == curr_in.id: continue
        res[db.currs[v].abbrev] = best_rates[v]
    return res

## если какая то транзакция была пропущена - в АНСПЕНТ не попала так как была уже израсходована
## то проверить - была ли она обработана и если нет то обработать
## check_txid/BTC/4c921268aa59a182f7268c211d9facdce5445d2306638b398cf1e7d8880a9266
##
def check_txid():
    from cp_api import check_txid
    return check_txid(db, request)
