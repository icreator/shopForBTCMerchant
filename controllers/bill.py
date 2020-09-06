# coding: utf8

# TODO
# сделать повтоную высылку уведомлений если счет закрыт - кнопку на форме - вдруг их сбросил кто-то

import logging
logger = logging.getLogger("web2py.app.shop")
logger.setLevel(logging.DEBUG)

import common
import db_common
import db_client
import orders_lib
import rates_lib
import cp_api

response.subtitle=' '

def download():
    return response.download(request,db)

#################################################
def make_shops_name(shop):
    return  shop.name or shop.url
def make_shops_url(shop):
    return  shop.url or shop.name and 'http://%s' % shop.name or None
def make_back_url(shop, so):
    sh_url =  make_shops_url(shop)
    if sh_url:
        empty_url = '?'
        if shop.back_url:
            sh_url += '/' + shop.back_url
            empty_url = ''
        if so.back_url:
            sh_url += '/' + so.back_url
            empty_url = ''
        sh_url += empty_url + ('%s' % so.order_id)
        return sh_url


#######################################
def try_note():
    err, shop_order = cp_api.check_ars(db, request)
    if err:
        logger.warn( err )
        return { 'error': err }
    import shops_lib
    shop = db.shops[shop_order.shop_id]
    return shops_lib.try_make_note_url(db, shop, shop_order)


