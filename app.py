from flask import Flask, request, Response
import json
import time
import urllib.parse
import urllib.request
import threading
import re

# TODO: SLEEP 전 메세지를 보내야 하는 문제..threading.Timer 사용하면 좋을 듯
# https://www.geeksforgeeks.org/timer-objects-python/
# timer 설정 후 메세지가 추가로 오는 경우 timer.cancel로 취소
# TODO: 일정 시간이 지난 후 문장 합쳐서 출력
# TODO: 봇과 대화한 기록이 있는 경우 /start 명령어를 넣어야 동작
# TODO: 실제 계정 만들기
# TODO: COUNSEL 로직 추가
# TODO: 모듈화를 위해 다른 파일로 분리: 가장 나중에

# json 파일에서 텔레그램 토큰을 가져온다.
TELEGRAM_TOKEN = ""
with open('key.json', 'r') as f:
    secrets = json.loads(f.read())
    try:
        TELEGRAM_TOKEN = secrets["TELEGRAM_TOKEN"]
    except KeyError:
        pass

# @hamdoe_bot

app = Flask(__name__)
message_dict = {}


@app.route('/webhook', methods=['POST'])
def get_message():
    """webHook으로 push된 요청을 반환한다."""
    message = request.get_json()
    # print(request_data['message']['text'])
    save_message(message)
    return Response(status=204)


def save_message(message):
    """받은 메세지에서 필요한 정보만 추출해 message_dict에 저장한다."""
    last_update_id = 0
    try:
        with open('last_update_id.txt', 'r') as file:
            last_update_id = int(file.read())
    except (FileNotFoundError, ValueError):
        pass

    next_update_id = message['update_id']
    from_id = message['message']['from']['id']
    text = message['message']['text']

    # 새 메세지의 update_id가 파일에 저장되어 있는 update_id보다 큰 경우 파일에 저장
    if next_update_id and next_update_id > last_update_id:
        with open('last_update_id.txt', 'w') as file:
            file.write(str(next_update_id))
        if from_id in message_dict:
            message_dict[from_id][next_update_id] = text
        else:
            message_dict[from_id] = {next_update_id: text}
        print(list(message_dict.values())[0])
    wait_message()


def wait_message():
    check_messages_and_response()
    time.sleep(3)
        # 빠르게 확인하기 위해 일단 3초로 하겠습니다


def check_messages_and_response():
    """
    챗봇으로 메세지를 확인하고, 적절히 응답한다.
    """
    messages = list(message_dict.values())[0]
    last_update_id = max(list(messages.keys()))
    received_messages = list(messages.values())
    chat_id = list(message_dict.keys())[0]
    if received_messages[0] == '/start':
        send_message(chat_id, '안녕 반가워! 나는 상담 챗봇 케라콘이라고 해')
        # time.sleep(1)
        message_dict.clear()
        print(chat_id)
        # 이름을 물어봅니다.
        _, name = ask_name(chat_id)

        # 고민을 듣고 고민을 말한 연속적인 말들을 리스트 형태로 불러옵니다.
        _, question = counsel(name, chat_id)

    # if received_messages:
    #     send_text = ''
    #     for message in received_messages:
    #         send_text += message
    #         send_text += ' '
    #     send_text += ' 라고 말씀하셨군요!'
    #     send_message(chat_id, send_text)


def build_url(method, query=''):
    """텔레그램 챗봇 웹 API에 요청을 보내기 위한 URL을 만들어 반환한다."""
    return f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}?{query}'


def request_to_chatbot_api(method, query=''):
    """메서드와 질의조건을 전달받아 텔레그램 챗봇 웹 API에 요청을 보내고,
        응답 결과를 사전 객체로 해석해 반환한다."""
    url = build_url(method, query)
    response = urllib.request.urlopen(url)
    return response


# response = request_to_chatbot_api('getUpdates', 'offset=0')
# for res in response['result']:
#     print(res['message']['text'])


def simplify_messages(response):
    """텔레그램 챗봇 API의 getUpdate 메서드 요청 결과에서 필요한 정보만 남긴다."""
    result = response['result']
    if not result:
        return None, []
    last_update_id = max(item['update_id'] for item in result)
    messages = [item['message'] for item in result]
    simplified_messages = [{'from_id': message['from']['id'],
                            'text': message['text']}
                           for message in messages]
    return last_update_id, simplified_messages


def get_updates(update_id='0'):
    """챗봇 API로 update_id 이후에 수신한 메세지를 조회하여 반환한다."""
    query = f'offset={update_id}'
    response = request_to_chatbot_api(method='getUpdates', query=query)
    return simplify_messages(response)


def send_message(chat_id, text):
    """
    챗봇 API로 chat_id 사용자에게 text 메세지를 발신한다.
    퍼센트 인코딩을 해줘야 한글뿐만 아니라 띄어쓰기를 포함한 문장을 발신할 수 있다.
    """
    message_text = urllib.parse.quote(text)
    query = f'chat_id={chat_id}&text={message_text}'
    response = request_to_chatbot_api(method='sendMessage', query=query)
    return response


def ask_name(chat_id):
    name = ''
    send_message(chat_id, '너는 이름이 뭐야?')
    time.sleep(5)
    messages = list(message_dict.values())[0]
    last_update_id = max(list(messages.keys()))
    received_messages = list(messages.values())
    chat_id = list(message_dict.keys())[0]
    # last_update_id, received_messages = get_updates(next_update_id)
    for message in received_messages:
        # name = re.search('\\b[가-힣]+\\b이?야?', message).group()
        name = message
        # 이름을 골라내는 부분을 정규표현식으로 쓰고 싶은데 어렵네요ㅠ 잘 아시는 분 있으면 부탁드립니다!
    time.sleep(1)
    send_message(chat_id, '이름이 ' + name + '(이)구나!')
    message_dict.clear()
    return last_update_id, name


def counsel(name, chat_id):
    send_message(chat_id, name + '(이)는 무슨 고민이 있어서 왔어?')
    question = ''
    time.sleep(10)
    messages = list(message_dict.values())[0]
    last_update_id = max(list(messages.keys()))
    received_messages = list(messages.values())
    chat_id = list(message_dict.keys())[0]
    # last_update_id, received_messages = get_updates(next_update_id)
    for message in received_messages:
        question += message
        question += ''
        # 여기 question을 받아서 학습한 모델에 넣으면 될 것 같습니다.
    # print(question)
    time.sleep(1)
    send_message(chat_id, '그랬구나')
    time.sleep(1)
    send_message(chat_id, '많이 힘들었겠다')
    message_dict.clear()

    return last_update_id, question


if __name__ == '__main__':
    app.run()
