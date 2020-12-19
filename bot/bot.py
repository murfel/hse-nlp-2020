import datetime
import telebot

from natasha import (Segmenter,
                     NewsEmbedding,
                     NewsMorphTagger,
                     NewsSyntaxParser,
                     DatesExtractor,
                     NewsNERTagger,
                     MorphVocab,
                     Doc,
                     LOC)

bot = telebot.TeleBot('INSERT_YOUR_TOKEN_HERE')

weather = {'Санкт-Петербург': [-10, -20], 'Москва': [4, 7]}


class State:
    asking_weather = True
    date = None
    loc = None


state = State()


def say_hello():
    return 'Привет!'


def say_goodbye():
    return 'Пока!'


def say_weather(when, where):
    when_num = 1
    if when == datetime.date.today():
        when_num = 0
    return 'Погода в {} на {}: {}°C'.format(where, ['сегодня', 'завтра'][when_num], weather[where][when_num])


def say_error():
    return 'Ничего не понимаю. Скажи нормально'


def parse_intent(text):
    text = text.lower()
    if 'привет' in text:
        return 'hello'
    elif 'пока' in text:
        return 'goodbye'
    elif 'погода' in text:
        return 'weather'
    else:
        return 'error'


def custom_date_to_date(custom_date):
    if custom_date in 'сегодня сейчас'.split():
        return datetime.date.today()
    elif custom_date == 'завтра':
        return datetime.date.today() + datetime.timedelta(days=1)
    else:
        return None


def parse_slots_weather(text: str):
    # capitalize each letter, as Natasha is unable to extract lower-case locations
    text = text.title()

    segmenter = Segmenter()
    emb = NewsEmbedding()
    morph_tagger = NewsMorphTagger(emb)
    syntax_parser = NewsSyntaxParser(emb)
    ner_tagger = NewsNERTagger(emb)
    morph_vocab = MorphVocab()

    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    doc.tag_ner(ner_tagger)

    for span in doc.spans:
        span.normalize(morph_vocab)

    # extract location
    spans = [span for span in doc.spans if span.type == LOC]
    loc = spans[0].normal if len(spans) > 0 else None

    # extract date
    dates_extractor = DatesExtractor(morph_vocab)
    dates = list(dates_extractor(text))
    date = None
    if len(dates) > 0:
        date = dates[0]
        today = datetime.date.today()
        date = datetime.date(date.fact.year or today.year, date.fact.month or today.month, date.fact.day or today.day)
    for custom_date in 'сегодня сейчас завтра'.split():
        if custom_date in text.lower():
            date = custom_date_to_date(custom_date)
    return date, loc


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    def reply(text):
        bot.send_message(message.from_user.id, text)

    intent = parse_intent(message.text)
    answer = ''
    global state
    if intent == 'hello':
        answer = say_hello()
        state = State()
    elif intent == 'goodbye':
        answer = say_goodbye()
        state = State()
    elif intent == 'error':
        if state.asking_weather:
            intent = 'weather'
        else:
            answer = say_error()
    if answer:
        reply(answer)

    if intent == 'weather':
        state.asking_weather = True
        date, loc = parse_slots_weather(message.text)
        if date is not None:
            state.date = date
        if loc is not None:
            state.loc = loc

        if state.loc is None or state.loc not in weather.keys():
            reply('В каком городе? Попробуйте Москву или Санкт-Петербург')
            if state.date is None:
                reply('А самое главное — на какой день: на сегодня, на завтра или на какую-то дату?')
        else:  # if location is given and date isn't, assume date is today
            if state.date is None:
                state.date = datetime.date.today()
            answer = say_weather(state.date, state.loc)
            reply(answer)
            state = State()


def main():
    bot.polling(none_stop=True, interval=0)


if __name__ == '__main__':
    main()
