response.title=T("Подключение к международной платежной системе на основе криптовалют (мерчант биткоин)")

import db_common
import rates_lib
import recl

response.backstretch = False


# переходник для показа ссыфлкок и картинок в листингах
def download():
    return response.download(request,db)


def lll(table, f = None):
    ll = DIV()
    return ll

def plugins():
    session.forget(response)
    response.title = T('Платежные модули для разных магазинов')
    response.subtitle = T('Нажмите на иконку для загрузки файла')
    mds = []
    for r in db(db.cp_mods.id>1).select():
        url = r.fname and URL('static','plugins', args=[r.fname]) or r.discuss
        mds += CAT(
            DIV(
                DIV(
                A(IMG(_src=URL('default','download', args=['db', r.icon_h or r.icon]),
                      _width=200, _hspace=20), # _width=100 _hei_ght=70, 
                    _href=url),
                _style='width:220px;margin:10px;float:left;'),
                DIV(
                    url and (A(T('Платежный плагин для'),' ', B(r.cms), _href=url)) or '',' ',
                    T('прием биткоинов на сайте'), r.ver and ' ver.%s' % r.ver or '', BR(),
                    r.txt1 and SPAN(XML(r.txt1),  _class='help') or '',
                _style='margin:10px;float:left;display: table-cell;vertical-align: middle;'),
                FIELDSET(
                    (T('Значения параметров при регистрации магазина')),
                    LABEL(T('(используйте ctrl-A и затем ctrl-C для копирования строки из поля):')),
                    B('note_url= '), INPUT(_value=r.note_url, _readonly='true', _class='url_set'),BR(),
                    B('back_url= '), INPUT(_value=r.back_url, _readonly='true', _class='url_set'),
                    _class='oll3a', _style='clear:left;'),
                r.txt1 and LABEL(T(r.txt1)) or '',
                _class="oll3"
            ),
            BR(),
        )
    ll = CAT(
        DIV(
        H4(T('Для тех кто хочет написать свой модуль - пример модуля на языке питон:')),
        DIV(
            A(IMG(_src=URL('static','plugins/web2py_logo.png'),  _hspace=10, _w_idth=200),
                _href=URL('static','plugins/web2py-cPayModule.zip')),
            'Python - ', B('web2py'), ' - cryptoPay ver.1.02',BR(),
            _class="oll3"),
        DIV(T('Так же вы можете взять'),' ',
            A(B(T('пример экрана настроек')), _href=URL('default','plugin_set'), _class='btn oll3a'),' ',
            T('для создаваемых модулей'), _class=''
            ),
        _class="oll3"),
        BR(),
        H4(T('Платежные модули для разных магазинов')),
        CAT(mds),
        )
    return locals()
    
def vacs():
    
    response.title = T('Это все может быть и у тебя!')
    response.subtitle = T('Просто объединяйся с нами,<br>как собственник или участник.<br>Наша команда ждет тебя!<br>Нам нужен веб-дизайнер, агенты по продвижению биллинга в интернет-магазины...')
    response.backstretch = True

    ###db.vacs.truncate()
    fields = [db.vacs.job, db.vacs.expertise]
    ll = lll(db.vacs, fields)
    f = SQLFORM(db.vacs,
        keepvalues=True,
        )
    if f.process(keepvalues=True).accepted:
        response.flash = T('Спасибо, Мы с Вами свяжемся.')
        ll = lll(db.vacs, fields)
    return locals()

def startup_list():
    session.forget(response)
    response.title = T('Это все может быть и у тебя!')
    response.subtitle = T('Просто объединяйся с нами')
    response.backstretch = True
    mess = request.vars.get('mess')
    if mess:
        response.flash = mess
    ll = lll(db.startup)
    return locals()
    
def startup():
    response.title = T('Это все может быть и у тебя!')
    response.subtitle = T('Просто объединяйся с нами:<br>В этом бизнесе будущего, ты можешь выступить как инвестор-партнер или как участник проекта.<br>А можешь открыть парнерство и получать проценты от оборота со своих клиентов')
    response.backstretch = True
    
    ff = SQLFORM(db.startup,
        keepvalues=True,
        )
    if ff.process(keepvalues=True).accepted:
        # обновим
        #ll = lll(db.startup)
        redirect(URL('startup_list',vars={'mess':T('Поздравляем, Вы добавлены в список акционеров. Вам будет выслано письмо с инструкциями.')}))
        pass
    elif ff.errors:
       response.flash = T('Вы ввели ошибочные данные')
    return locals()
    
def api_docs():
    session.forget(response)
    response.title = T('')
    response.subtitle = T('')
    return dict()
    
def index():
    session.forget(response)
    #redirect(URL('to_phone','index'))# ,args=['err01']))
    redirect(URL('home'))

