# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

#response.title = ' '.join(word.capitalize() for word in request.application.split('_'))
#response.subtitle = T('Select Services')

## read more at http://dev.w3.org/html5/markup/meta.name.html

## your http://google.com/analytics id
response.google_analytics_id = None

#########################################################################
## this is the main application menu add/remove items as required
#########################################################################
add_shop = [
            (T('С чего начать?'), True, URL('add','start')),
            (T('Создать счёт на оплату'), True, URL('bill','simple')),
            (T('Подать заявку на подключение'), True, URL('add','index')),
            (T('Платежные модули и плагины'), True, URL('default','plugins')),
            (T('Подключенные магазины'), True, URL('shops','list')),
            (T('Тестировать уведомления'), True, URL('add','note_test')),
          ]
import common
if not common.not_is_local(): add_shop.append((B(T('Принять магазин')), True, URL('add','accept')))

response.menu = [
    (CAT(H4(T('Зачем')),T('это нужно?')), URL('default','home')==URL(), URL('default','home'), []),
    (CAT(H4(T('Как')),T('начать?')), URL('add','start')==URL(), URL('add','start'), []), # add_shop ),
    (CAT(H4(T('Кто уже')),T('использует?')), URL('shops','list')==URL(), URL('shops','list')),
    (CAT(H4(T('Что мы')),T('принимаем?')), URL('default','currs')==URL(), URL('default','currs'), []),
    (CAT(H4(T('Почём')), T('обслуживаем?')), URL('shops','prices')==URL(), URL('shops','prices')),
    ]

response.menu_foot = [
    (B(T('Стартап')), True, URL('default','startup'), []),
    (T('API'), True, URL('default','api_docs'), []),
    (T('Как заработать?'), True, URL('dealers','index'), []),
    (T('Вакансии'), True, URL('default','vacs'), []),
    (T('Почему?'), True, URL('why','index'), []),
    (T('Когда?'), True, URL('news','index'), []),
    ]