#################################################
# ТУТ нельзя менять количество из-за order_curr -
# так как иначе поменется КУРС в созданном заказе_на_обмен
# и потом поменяется вход по неверному курсу
#
def pay():
    session.forget(response)

    #print request.args
    #print request.vars

    err, shop_order = cp_api.check_ars(db, request)
    if err:
        # ошибка или секрет сработал
        logger.warn( err )
        raise HTTP(500, BEAUTIFY(err))

    if session.lang:
        #T.set_current_languages(lang)
        T.force(session.lang)
    
    # это заказ просроченный или закрытый
    closed = shop_order and shop_order.status in orders_lib.UNUSED_STATUSES
    if closed: raise HTTP(501, '{ "error": "order status is %s - not for pay" }' % shop_order.status )

    shop_order_id = shop_order.id
    order_id = shop_order.order_id
    shop = db.shops[shop_order.shop_id]
    curr = db.currs[shop_order.curr_id]

    # возможно тут сам пользователь задал сумму для продолженного платежа
    volume_out = float(request.vars.get('volume') or 0)
    price = shop_order.price
    payed = shop_order.payed_soft + shop_order.payed_hard + shop_order.payed_true
    if price and price >0:
        volume_out = common.rnd_8(price - payed)
        if volume_out < 0: volume_out = 0

    xcurr_in_val = request.vars['xcurr_in']
    # если нет валюты - назад
    if not xcurr_in_val or volume_out == 0:
        ou = '%s' % shop_order_id
        if shop_order.secr: ou += '.%s' % shop_order.secr
        redirect(URL('show', args=[ou]))

    if not shop_order.email:
        shop_order.update_record( email = request.vars['email'] )
    response.vars = {}
    response.vars['shop_id'] = shop.id
    response.vars['volume_out'] = volume_out
    response.vars['shop_order'] = shop_order
    response.vars['curr'] = curr.abbrev
    response.vars['curr_icon'] = curr.icon
    #print xcurr_in_val
    response.vars['xcurr_in'] = xcurr_in_val
    response.vars['price'] = shop_order.price

    curr_in, xcurr_in, e = db_common.get_currs_by_abbrev(db, xcurr_in_val)
    response.vars['curr_in_icon'] = curr_in.icon

    # найдем адресс кошелека для данной крипты и нашего заказа
    x_label = db_client.make_x_acc(shop, order_id, curr.abbrev)
    shop_order_addr = db_client.get_shop_order_addr_for_xcurr(db, shop_order_id, curr_in, xcurr_in, x_label)
    if not shop_order_addr:
        response.title=T("ОШИБКА")
        #session.vars = { 'shop_order_id': shop_order_id }
        return dict(uri= T(' связь с кошельком ') + curr_in.name + T(' прервана.'), addr=None)

    img = None
    shop_name = make_shops_name(shop)
    shops_url = make_shops_url(shop)
    response.vars['s_url'] = XML( A(T('тут'), _href=shops_url, _target="_blank"))
    response.vars['back_url'] = make_back_url( shop, shop_order )
    if shop.icon:
        img = IMG(_src=URL('default','download', args=['db', shop.icon]), _width=130)
    if shop.icon_url:
        img = IMG(_src=shops_url + '/' + shop.icon_url, _width=130)
    response.vars['shop_url'] = XML( A(img or shop_name, _href=shops_url, _target="_blank"))

    # используем быстрый поиск курса по формуле со степенью на количество входа
    # только надо найти кол-во входа от выхода
    best_rate = None
    pr_b, pr_s, pr_avg = rates_lib.get_average_rate_bsa(db, curr_in.id, curr.id, None)
    #print pr_b, pr_s, pr_avg
    if pr_avg:
        # примерное кол-во найдем
        vol_in = volume_out / pr_b
        #print vol_in, curr_in.abbrev, '-->', volume_out, curr.abbrev
        # точный курс возьмем
        amo_out, _, best_rate = rates_lib.get_rate(db, curr_in, curr, vol_in)

    #print best_rate, pair
    if not best_rate:
        response.title=T("ОШИБКА")
        return dict(uri='[' + curr_in.name + '] -> [' + curr.name + ']' + T(' - лучшая цена не доступна.'), addr=None, shop_id=shop.id)

    volume_in = volume_out/best_rate
    # теперь добавим погрешность курса
    volume_in = common.rnd_8(rates_lib.add_limit( volume_in, xcurr_in.txfee * 3))
    # пересчет курса с погрешностью к курсу
    best_rate = volume_out/volume_in
    response.vars['best_rate']=best_rate
    response.vars['best_rate_rev']=1.0/best_rate
    response.vars['volume_in'] = volume_in

    # если есть цена у счета то под него 1 раз создадим заказ на обмен
    # для заказов без цены - не делаем заказов на курс обмена
    if volume_out:
        # посмотрим - создавлся ли заказ на конвертацию?
        rate_order = db(db.rate_orders.ref_id == shop_order_addr.id).select().first()
        if not rate_order:
            # make new rate_order
            id = db.rate_orders.insert(
                ref_id = shop_order_addr.id,
                volume_in = Decimal(volume_in),
                volume_out = Decimal(volume_out),
                )
            # теперь стек добавим, который будем удалять потом
            db.rate_orders_stack.insert( ref_id = id )


    uri = common.uri_make( curr_in.name2, shop_order_addr.addr, {'amount':common.rnd_8(volume_in), 'label': db_client.make_x_acc_label(shop, order_id, curr.abbrev)}, T('ОПЛАТИТЬ'))

    return dict(uri=uri, addr=shop_order_addr.addr, shop_id=shop.id)

################################################################
def show_headers():
    session.forget(response)
    if session.lang:
        #T.set_current_languages(session.lang)
        T.force(session.lang)
        pass
    so_id = request.args and request.args[0]
    so = so_id and db.shop_orders[so_id]
    if not so: raise HTTP(200, T('Счет не найден') )

    response.vars = {}
    st = so.status
    st2 = ''
    if False: pass
    elif st == 'NEW': st2 = T('счет создан, платежи еще не поступали')
    elif st == 'FILL': st2 = T('счет пополняется...')
    elif st == 'SOFT': st2 = T('счет оплачен полностью, но хотя бы один платеж еще имеет статуc SOFT')
    elif st == 'HARD': st2 = T('счет оплачен полностью, но хотя бы один платеж еще имеет статуc HARD')
    elif st == 'CLOSED': st2 = T('счет оплачен полностью')
    elif st == 'EXPIRED': st2 = T('счет просрочен, все платежи возвращаются')
    else: st2 = T('счет не действителен')
    st = T('Статус счета: %s (%s)') % (st, st2)
    response.vars['status']  = st
    payed = so.payed_soft + so.payed_hard + so.payed_true
    if so.price:
        if so.price > payed:
            to_pay = so.price - payed
            response.vars['to_pay_label'] = T('Осталось оплатить')
            response.vars['to_pay'] = float(to_pay)
        else:
            pass
    else:
        response.vars['to_pay_label'] = T('Оплатить')
        response.vars['to_pay'] = 1.0
    return dict()

