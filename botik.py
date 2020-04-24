import telebot
import wget, os
import urllib.request
import zipfile
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from string import punctuation
import pymorphy2
from collections import Counter
morph = pymorphy2.MorphAnalyzer()

def delete_files(path):
    os.remove(path) 
    
def file_open(filename):  # читаем файл
    with open(filename, encoding='utf-8') as f:
        text = f.read()
    return text

def text_lemmas(tokens):
    lemmas_lst = []
    for token in tokens:
        token_pr = morph.parse(token)[0]  # возвращает список некоторых характеристики, из клоторых 0 - нужная
        lemmas_lst.append(token_pr.normal_form)  # вытаскивает нужную характеристику - начальную форму
    return lemmas_lst


def freq(lemmas_lst):
    freq_dict = Counter(lemmas_lst)
    return freq_dict

def text_tokens(text):  # делаем список стоп-слов, потом список токенов без стоп-слов
    stop_words = stopwords.words('russian') + [_ for _ in punctuation] + ['—', '«', '»']
    tokens_ws = [token.lower() for token in word_tokenize(text) if token not in stop_words]
    return tokens_ws  # удаляются почему-то не все стоп-слова???


def find_fanfic(linkname):
    f = urllib.request.urlopen(linkname).read()
    pattern = '/download.php?fic='
    index = str(f).find(pattern)
    if index == -1:
        messag = 'Не могу его скачать'
    else:
        idfic = linkname[-6:]
        reallink = "https://fanfics.me/download.php?fic="+idfic +"&format=txt"
        filename = wget.download(reallink)
        os.rename(filename, u''+os.getcwd()+'/'+filename)
        z = zipfile.ZipFile(filename, 'r')
        z.extractall()
        textname = filename[:-3] + 'txt'
        text = file_open(textname)
        tokens_lst = text_tokens(text)
        lemmas_lst = text_lemmas(tokens_lst)
        freq_dict = freq(lemmas_lst)
        freqstr = ''
        counter = 0
        with open('result1.txt', 'w', encoding='utf-8') as f:  # для удобства проверки результатов пишу в файл
            for key, item in freq_dict.most_common():
                s = key + '  :  ' + str(item) + '\n'
                f.write(s)
                if counter < 21:
                    freqstr += s
                counter +=1
        messag = freqstr
        delete_files(filename) #пока нам эти файлы не нужны
        delete_files(textname) #а то перевключать код, чтобы удалить старые файлы, вызывающие ошибку, так как я повторяю их кучу раз...
        delete_files('result1.txt') 
    return messag
               

bot = telebot.TeleBot('1202811556:AAHQh1uQsjHEtbtVL6Z3gOB5X_vQDCDW8eI');
@bot.message_handler(commands=['start']) #чтобы начать с команды старт
    
def start_message(message):
    bot.send_message(message.chat.id, '''Привет, я бот, который сделает частотный 
                     словарь вашего фанфика и сравнит его с литературной нормой и 
                     что-нибудь скажет. Кидайте мне ссылки на фанфики из 
                      fanfics.me''')

@bot.message_handler(content_types=['text'])
def send_text(message):
    texxt = message.text
    if texxt.startswith('https://fanfics.me/') and texxt[-6:].isdigit():
        mes = find_fanfic(texxt)
        bot.send_message(message.chat.id, mes)
    else:
        bot.send_message(message.chat.id, 'Можно рабочую ссылку на fanfics.me пожалуйста?')



bot.polling(none_stop=True, interval=0) #чтоб бот оставался на сервере и ждал новых сообщений