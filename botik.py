import telebot
import os
import urllib.request
import requests
import re
import csv
import zipfile
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from string import punctuation
import pymorphy2
import json
from collections import Counter
morph = pymorphy2.MorphAnalyzer()


def delete_files(path):  # чтобы удалять существующие файлы, т к имена всегда одни, чтоб код не рушился
    os.remove(path) 

    
def file_open(filename, types='t'):  # читаем файл
    if types == 't':
        with open(filename, encoding='utf-8') as f:
            text = f.read()
            return text
    elif types == 'c':
        with open(filename, 'r', encoding='utf-8') as csv_file:  # читаем и создем словарь с кешем
            csv_table = csv.reader(csv_file)
            csv_dict = {}
            for row in csv_table:
                csv_dict[row[0]] = row[1]
            return csv_dict
    else:
        with open(filename, 'r') as file_json:
            json_read = json.load(file_json)
            return json_read


def text_tokens(text):  # список токенов
    punctuation_lst = [_ for _ in punctuation] + ['—', '«', '»', '...']
    tokens = [token.lower() for token in word_tokenize(text) if token not in punctuation_lst]  # без пунктуации, но со стоп-словами
    return tokens


def text_lemmas(tokens):  # список лемм
    lemmas_lst = []
    cache_dict = file_open('cache.csv', types='c')
    new_token = {}  # токены, которых нет в кеше, чтобы потом дописать
    for token in tokens:
        if token in cache_dict:
            norm_form = cache_dict[token]
        else:
            token_pr = morph.parse(token)[0]  # возвращает список некоторых характеристики, из клоторых 0 - нужная
            norm_form = token_pr.normal_form  # вытаскивает нужную характеристику - начальную форму
            new_token[token] = norm_form
        lemmas_lst.append(norm_form)
    with open('cache.csv', "a", encoding='utf-8', newline='') as cache:
        writer = csv.writer(cache)
        for token in new_token:
            token_list = [token, new_token[token]]
            writer.writerow(token_list)
    return lemmas_lst


def stop_filter(lemmas):
    stop_words = stopwords.words('russian')
    lemmas_ws = [lemma for lemma in lemmas if lemma not in stop_words]  # без стоп-слов
    return lemmas_ws


def freq(lemmas_lst):
    freq_dict = Counter(lemmas_lst)  # создаем частотный словарь
    freq_parts = {'NOUN': Counter({}), 'INFN': Counter({}), 'ADJF': Counter({})}  # заготовка под словарь с нужными частями речи
    special_dict = file_open('special.csv', types='c')
    for lemma in freq_dict:
        lem_part = ''
        detected = False
        if lemma in special_dict:
            lem_part = special_dict[lemma]
            detected = True
        lem_pr = morph.parse(lemma)
        num_var = 0
        while not detected and num_var < len(lem_pr):  # части речи, берем ту, для которой лемма совпадает с нормальной формой
            variant = lem_pr[num_var]
            if lemma == variant.normal_form:
                lem_part = str(variant.tag).split(',')[0]
                detected = True  # выходим из цикла, как только определили часть речи
            num_var += 1
        if lem_part in freq_parts:
            freq_parts[lem_part][lemma] = freq_dict[lemma]  # переносим данные из частотного словаря в созданный словарь
    return freq_dict, freq_parts


def compare(part_dict, numb=5):  # numb - количество наиболее популярных слов, которые надо вывести
    dict_comm = {}
    dict_rus = file_open('freq_lya_dict.json', types='j')
    for part in part_dict:
        dict_comm[part] = Counter({})
        for word, count in part_dict[part].most_common(numb):  # соотносим пвторой словарь с нужными словами
            if word in dict_rus[part]:
                dict_comm[part][word] = [count, dict_rus[part][word]]
            else:
                dict_comm[part][word] = [count, 'not found']
    return dict_comm


def water_diversity(word_amount, word_ws_amount, word_unique_amount):
    stopwords_amount = word_amount - word_ws_amount  # кол-во стоп-слов в тексте
    water = round(stopwords_amount / word_amount * 100, 2)  # водность в процентах, до двух знаков
    lexical_diversity = round(word_unique_amount / word_amount * 100, 2)  # разнообразие в процентах, до двух знаков
    return water, lexical_diversity


def lastindex():  # считаем последний индекс частотного словаря
    if os.path.exists('result1.txt'):
        with open('result1.txt', 'r', encoding='utf-8') as f: 
            lines = f.readlines()
            lastindex = len(lines)
        return lastindex


