# coding: utf8

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
# http://127.0.0.1:8000/shop/api_bill/info.json/10

################################################################################
# проверить статус заказа
# для продолженных заказв параметр status =
# http://127.0.0.1:8000/shop/api2/check.json/147?status=HARD
def check():
    session.forget(response)
    from cp_api import check
    return check(db, request)

# http://127.0.0.1:8000/shop/api2/info.json/188?status=HARD
# &get_addrs &all_fields
# http://127.0.0.1:8000/shop/api2/info/147?get_addrs&all_fields
def info():
    session.forget(response)
    from cp_api import info
    return info(db, request)

def make():
    session.forget(response)

    from cp_api import make
    err, bill_id = make(db, request)
    #print err, bill_id
    if err:
        raise HTTP(501, '%s' % err)

    return bill_id