# http://127.0.0.1:8000/shop2/order/show/1?order=w23a1&curr=BTC&price=0.002&curr_in=BTC&curr_in=LTC
# args: shop_order_id - or None
# # http://127.0.0.1:8000/shop2/order/show/1

def show():
    
    # redirect to new web-face
    redirect(URL('bs3b','bill','show', args=request.args, vars = request.vars, host='lite.cash'))

    err, shop_order = cp_api.check_ars(db, request)
    if err:
        # ошибка или секрет сработал
        logger.warn( err )
        raise HTTP(500, BEAUTIFY(err))

    #print shop_order
    # если задан язык представления то переведем
    lang = request.vars.get('lang') or shop_order.lang
    if lang:
        #print 'force lang:', lang
        #T.force(lang)
        #T.set_current_languages(lang, lang)
        session.lang = lang
        #T.set_current_languages(lang)
    if session.lang:
        T.force(session.lang)

    response.title=T(" ")
    img = None
    shop = db.shops[shop_order.shop_id]
    curr = db.currs[shop_order.curr_id]
    shop_name = make_shops_name(shop)
    if shop.icon:
        img = IMG(_src=URL('default','download', args=['db', shop.icon]), _width=124)
    #elif shop.img: img = XML('<img src="%s">' % shop.img)

    shops_url = make_shops_url(shop)
    #print shops_url
    #response.title=XML(XML(T("Параметры платежа для ") + '<BR>') + XML( img or '' ) + ' ' +\
    #        XML( A(shop_name, _href=shops_url, _target="_blank")))

    price = shop_order.price # берем из заказа
    response.vars = {}
    response.vars['s_url'] = XML( A(T('тут'), _href=shops_url, _target="_blank"))
    response.vars['back_url'] = make_back_url( shop, shop_order )
    if shop.icon:
        img = IMG(_src=URL('default','download', args=['db', shop.icon]), _width=130)
    if shop.icon_url:
        img = IMG(_src=shops_url + '/' + shop.icon_url, _width=130)
    response.vars['shop_url'] = XML( A(img or shop_name, _href=shops_url, _target="_blank"))

    response.vars['curr_out'] = curr.abbrev
    response.vars['curr_icon'] = curr.icon
    response.vars['shop_order'] = shop_order
    response.vars['price'] = price
    closed = shop_order and (shop_order.status in orders_lib.UNUSED_STATUSES or shop_order.status == 'HARD')
    if closed:
        response.vars['closed'] = shop_order.status
        return dict()

    payed = shop_order.payed_soft + shop_order.payed_hard + shop_order.payed_true
    to_pay = price and (price - payed) or Decimal(request.vars.get('vol') or shop_order.vol_default or 1)

    if to_pay <0: to_pay = Decimal(0)
    response.vars['shop_text'] = shop.show_text
    # для первоначальной загрузки страници и устанвки курсов
    response.vars['volume_out'] = to_pay

    dealer = None
    # запретим магазинам с ларками работать CLR
    # и от них список крипты если есть то только с нею - response.vars.get('curr_in')
    # тут более точный курс получаем но медленно по базе
    # а если просрочен платеж то там кукрс будет вычислен быстро по базе и степени
    # тут берем именно ВАЛЮТУ_ЗАКАЗА чтобды курс показывался и для валюты конвертации
    xpairs = closed and {} or db_client.get_xcurrs_for_shop(db, 0, curr, shop, shop_order.curr_in_stop, shop_order.curr_in)

    if not shop_order.price and shop_order.exchanging and curr:
        # для обменных операций - показать резервы и не более резерва дать оплатить
        response.vars['reserve'] = db_common.get_reserve( curr )
        i = 0
        for xp in xpairs:
            if xp['abbrev'] == curr.abbrev:
                break
            i = i + 1
        xpairs.pop(i)

    return dict(xcurrs_list=xpairs)

