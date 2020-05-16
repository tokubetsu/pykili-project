import telebot
import wget, os
import urllib.request
import zipfile
import re
import csv
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from string import punctuation
import pymorphy2
from collections import Counter
morph = pymorphy2.MorphAnalyzer()

def delete_files(path):
    os.remove(path) 
#чтобы удалять существующие файлы, т к имена всегда одни, чтоб код не рушился
    
def file_open(filename):  # читаем файл
    with open(filename, encoding='utf-8') as f:
        text = f.read()
    return text

def text_tokens(text):  # список токенов
    punctuation_lst = [_ for _ in punctuation] + ['—', '«', '»']
    tokens = [token.lower() for token in word_tokenize(text) if token not in punctuation_lst]  # без пунктуации, но со стоп-словами
    return tokens

def text_lemmas(tokens):
    lemmas_lst = []
    for token in tokens:
        token_pr = morph.parse(token)[0]  # возвращает список некоторых характеристики, из клоторых 0 - нужная
        lemmas_lst.append(token_pr.normal_form)  # вытаскивает нужную характеристику - начальную форму
    return lemmas_lst

def stop_filter(lemmas):
    stop_words = stopwords.words('russian')
    lemmas_ws = [lemma for lemma in lemmas if lemma not in stop_words]  # без стоп-слов
    return lemmas_ws

def freq(lemmas_lst):
    freq_dict = Counter(lemmas_lst)  # создаем частотный словарь
    
    if os.path.exists('result1.txt'): #перенес его запись в файл сюда, а то понадобится чтоб вывести по просьбе
        delete_files('result1.txt')
    with open('result1.txt', 'w', encoding='utf-8') as f:
        for key, item in freq_dict.most_common():
            s = key + '  :  ' + str(item) + '\n'
            f.write(s)
            
    freq_parts = {'NOUN': Counter({}), 'INFN': Counter({}), 'ADJF': Counter({})}  # заготовка под словарь с нужными частями речи
    for lemma in freq_dict:
        lem_part = ''
        lem_pr = morph.parse(lemma)
        detected = False
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
    dict_rus = {}
    dict_comm = {}
    for part in part_dict:
        s = part + '.csv'  # создаем название файла
        dict_rus[part] = {}
        dict_comm[part] = Counter({})
        with open(s, encoding='utf-8') as csv_file:  # читаем csv и пишем его в словарь, но без столбца с частотой
            csv_table = csv.reader(csv_file)
            for row in csv_table:
                cells = row[0].split(';')
                dict_rus[part][cells[1]] = cells[0]
        for word, count in part_dict[part].most_common(numb):  # соотносим пвторой словарь с нужными словами
            if word in dict_rus[part]:
                dict_comm[part][word] = [count, dict_rus[part][word]]
            else:
                dict_comm[part][word] = [count, 'not found']
    return dict_comm


def work_with_txt(text):
    tokens_lst = text_tokens(text)  # токенизация текста
    lemmas_lst = text_lemmas(tokens_lst)  # лемматизация токенов
    lemmas_clean = stop_filter(lemmas_lst)  # удаляем стоп-слова
    word_amount = len(lemmas_lst)  # кол-во слов в тексте
    stopwords_amount = word_amount - len(lemmas_clean)  # кол-во стоп-слов в тексте
    freq_dict, freq_parts = freq(lemmas_clean)  # частостный словарь: общий и по частям речи
    dict_comm = compare(freq_parts)
    water = round(stopwords_amount / word_amount * 100, 2)  # водность в процентах, до двух знаков
    lexical_diversity = round(len(freq_dict) / word_amount * 100, 2)  # разнообразие в процентах, до двух знаков
    messag = 'Уровень водности текста:\t' + str(water) + '%\n'
    messag += 'Коэффициент лексического разнообразия:\t' + str(lexical_diversity) + '%\n'
    for key, item in freq_dict.most_common(20):
        messag += key + '  :  ' + str(item) + '\n'
    for part in dict_comm:
        messag += '\n\n' + part + '\n'
        for word, inf in dict_comm[part].most_common():
            messag += word + '  :  ' + str(inf[0]) + ' vs ' + str(inf[1]) + '\n'
    return messag
 
def lastindex(): #считаем последний индекс частотного словаря
    if os.path.exists('result1.txt'):
        with open('result1.txt', 'r', encoding='utf-8') as f: 
            lines = f.readlines()
            lastindex = len(lines)
        return lastindex

def slovar(last): #Выводим словарь до запрошенного индекса
    freqs=''
    if os.path.exists('result1.txt'):
        with open('result1.txt', 'r', encoding='utf-8') as f: 
            lines = f.readlines()
            index = 0
            while index < last:
                freqs += lines[index]
                index +=1
    else:
        freqs = 'Сначала дайте фанфик на обследование, а потом словарь просите'
    return freqs
           
def find_fanfic(linkname): #Выкачиваем из сайта ссылку на скачивание, скачиваем и извлекаем
    f = urllib.request.urlopen(linkname).read()
    pattern = '/download.php?fic='
    index = str(f).find(pattern)
    if index == -1:
        messag = 'Не могу его скачать'
    else:
        pattern = r'\/download\.php\?fic=\d+&format='
        reallink = 'https://fanfics.me' + re.search(pattern, str(f)).group()+'txt'
        filename = wget.download(reallink) 
        os.rename(filename, u''+os.getcwd()+'/'+filename) #если честно, на момент написания комментариев уже не помню, что это, но оно работает
        z = zipfile.ZipFile(filename, 'r')
        z.extractall()
        textname = filename[:-3] + 'txt'
        text = file_open(textname)
        messag = work_with_txt(text)
        delete_files(filename)
        delete_files(textname)
    return messag
               

bot = telebot.TeleBot('1202811556:AAHQh1uQsjHEtbtVL6Z3gOB5X_vQDCDW8eI');
@bot.message_handler(commands=['start']) #чтобы начать с команды старт
    
def start_message(message):
    bot.send_message(message.chat.id, 'Привет, я бот, который сделает частотный словарь вашего фанфика и сравнит его с литературной нормой и что-нибудь скажет. Кидайте мне ссылки на фанфики из fanfics.me. В изначальном выводе будет коэффициент водности текста, коэффициент лексического разнообразия, частотный словарь общий, по частям речи (кол-во слова в тексте + место слово в списке Ляшевской по этой части речи')
    bot.send_message(message.chat.id, 'Напиши help чтобы узнать, что надо делать')
@bot.message_handler(content_types=['text'])
def send_text(message):
    texxt = message.text
    if texxt.lower() == 'help':
        bot.send_message(message.chat.id, 'Скинь ссылку, начинающуюся на https://fanfics.me/, я посчитаю кое-что. И только потом скажи "словарь", чтобы я отправил тебе часть частотного словаря')
    elif texxt.startswith('https://fanfics.me/'):
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
    
bot.polling(none_stop=True, interval=0) #чтоб бот оставался на сервере и ждал новых сообщений