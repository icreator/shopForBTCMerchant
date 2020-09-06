# -*- coding: utf-8 -*-

routes_in = (
    # очень много запросов идут на эту иконку почемуто. ответ сервера 400(код ошибки) 50(миллисек?)
    (r'/favicon.ico', r'/bs3b/static/images/favicon.png'),
    (r'/favicon.png', r'/bs3b/static/images/favicon.png'),
    (r'/robots.txt', r'/bs3b/static/robots.txt'),
    (r'/bs3b_dvlp/$anything', r'/bs3b_dvlp/$anything'),
    #(r'/shop/$anything', r'/shop/$anything'),
    #(r'/bs3b/bill/show_update/$anything', r'/bs3b/bill/show_update/$anything'),
    #(r'/bill/show_update/$anything', r'/bs3b/bill/show_update/$anything'), # для ускорения
    #(r'/bs3b/$anything', r'/bs3b/$anything'),
    #(r'/$anything', r'/bs3b/default/index/$anything'), # /$anything - для передачи кодировки языка!
    #(r'/default/$anything', r'/bs3b/default/index/$anything'),
    #(r'/shop/$anything', r'/shop/$anything'),
    #(r'/bets/favicon.ico', r'/bs3b/static/images/favicon.png'),
    #(r'/bets/favicon.png', r'/bs3b/static/images/favicon.png'),
    #(r'/bets/robots.txt', r'/bs3b/static/robots.txt'),
        # на форуме https://www.prestashop.com/forums/topic/347034-bitcoin-payments-free-module-merchant/
        # дана ссылка старая такая:
        # http://lite.cash/bs3b/static/modules/PrestaShop.1.5.6.0_LITEcash_2_6.zip
        # и чтобы не было ошибки делаем:
    #(r'/BETS/$anything', r'/bets/$anything'), # перенаправляем на ставки
    #(r'/bets/$anything', r'/bets/$anything'),
    #(r'/bets', r'/bets'),
    (r'/', r'/bs3b/default/index/'),
    (r'/index/$anything', r'/bs3b/default/index/$anything'),
    (r'/index', r'/bs3b/default/index'),
    #(r'/download', r'/bs3b/default/download'),
    (r'/join/$anything', r'/bs3b/default/index/join/$anything'),
    (r'/join', r'/bs3b/default/index/join'),
    (r'/shop_add/$anything', r'/default/shop_add/$anything'),
    (r'/shop_add', r'/bs3b/default/shop_add'),
    (r'/support/$anything', r'/default/support/$anything'),
    (r'/support', r'/bs3b/default/support'),
    (r'/bs3b/index', r'/bs3b/default/index'),
    (r'/bs3b', r'/bs3b/default/index'),
    (r'/$anything', r'/bs3b/$anything'),
    )

routes_out = [
    #(x, y) for (y, x) in routes_in
    (r'/bs3b/static/images/favicon.png', r'/favicon.ico'),
    (r'/bs3b/static/images/favicon.png', r'/favicon.png'),
    (r'/bs3b/static/robots.txt', r'/robots.txt'),
    (r'/bs3b/$anything', r'/$anything')
    ]
#routes_out.insert(0, )
#routes_out.insert(0, (r'/bs3b', r'/'))