def slovar(last):  # Выводим словарь до запрошенного индекса
    freqs = ''
    if os.path.exists('result1.txt'):
        with open('result1.txt', 'r', encoding='utf-8') as f: 
            lines = f.readlines()
            index = 0
            while index < last:
                freqs += lines[index]
                index += 1
    else:
        freqs = 'Сначала дайте фанфик на обследование, а потом словарь просите'
    return freqs


def work_with_txt(text):
    tokens_lst = text_tokens(text)  # токенизация текста
    lemmas_lst = text_lemmas(tokens_lst)  # лемматизация токенов
    lemmas_clean = stop_filter(lemmas_lst)  # удаляем стоп-слова
    freq_dict, freq_parts = freq(lemmas_clean)  # частостный словарь: общий и по частям речи
    dict_comm = compare(freq_parts)
    water, lexical_diversity = water_diversity(len(lemmas_lst), len(lemmas_clean), len(freq_dict))
    messag = 'Уровень водности текста:\t' + str(water) + '%\n'
    messag += 'Коэффициент лексического разнообразия:\t' + str(lexical_diversity) + '%\n'
    messag += '\n\n'
    for key, item in freq_dict.most_common(20):
        messag += key + '  :  ' + str(item) + '\n'
    for part in dict_comm:
        messag += '\n\n' + part + '\n'
        for word, inf in dict_comm[part].most_common():
            messag += word + '  :  ' + str(inf[0]) + '\t' + str(inf[1]) + '\n'      
    if os.path.exists('result1.txt'):
        delete_files('result1.txt')
    with open('result1.txt', 'w', encoding='utf-8') as f:  # чтобы потом отдельно выдавать словарь
        for key, item in freq_dict.most_common():
            s = key + '  :  ' + str(item) + '\n'
            f.write(s)
    return messag
 
      
def find_fanfic(linkname):  # Выкачиваем из сайта ссылку на скачивание, скачиваем и извлекаем
    response = requests.head(linkname)
    if str(response) == '<Response [200]>':
        f = urllib.request.urlopen(linkname).read()
        pattern = '/download.php?fic='
        index = str(f).find(pattern)
        if index == -1:
            messag = 'Не могу его скачать'
        else:
            pattern = r'\/download\.php\?fic=\d+&format='
            reallink = 'https://fanfics.me' + re.search(pattern, str(f)).group()+'txt'
            with open('fanfic.zip', "wb") as f:
                ufr = requests.get(reallink) 
                f.write(ufr.content)
            z = zipfile.ZipFile('fanfic.zip', 'r')
            z.extractall()
            filename = z.namelist()[0]
            text = file_open(filename)
            messag = work_with_txt(text)
            delete_files('fanfic.zip')
            delete_files(filename)
    else:
        messag = "Нерабочая ссылка, отправь, пожалуйста, другую"
    return messag
               

bot = telebot.TeleBot('1202811556:AAHQh1uQsjHEtbtVL6Z3gOB5X_vQDCDW8eI');


@bot.message_handler(commands=['start'])  # чтобы начать с команды старт
def start_message(message):
    bot.send_message(message.chat.id, 'Привет, я бот, который сделает частотный словарь вашего фанфика и сравнит его с \
    литературной нормой и что-нибудь скажет. Кидайте мне ссылки на фанфики из fanfics.me. В изначальном выводе будет \
    коэффициент водности текста, коэффициент лексического разнообразия, частотный словарь общий, по частям речи \
    (кол-во слова в тексте + место слово в списке Ляшевской по этой части речи')
    bot.send_message(message.chat.id, 'Напиши help чтобы узнать, что надо делать')


@bot.message_handler(content_types=['text'])
def send_text(message):
    texxt = message.text
    if texxt.lower() == 'help':
        bot.send_message(message.chat.id, 'Скинь ссылку, начинающуюся на https://fanfics.me/, я посчитаю кое-что. \
        И только потом скажи "словарь", чтобы я отправил тебе часть частотного словаря')
    elif texxt.startswith('https://fanfics.me/'):
        bot.send_message(message.chat.id, 'Начинаю работать')
        mes = find_fanfic(texxt)
        bot.send_message(message.chat.id, mes)
    elif texxt.lower() == 'словарь':
        last = lastindex()
        if last is not None:
            mes = 'Всего в словаре - ' + str(last) + ' слов. Напиши, до какого индекса выводить словарь'
        else:
            mes = 'Сначала дайте фанфик на обследование, а потом словарь просите'
        bot.send_message(message.chat.id, mes)
    elif texxt.isdigit():
        last = int(texxt)
        mes = slovar(last)
        bot.send_message(message.chat.id, mes)
    else:
        bot.send_message(message.chat.id, 'Скажи help')


bot.polling(none_stop=True, interval=0)  # чтоб бот оставался на сервере и ждал новых сообщений