def home():
    session.forget(response)
    response.title = False
    response.backstretch = True

    sum = db.currs_stats.count_.sum()
    stats = db( (db.currs.used == True )
           & (db.currs.id == db.currs_stats.curr_id)).select(sum, db.currs.ALL, groupby=db.currs_stats.curr_id, orderby=~sum)
    _, reclams = recl.get(db,3)

    form = SQLFORM(db.news_descrs, fields = ['email'],
        submit_button = T('Подписаться'),
        labels = {'email': ''  },
        )

    if form.accepts(request.vars, session):
        response.flash = T('Вы подписаны')
    elif form.errors:
        response.flash = T('ОШИБКА!')

    return dict(form = form, stats=stats, reclams=reclams)

def currs():
    session.forget(response)
    response.title = False
    '''
    #rows = db(db.person).select(join=db.thing.on(db.person.id==db.thing.owner_id))
    form = SQLFORM.grid(
        #db.currs.on(db.xcurrs.curr_id==db.currs.id),
        db.currs,
        #left=db.child.on(db.child.parent==db.parent.id)
        left=db.xcurrs.on(db.xcurrs.curr_id==db.currs.id),
        #field_id=db.currs.abbrev,
        upload=URL('default','download'),
        deletable=False,
        editable=False,
        details=True,
        selectable=None,
        create=False,
        csv=False,
        links_in_grid=False,
        #upload='<download>',
        )
    '''
    '''
SELECT * 
FROM
  Person
  INNER JOIN 
  City 
    ON Person.CityId = City.Id
    '''
    
    sqlstr = \
'select icon, url, name, abbrev, desr, conf_soft, conf_hard, conf_true, block_time, txfee, currs.id \
from currs  INNER JOIN xcurrs ON currs.id = xcurrs.curr_id '
    sss = db.executesql(sqlstr)
    s = u'' #<div class="ol00">'
    curr_out, x, e = db_common.get_currs_by_abbrev(db, 'RUB')
    for rr in sss:
        #print rr
        #curr_in = db.currs[rr[10]]
        #print curr_in.abbrev
        b_rate, s_rate, avg_rate = rates_lib.get_average_rate_bsa(db, rr[10], curr_out.id)
        #print b_rate, s_rate, avg_rate
        #print rr[1]
        s += '<div class="d01"><div class="d03">'
        #s += '<div class="oll1a"><div class="oll3a">'
        # IMG(_src=URL('default','download', args=['db', vars['curr_icon']]), _width=30, _height=30, _class='lst_icon')
        s += u'<img src="%s" width=34 height=34 class="lst_icon"></img>' % URL('default','download', args=[rr[0]])
        s = s + u'<b> <a href="%s" target="_blank">%s</a> [%s]</b>: %s<br>' % rr[1:5]
        #s = s.decode('utf8')
        s = s + T('Среднее время получения статусов:').decode('utf8')
        #s = s.decode('utf8')
        s = s + u'SOFT - %s sec; HARD - %s min; TRUE - %s min.' % (rr[5]*rr[8]+10, round(rr[6]*rr[8]/60.0,2), round(rr[7]*rr[8]/60.0,2))
        s = s + T(' Комиссия сети').decode('utf8')
        s = s + ' - %s,' % rr[9]
        if b_rate:
            s = s + T(' что при курсе %s составит %s [%s]').decode('utf8') % (round(b_rate,3), round(b_rate*float(rr[9]),3), curr_out.abbrev)
        s = s + '<br>'
        s += '</div></div>'
    #s += '</div>'
    #form = SQLFORM.grid( sss )
    #print sss
    '''
    form = SQLFORM.grid(
        sss.table,
        upload=URL('download'),
        deletable=False,
        editable=False,
        details=True,
        selectable=None,
        create=False,
        csv=False,
        )
    '''
    #return locals()
    return dict(form=DIV(H4(T('Криптовалюты')), XML(s), _class='d00'))