def simple_check():
    mess = ''
    so = secr = None
    err, shop_order = cp_api.check_ars(db, request)
    if err:
        # ошибка или секрет сработал
        logger.warn( err )
        raise HTTP(500, BEAUTIFY(err))

    id = request.args(0)
    uuu = URL('bill', 'show', args=[id], host=True, scheme=True)
    chk = URL('api_bill', 'check', args=[id], host=True, scheme=True)

    from gluon.tools import fetch
    from gluon.contrib import simplejson as json
    resp = fetch(URL('api_bill', 'check.json', args=[id], host=True, scheme=True))
    resp = json.loads( resp )

    return locals()

def simple():
    uuu = resp = None
    response.subtitle=T('Заполните  информацию о заказе:')
    f = FORM('',
             LABEL(T('Ваш биткоин-адрес для выплат')), INPUT(_name='x_addr', _value='14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt', requires=IS_NOT_EMPTY()),
             LABEL(T('Ссылка на магазин "http://my_shop.com"')), INPUT(_name='shop_url'),
             LABEL(T('Ссылка на иконку магазина "images/logo1.jpg"')), INPUT(_name='icon_url'),
             LABEL(T('Ссылка для уведомлений магазина "modules/cp_resp?"')), INPUT(_name='note_url'),
             LABEL(T('Ссылка возврата в магазин "orders_show?order="')), INPUT(_name='back_url'),
             HR(),
             LABEL(T('Номер заказа в вашем магазине')), INPUT(_name='order', requires=IS_NOT_EMPTY()),
             LABEL(T('Валюта заказа (USD, RUB, BTC, LTC)')), INPUT(_name='curr', _value='BTC'),
             LABEL(T('Цена заказа')), INPUT(_name='price'),
             LABEL(T('Время жизни заказа в минутах (по умолчанию = 180мин)')), INPUT(_name='expired'),
             LABEL(T('Валюта конвертации (в которую конвертируется поступающая криптовалюта)')), INPUT(_name='conv_curr'),
             LABEL(T('Язык текстов (en, ru)')), INPUT(_name='lang'),

             LABEL(T('Другие параметры (синтаксис как параметры в строке URL (&mess=HI+ALL&name=my_shop...)')),
             INPUT(_name='pars1', _value='&public&mess=Hi+TESTER'),
             BR(),INPUT(_name='pars2'),
             LABEL(T('')), INPUT(_type='submit', _value=T('Создать'))
             #LABEL(T('')), INPUT(_name='order'),
        )
    if f.accepts(request.vars, session):
        #response.flash = T('new record inserted')
        # берем ИД новой записи
        addr = f.vars.pop('x_addr')
        pars1 = f.vars.pop('pars1')
        pars2 = f.vars.pop('pars2')
        for (k,v) in f.vars.copy().iteritems():
            if not v:
                f.vars.pop(k)
        # print f.vars
        uuu = URL('api_bill', 'make', args=[addr], vars=f.vars, host=True, scheme=True)
        uuu += pars1 + pars2
        from gluon.tools import fetch
        resp = fetch(uuu)
        #print resp
        #uuu += '<br>'
        #resp += '<br>'
        redirect( URL('bill', 'simple_check', args=[resp] ))
    return locals()
