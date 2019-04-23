from flask import Flask, request
import logging
import json
from geo import get_geo_info, get_distance
import requests

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

sessionStorage = {}
sessionStorage['city'] = None
sessionStorage['work'] = 0
sessionStorage['ll'] = ''
sessionStorage['organization'] = ''
sessionStorage['search'] = "https://search-maps.yandex.ru/v1/"
sessionStorage['api'] = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"
sessionStorage['address'] = ''


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Request: %r', response)
    return json.dumps(response)


def handle_dialog(res, req):
    try:
        user_id = req['session']['user_id']
        # Обработка команды "Помощь" в зависимости от того, на какой стадии пользователь
        if 'помощь' in req['request']['nlu']['tokens']:
            if sessionStorage[user_id]['first_name'] is None:
                res['response']['text'] = 'Представьтесь, пожалуйста.'
            elif sessionStorage['city'] is None:
                first_name = sessionStorage[user_id]['first_name']
                res['response']['text'] = f'{first_name.title()}, введите город, ' \
                                          f'в котором хотите искать организацию.'
            elif sessionStorage['work'] == 0:
                first_name = sessionStorage[user_id]['first_name']
                res['response']['text'] = '{}, используйте "Поиск [Адрес/Название организации]",' \
                                          ' чтобы найти здание или компанию, ближайшую к центру' \
                                          ' города {} или к дому, если он указан("Дом [Адрес]",' \
                                          ' чтобы установить точку на дом для поиска расстояния' \
                                          '.)'.format(first_name, sessionStorage['city'])
                res['response']['buttons'] = [
                    {
                        'title': 'Покажи адрес дома',
                        'hide': True
                    }, {
                        'title': 'Удали дом',
                        'hide': True
                    }
                ]
            elif sessionStorage['work'] == 1:
                first_name = sessionStorage[user_id]['first_name']
                res['response'][
                    'text'] = f'{first_name.title()}, используйте кнопки для ' \
                              f'получения информации об организации.'
                res['response']['buttons'] = [
                    {
                        'title': 'Адрес',
                        'hide': True
                    }, {
                        'title': 'Телефон',
                        'hide': True
                    }, {
                        'title': 'Время',
                        'hide': True
                    }, {
                        'title': 'Индекс',
                        'hide': True
                    }, {
                        'title': 'Расстояние от дома',
                        'hide': True
                    }, {
                        'title': 'Покажи на карте',
                        'hide': True
                    }, {
                        'title': 'Обратно',
                        'hide': True
                    }, {
                        'title': 'Помощь',
                        'hide': False
                    }
                ]
            return
        # Показываем пользователю данные, если включен режим работы
        if sessionStorage['work'] == 1:
            print(sessionStorage['organization'])
            try:
                name = sessionStorage['organization']['properties']['CompanyMetaData']['name']
            except:
                name = '"Компания"'
            if 'время' in req['request']['nlu']['tokens']:
                try:
                    peremennaya = \
                        sessionStorage[user_id]['organization']["properties"]["CompanyMetaData"]["Hours"]["text"]
                    res['response']['text'] = 'Компания {} работает {}'.format(name, peremennaya)
                except:
                    res['response']['text'] = 'Я не смогла получить часы работы компании {}'.format(name)
            elif 'телефон' in req['request']['nlu']['tokens']:
                try:
                    peremennaya = \
                        sessionStorage['organization']['properties']['CompanyMetaData']['Phones'][0]['formatted']
                    res['response']['text'] = 'Телефон компании {} - {}'.format(name, peremennaya)
                except:
                    res['response']['text'] = 'Я не смогла получить телефон компании {}'.format(name)
            elif 'адрес' in req['request']['nlu']['tokens']:
                try:
                    peremennaya = sessionStorage['organization']['properties']['CompanyMetaData']['address']
                    res['response']['text'] = '{} находится по адресу {}'.format(name, peremennaya)
                except:
                    res['response']['text'] = 'Я не смогла получить адрес компании {}'.format(name)
            elif 'индекс' in req['request']['nlu']['tokens']:
                try:
                    peremennaya = sessionStorage['organization']['properties']['CompanyMetaData']['postalCode']
                    res['response']['text'] = 'Индекс компании {} - {}'.format(name, peremennaya)
                except:
                    res['response']['text'] = 'Я не смогла получить индекс компании {}'.format(name)
            elif 'покажи на карте' == req['request']['original_utterance'].lower():
                res['response']['text'] = 'Лови ссылку! https://yandex.ru/maps/?mode=search&text={}'.format(
                    '+'.join(sessionStorage['organization']['properties']['CompanyMetaData']['address'].split()))
            elif 'обратно' in req['request']['nlu']['tokens']:
                sessionStorage['work'] = 0
                res['response']['text'] = 'Введи "Поиск [Адрес/Название организации]", чтобы на' \
                                          'йти здание или компанию, ближайшую к центру города {}' \
                                          ' или к дому, если он указан("Дом [Адрес]", чтобы' \
                                          ' установить точку на дом для поиска ' \
                                          'расстояния.)'.format(sessionStorage['city'])
                res['response']['buttons'] = [
                    {
                        'title': 'Помощь',
                        'hide': False
                    }, {
                        'title': 'Покажи адрес дома',
                        'hide': True
                    }, {
                        'title': 'Удали дом',
                        'hide': True
                    }, {
                        'title': 'Обратно',
                        'hide': True
                    }
                ]
                sessionStorage['company'] = ''
                sessionStorage['organization'] = None
                return
            elif 'расстояние' in req['request']['nlu']['tokens']:
                if sessionStorage['address']:
                    print(sessionStorage['ll'], sessionStorage['archive'])
                    dist = get_distance([float(x) for x in sessionStorage['ll'].split(',')],
                                        [float(x) for x in sessionStorage['archive'].split(',')])
                    res['response']['text'] = 'От твоего дома до организации примерно {} метра'.format(dist)
                else:
                    res['response'][
                        'text'] = 'Для подсчёта расстояния мне нужен адрес дома! ' \
                                  'Нажми кнопку "Обратно", потом укажи адрес дома в' \
                                  ' формате "Дом [Адрес]" и возвращайся.'
            else:
                res['response'][
                    'text'] = 'Не поняла тебя. Я могу показать только то, что написано на' \
                              ' кнопках, используй их!'
            res['response']['buttons'] = [
                {
                    'title': 'Адрес',
                    'hide': True
                }, {
                    'title': 'Телефон',
                    'hide': True
                }, {
                    'title': 'Время',
                    'hide': True
                }, {
                    'title': 'Индекс',
                    'hide': True
                }, {
                    'title': 'Расстояние от дома',
                    'hide': True
                }, {
                    'title': 'Покажи на карте',
                    "url": 'https://yandex.ru/maps/?mode=search&text={}'.format(
                        '+'.join(sessionStorage['organization']['properties']['CompanyMetaData']['address'].split())),
                    'hide': True
                }, {
                    'title': 'Обратно',
                    'hide': True
                }
            ]
            return
        else:
            # Знакомимся, если пользователь только начал общение
            if req['session']['new']:
                res['response']['text'] = 'Привет! Давай познакомимся! Как тебя зовут?'
                res['response']['buttons'] = [
                    {
                        'title': 'Помощь',
                        'hide': False
                    }
                ]
                sessionStorage[user_id] = {
                    'first_name': None,
                    'game_started': False
                }
                return
            # Определяем город, если уже познакомились
            if sessionStorage[user_id]['first_name'] is None and sessionStorage['city'] is None:
                first_name = get_first_name(req)
                if first_name is None:
                    res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': False
                        }
                    ]
                else:
                    sessionStorage[user_id]['first_name'] = first_name
                    res['response'][
                        'text'] = f'{first_name.title()}, напиши мне любой город России и ' \
                                  f'сможешь узнать о нём информацию.'
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': False
                        }
                    ]
            # Определяем город, если пользователь представился или решил его поменять
            else:
                first_name = sessionStorage[user_id]['first_name']
                if sessionStorage['city'] is None:
                    city = get_cities(req)
                    if len(city) == 0:
                        res['response'][
                            'text'] = f'Я не поняла названия ни одного города, ' \
                                      f'{first_name.title()}! Попробуй ещё раз.'
                        res['response']['buttons'] = [
                            {
                                'title': 'Помощь',
                                'hide': False
                            }
                        ]
                        sessionStorage['city'] = None
                    elif len(city) == 1:
                        country = get_geo_info(city[0], 'country')
                        if country != 'Россия':
                            res['response'][
                                'text'] = f'Извини, {first_name.title()}, но этот город' \
                                          f' находится не в России! Введи другой.'
                            res['response']['buttons'] = [
                                {
                                    'title': 'Помощь',
                                    'hide': False
                                }
                            ]
                            sessionStorage['city'] = None
                        else:
                            res['response']['text'] = 'Введи "Поиск [Адрес/Название организации]' \
                                                      '", чтобы найти здание или компанию, ' \
                                                      'ближайшую к центру города или к дому, ' \
                                                      'если он указан("Дом [Адрес]", чтобы ' \
                                                      'установить точку на дом для поиска' \
                                                      ' расстояния.)'
                            geocoder_request = "http://geocode-maps.yandex.ru/1.x/" \
                                               "?geocode={}&format=json".format(city)
                            response = requests.get(geocoder_request)
                            json_response = response.json()
                            toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                            toponym_coodrinates = toponym["Point"]["pos"]
                            sessionStorage['ll'] = ','.join(toponym_coodrinates.split())
                            sessionStorage['archive'] = ','.join(toponym_coodrinates.split())
                            sessionStorage['city'] = city[0]
                            sessionStorage['address'] = ''
                            res['response']['buttons'] = [
                                {
                                    'title': 'Помощь',
                                    'hide': False
                                }, {
                                    'title': 'Покажи адрес дома',
                                    'hide': True
                                }, {
                                    'title': 'Удали дом',
                                    'hide': True
                                }, {
                                    'title': 'Обратно',
                                    'hide': True
                                }
                            ]
                    else:
                        sessionStorage['city'] = None
                        res['response']['text'] = f'Слишком много городов, ' \
                                                  f'{first_name.title()}! Выбери только 1!'
                        res['response']['buttons'] = [
                            {
                                'title': 'Помощь',
                                'hide': False
                            }
                        ]
                else:
                    # Удаляем данные о городе, если пользователь дал команду
                    if 'обратно' in req['request']['nlu']['tokens']:
                        sessionStorage['city'] = None
                        sessionStorage['address'] = None
                        res['response'][
                            'text'] = f'{first_name.title()}, напиши мне любой город ' \
                                      f'России и сможешь узнать о нём информацию.'
                        res['response']['buttons'] = [
                            {
                                'title': 'Помощь',
                                'hide': False
                            }
                        ]
                    # Устанавливаем точку на дом, увидев ключевое слово
                    elif 'дом' in req['request']['nlu']['tokens'][0]:
                        # Запрещаем, если дом уже есть
                        if sessionStorage['address']:
                            res['response']['text'] = f'{first_name.title()}, ' \
                                                      f'сначала выселись из предыдущего!'
                            res['response']['buttons'] = [
                                {
                                    'title': 'Помощь',
                                    'hide': False
                                }, {
                                    'title': 'Покажи адрес дома',
                                    'hide': True
                                }, {
                                    'title': 'Удали дом',
                                    'hide': True
                                }, {
                                    'title': 'Обратно',
                                    'hide': True
                                }
                            ]
                        # Не запрещаем, если дома нет
                        else:
                            f = True
                            for entity in req['request']['nlu']['entities']:
                                if entity['type'] == 'YANDEX.GEO':
                                    if 'house_number' in entity['value'].keys():
                                        f = False
                                        sessionStorage['address'] = ' '.join(req['request']['nlu']['tokens'][1:])
                                        geocoder_request = "http://geocode-maps.yandex.ru/1.x/?geocode={}&format=json" \
                                            .format(
                                            '+'.join([x.strip(',') for x in req['request']['nlu']['tokens'][1:]]))
                                        sessionStorage['address'] = ' '.join(req['request']['nlu']['tokens'][1:])
                                        response = requests.get(geocoder_request)
                                        json_response = response.json()
                                        toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0][
                                            "GeoObject"]
                                        toponym_coodrinates = toponym["Point"]["pos"]
                                        sessionStorage['ll'] = ','.join(toponym_coodrinates.split())
                                        res['response']['text'] = 'Дом по адресу {} добавлен!'.format(
                                            sessionStorage['address'])
                                        res['response']['buttons'] = [
                                            {
                                                'title': 'Помощь',
                                                'hide': False
                                            }, {
                                                'title': 'Покажи адрес дома',
                                                'hide': True
                                            }, {
                                                'title': 'Удали дом',
                                                'hide': True
                                            }, {
                                                'title': 'Обратно',
                                                'hide': True
                                            }
                                        ]
                            if f:
                                res['response'][
                                    'text'] = f'Я не нашла ни одного дома, ' \
                                              f'{first_name.title()}! Попробуй ещё раз.'
                                res['response']['buttons'] = [
                                    {
                                        'title': 'Помощь',
                                        'hide': False
                                    }
                                ]
                    # Печатаем адрес дома, если он указан
                    elif 'покажи адрес дома' == req['request']['original_utterance'].lower():
                        if sessionStorage['address']:
                            res['response']['text'] = 'Твой дом находится по адресу {}'.format(
                                sessionStorage['address'])
                        else:
                            res['response']['text'] = f'{first_name.title()}, ' \
                                                      f'у тебя нет дома! ノ( º _ ºノ)'
                        res['response']['buttons'] = [
                            {
                                'title': 'Помощь',
                                'hide': False
                            }, {
                                'title': 'Удали дом',
                                'hide': True
                            }, {
                                'title': 'Обратно',
                                'hide': True
                            }
                        ]
                    # Удаляем дом, если он есть
                    elif 'удали дом' == req['request']['original_utterance'].lower():
                        if sessionStorage['address']:
                            res['response']['text'] = 'Твой дом по адресу {}' \
                                                      ' удалён!'.format(sessionStorage['address'])
                            sessionStorage['address'] = ''
                            sessionStorage['ll'] = sessionStorage['archive']
                        else:
                            res['response']['text'] = f'{first_name.title()}, ' \
                                                      f'у тебя нет дома! ノ( º _ ºノ)'
                        res['response']['buttons'] = [
                            {
                                'title': 'Помощь',
                                'hide': False
                            }
                        ]
                    # Ищем организацию, если увидели ключевое слово
                    elif 'поиск' in req['request']['nlu']['tokens']:
                        sessionStorage['company'] = '+'.join(req['request']['nlu']['tokens'][1:])
                        search_params = {
                            "apikey": sessionStorage['api'],
                            "text": sessionStorage['company'],
                            "lang": "ru_RU",
                            "ll": sessionStorage['ll'],
                            "type": "biz"
                        }
                        response = requests.get(sessionStorage['search'], params=search_params)
                        json_response = response.json()
                        sessionStorage['organization'] = json_response["features"][0]
                        if sessionStorage['organization']:
                            sessionStorage['work'] = 1
                            res['response'][
                                'text'] = f'Организация успешно найдена, ' \
                                          f'{first_name.title()}. Что подсказать?'
                            res['response']['buttons'] = [
                                {
                                    'title': 'Адрес',
                                    'hide': True
                                }, {
                                    'title': 'Телефон',
                                    'hide': True
                                }, {
                                    'title': 'Время',
                                    'hide': True
                                }, {
                                    'title': 'Индекс',
                                    'hide': True
                                }, {
                                    'title': 'Расстояние от дома',
                                    'hide': True
                                }, {
                                    'title': 'Покажи на карте',
                                    "url": 'https://yandex.ru/maps/?mode=search&text={}'.format('+'.join(
                                        sessionStorage['organization']['properties']['CompanyMetaData'][
                                            'name'].split())),
                                    'hide': True
                                }, {
                                    'title': 'Обратно',
                                    'hide': True
                                }, {
                                    'title': 'Помощь',
                                    'hide': False
                                }
                            ]
                        else:
                            res['response'][
                                'text'] = f'Я не смогла найти организацию, ' \
                                          f'{first_name.title()}. Попробуй ещё раз.'
                    else:
                        res['response']['text'] = f'{first_name.title()}, произошла ' \
                                                  f'непредвиденная ошибка. Возможно, вы ' \
                                                  f'пытаетесь меня сломать, а так делать ' \
                                                  f'заперещено. Общайтесь хорошо или я обижусь!'
                        res['response']['buttons'] = [
                            {
                                'title': 'Помощь',
                                'hide': False
                            }
                        ]
    except:
        res['response'][
            'text'] = 'Если вы видите эту ошибку, то вы конкретно так' \
                      ' сломали Алису, подорожник вряд ли поможет. ' \
                      'Напишите vk.com/drmattsuu'


def get_cities(req):
    cities = []
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            if 'city' in entity['value'].keys():
                cities.append(entity['value']['city'])
    return cities


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()