def plugin_set():
    sel1 = '''
    <table>
        <tbody>
        <tr>
            <td><br>Если ничего не выбрано, то принимаются все криптовалюты, которые обрабатывает сервис.<br>
            Например, Вы можете выбрать только BTC и LTC и задать параметр conv_curr="Без конвертации" - тогда пользователь при оплате Вашего счета сможет оплачитвать только биткоинами и лайткоинами, которые без конвертации будут поступать Вам на балланс.
            </td>

              <td><div class="scrollbox">
                                            <div class="even">
                          <input type="checkbox" name="curr_in[]" value="BTC" che_cked="chec-ked">
                          BTC                      </div>
                                            <div class="odd">
                          <input type="checkbox" name="curr_in[]" value="LTC" chec_ked="che-cked">
                          LTC                      </div>
                                            <div class="even">
                          <input type="checkbox" name="curr_in[]" value="NVC" check_ed="chec-ked">
                          NVC                      </div>
                                            <div class="odd">
                          <input type="checkbox" name="curr_in[]" value="CLR" checke_d="chec-ked">
                          CLR                      </div>
                  </div></td>

          </tr>
    </tbody>
    </table>
    '''
    cls1 = 'oll3a' # 'oll4'
    cls2 = 'oll3'
    fiats = OPTGROUP('RUB', 'USD', 'EUR',  _label='fiat currencies')
    crypts = OPTGROUP('BTC', 'LTC', 'NVC', 'CLR',  _label='crypto currencies')
    f = FORM(LABEL(T('Пример интерфейса для настройки модуля оплат')),
        DIV(FIELDSET(T('shop ID'),
            INPUT(_name='expire', _class='right', _value='14qZ3c9WGGBZrftMUhDTnrQMzwafYwNiLt'),BR(),
            T('Задайте номер магазина: '),
            LABEL(T('(Вы можете не регистрироваться на сервисе cryptoPay.in,'),BR(),
            T('тогда вместо номера магазина задайте адрес своего кошелька криптовалюты.)')),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('&curr='),
             DIV(T('Выберите валюту для создания счетов оплаты: '),
                SELECT(OPTION(T('По валюте магазина (заказа)'), _value='None'),
                       crypts, fiats, _name='curr', _class='right'),
                ),
                LABEL(T('"По валюте магазина (заказа)" - значит сам магазин задает валюту.'),BR(),
                    T('Более подробно о валютах - '), A(T('на сайте сервиса'), _target='_blank',
                                    _href=(URL('default','currs')))),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('&conv_curr='),
             DIV(T('Задайте валюту в которую будут конвертироваться входящие платежи: '),
                SELECT(OPTION(T('Без конвертации'), _value='not_convert'), crypts, fiats, _name='conv_curr', _class='right'),
                LABEL(T('Именно в ней Вы будете получать выплаты с сервиса'), BR(),
                    T('Если выбрано "без конвертации" то входящая криптовалюта будет начисляться магазину в том виде в котром пришла.')),
                ),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('&curr_in='),
             DIV(T('Задайте список криптовалют, которые разрешены для оплаты счетов: '),BR(),
                XML(sel1),
                LABEL(T('Более подробно о валютах - '), A(T('на сайте сервиса'), _target='_blank',
                                    _href=(URL('default','currs')))),
                ),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('&public'),
             DIV(T('Задайте открытость счетов: '),
                SELECT(
                       OPTION(T('Закрыто всем'), _value='None'),
                       OPTION(T('Открыто всем'), _value='public'),
                       OPTION(T('По значению в заказе'), _value='as_order'),
                       _name='secret', _class='right'),
                ),
                LABEL(T('По умолчанию - "закрыто всем", то есть доступ к инфоормации по счетам'),BR(),
                    T('возможен только с секретнным ключом,'),BR(),
                    T('который передается Вашему магазину для каждого созданного счета.')),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('&expire='),
                INPUT(_name='expire', _class='right'),BR(),
                T('Задайте продолжительность жизни счета в минутах:'),
                LABEL(T('По умолчанию - 180, максимально - сутки.'),BR(),
                    T('Если счет становится просроченным, то все поступившие на него платежи возвращаются')),
                #),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('&note_on='),
             DIV(T('Задайте статус не ранее которого присылать уведомления с сервиса: '),
                SELECT(OPTION(T('не задан'), _value='None'),
                       OPTION(T('HARD'), _value='HARD'),
                       OPTION(T('CLOSED'), _value='CLOSED'),
                       _name='note_on', _class='right'),
                ),
                LABEL(T('По умолчанию - уведомлять при появлении всех статусов у счета.'),BR(),
                    T('Более подробно о выборе статуса '), A(T('в описании API'), _target='_blank',
_href='https://docs.google.com/document/d/1hrAocgSS0ZuBvgLr6oS_dKDFhdQwL12qTJCBTaykzSg/edit#heading=h.7ul7vsllz816')),
            _class=cls1),
            _class=cls2),
#        HR(),
        DIV(FIELDSET(T('...'),
             DIV(T('Список дополнительных параметров:'),
                TEXTAREA(_name='cPay_pars', _class='right'),
                LABEL(T('Более подробно о параметрах '), A(T('в описании API'), _target='_blank',
_href='https://docs.google.com/document/d/1hrAocgSS0ZuBvgLr6oS_dKDFhdQwL12qTJCBTaykzSg/edit#heading=h.iii87ixk2pjt')),
                ),
            _class=cls1),
            _class=cls2),
        BR(),
        A(T('Назад к платежным модулям'), _href=URL('plugins'), _class='btn '+cls1),
        )
    return locals()
