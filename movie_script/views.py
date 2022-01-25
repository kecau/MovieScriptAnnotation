from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib import auth
from django.shortcuts import redirect
from django.db import connection
from .models import user_data, annotation
from django.http import HttpResponse
from django.core import serializers
import json
from django.utils import timezone

# Create your views here.

def main(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    user_id = request.session.get('user_id', '')


    return render(request, 'movie_script/main.html', {'user_id': user_id})

def signup(request):
    user_id = request.POST.get('user_id', '').lower()
    name = request.POST.get('name', '')
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    mobile = request.POST.get('mobile', '')
    email = request.POST.get('email', '').lower()
    birth = request.POST.get('birth', '')
    gender = request.POST.get('gender', '')

    if request.method == "POST":
        #return render(request, 'movie_script/signup.html', {})
        # auth_user 테이블 유저 생성
        user = User.objects.create_user(username=user_id, password=password1)
        auth_user_pk = user.id

        # tokenizer_user_data 테이블에 유저 데이터 입력
        user_data_model = user_data(auth_user_pk=auth_user_pk, user_id=user_id, user_name=name, mobile=mobile, email=email, birth=birth,
                                    gender=gender)
        user_data_model.save()

        # 로그인
        auth.login(request, user)
        # session에 username 저장
        request.session['user_id'] = user_id

        # 실행 시간이 오래 걸리는 작업은 signup_after 에서 처리한다.
        # 1. 유저가 입력한 경험 데이터에 konlpy 를 적용한다.
        # 2. tokenizer_user_experience 테이블에 유저가 입력한 경험 데이터 입력한다.
        # 3. tokenizer_user_experience 테이블에서 현재 유저의 데이터를 tokenizer_keyword_select 테이블의 모든 유저에게 insert 한다.
        content = {'auth_user_pk': auth_user_pk,
                   'user_id': user_id,
                   }
        return render(request, 'movie_script/main.html', content)


        # keyword_selector로 redirect
        #return redirect('keyword_selector')


    return render(request, 'movie_script/signup.html', {})



# user를 생성하기 전 중복되는 user_id가 있는지 체크하는 함수
# signup.html 에서 ajax를 통해 호출된다.
def user_duplication_check(request):

    error = ''
    user_id = request.GET.get('user_id').lower()
    # 동일 user id가 있는지 확인
    if User.objects.filter(username=user_id).first() is not None:
        error = '동일한 User ID가 이미 존재합니다.'
    # 현재 유저 수가 100명 이상인지 확인
    elif User.objects.count() > 100:
        error = '더 이상 계정을 만들 수 없습니다.'

    return HttpResponse(error)



# log in
def login(request):
    error = ''
    username = request.POST.get('username', '').strip().lower()
    password = request.POST.get('password', '')

    if request.method == "POST":
        # 유저가 존재하는지 확인
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            # 로그인
            auth.login(request, user)
            # 세션에 유저이름 저장
            request.session['user_id'] = username
            # keyword_selector로 redirect
            return redirect('main')
        else:
            return render(request, 'movie_script/login.html', {'error': 'username or password is incorrect'})
    else:
        return render(request, 'movie_script/login.html')

# log out
def logout(request):
    auth.logout(request)
    return redirect('login')



# 유저 정보 조회
def account(request):

    # 로그인 체크
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        print(request.session.get('user_id', ''))

    # 현재 유저 정보 조회
    user_id = request.session.get('user_id', '').lower()

    sql = """select * from movie_script_user_data
           where user_id = '""" + user_id + """'
           limit 1"""
    data = user_data.objects.raw(sql)
    data = serializers.serialize('json', data, ensure_ascii=False)
    data = json.loads(data)[0]['fields']


    # GET일 경우 현재 유저의 정보를 보여준다.
    if request.method == 'GET':
        content = {'data': data}
        return render(request, 'movie_script/account.html', content)


    # Edit 버튼을 눌렀을 경우 유저 정보를 수정한다.
    elif request.method == 'POST' and request.POST.get('action', '') == 'edit':
        user_id = request.POST.get('user_id', '').lower()
        name = request.POST.get('name', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        mobile = request.POST.get('mobile', '')
        email = request.POST.get('email', '').lower()
        birth = request.POST.get('birth', '')
        gender = request.POST.get('gender', '')

        # tokenizer_user_data 테이블에서 유저 정보를 가져온다.
        table = user_data.objects.get(user_id=user_id)
        table.updated_date = timezone.now()
        table.user_name = name
        table.mobile = mobile
        table.email = email
        table.birth = birth
        table.birth = birth
        table.gender = gender
        table.save()

        # 만약 비밀번호가 수정되었다면 auth_user 테이블의 유저 비밀번호를 변경한다.
        if request.POST.get('password_is_edited', 'false') == 'true':
            user = request.user
            user.set_password(password1)
            user.save()
            auth.login(request, user)


        return redirect('main')


    # delete account 버튼을 눌렀을 경우 유저를 삭제한다.
    elif request.method == 'POST' and request.POST.get('action', '') == 'delete':

        # tokenizer_user_data 테이블에서 해당 유저의 데이터 삭제
        sql = "delete from movie_annotation.movie_script_user_data where user_id='" + request.user.username + "'"
        with connection.cursor() as cursor:
            cursor.execute(sql)

        # auth_user 테이블에서 유저 삭제
        request.user.delete()

        return redirect('login')

    return render(request, 'movie_script/login.html')



# login 페이지에서 forgot_password? 버튼을 눌렀을 경우
def forgot_password(request):

    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip().lower()
        email = request.POST.get('email', '').strip().lower()

        # tokenizer_user_data 테이블에서 user_id와 email이 일치하는 유저가 있는지 찾아본다.
        sql = "select * from movie_script_user_data where user_id = '" + user_id + "' and email = '" + email + "'"
        data = user_data.objects.raw(sql)
        data = serializers.serialize('json', data, ensure_ascii=False)
        data = json.loads(data)

        # 일치하는 유저가 없을 경우 다시 돌아감
        if len(data) < 1:
            error = '일치하는 계정 정보가 없습니다.'
            content = {'user_id':user_id, 'email':email, 'error':error}
            return render(request, 'movie_script/forgot_password.html', content)
        # 일치하는 유저가 있을 경우
        else:
            content = {'user_id':user_id, 'email':email}
            return render(request, 'movie_script/reset_password.html', content)

    return render(request, 'movie_script/forgot_password.html')


# 비밀번호 reset
# forgot_password 페이지로부터 넘어옴
def reset_password(request):

    user_id = request.POST.get('user_id', '').strip().lower()
    email = request.POST.get('email', '').strip().lower()
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    if user_id == '' or email == '':
        return render(request, 'movie_script/reset_password.html')

    if request.method == 'POST':
        # 비밀번호 변경
        u = User.objects.get(username__exact=user_id)
        u.set_password(password1)
        u.save()
        return redirect('login')

    return render(request, 'movie_script/reset_password.html')

def update(request):

    # 로그인 체크
    if not request.user.is_authenticated:
        print("Not logged in")
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        print("Logged in")
        print(request.session.get('user_id', ''))

    user_id = request.session.get('user_id', '')
    speaker = request.GET.get('speaker')
    speech = request.GET.get('speech')
    listener = request.GET.get('listener')
    movie_name = request.GET.get('movie_name')
    annotation_key = request.GET.get('annotation_key')

    sql = """select * from movie_annotation.movie_script_annotation where user_id = '""" + user_id + """' and annotation_key = '""" + annotation_key + """' and movie_name = '""" + movie_name + """'"""

    sql = annotation.objects.raw(sql)
    sql = serializers.serialize('json', sql, ensure_ascii=False)
    sql = json.loads(sql)

    if sql != []:
        table = annotation.objects.get(user_id=user_id,annotation_key=annotation_key,movie_name=movie_name)
        table.updated_date = timezone.now()
        table.user_id = user_id
        table.annotation_key = annotation_key
        table.speaker = speaker
        table.speech = speech
        table.listener = listener
        table.movie_name = movie_name

        table.save()

    else:
        insert_sql="""insert into movie_annotation.movie_script_annotation (created_date, user_id, speaker, speech, listener, movie_name, annotation_key)
        values (now(),'""" + user_id + """','""" + speaker + """','""" + speech + """','""" + listener + """','""" + movie_name + """','""" + annotation_key + """')"""

        with connection.cursor() as cursor:
            cursor.execute(insert_sql)

    return HttpResponse("Success!")

def delete(request):

    # 로그인 체크
    if not request.user.is_authenticated:
        print("Not logged in")
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        print("Logged in")
        print(request.session.get('user_id', ''))

    user_id = request.session.get('user_id', '')
    movie_name = request.GET.get('movie_name')
    annotation_key = request.GET.get('annotation_key')

    delete_sql = """delete from movie_annotation.movie_script_annotation where user_id = '""" + user_id + """' and movie_name = '""" + movie_name + """' and annotation_key = '""" + annotation_key + """'"""

    with connection.cursor() as cursor:
        cursor.execute(delete_sql)

    return HttpResponse("Success!")

def instructions(request):
    return render(request, 'movie_script/instructions.html')


def 팔월의크리스마스(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "8월의 크리스마스"

    characters = ['정원', '다림']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_8월의크리스마스.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 칠급공무원(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    # if user_id != '':

    movie_name = "7급공무원"

    characters = ['수지', '재준']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_7급공무원.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id':user_id,'rawtext':script, 'data':data, 'movie_name':movie_name, 'data_length':data_length,'characters':characters,'saved_script':saved_script}


    return render(request, 'movie_script/movie_annotation.html',content)

def ing(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "Ing.."

    characters = ['민아', '영재', '미숙']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_ing.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def m(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "M"

    characters = ['민우', '미미', '은혜']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_M.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def ymca야구단(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "YMCA야구단"

    characters = ['정림', '호창']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_YMCA야구단.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 가면(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "가면"

    characters = ['차수진', '조형사', '김형사']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_가면.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 가문의영광(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "가문의 영광"

    characters = ['진경', '인재', '대서', '인태']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_가문의영광.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 가위(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "가위"

    characters = ['혜진', '선애', '은주', '현준', '정욱']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_가위.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 가을로(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "가을로"

    characters = ['현우', '민주', '세진']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_가을로.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 가족(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "가족"

    characters = ['정은', '주석', '정환']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_가족.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 가족의탄생(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "가족의 탄생"

    characters = ['미라', '형철', '무신']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_가족의탄생.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 각설탕(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "각설탕"

    characters = ['익두', '시은', '김조교사', '민자', '김조교사', '철이','판돌']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_각설탕.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 간신(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "간신"

    characters = ['숭재', '융', '사홍', '단희', '중매']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_간신.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 간첩리철진(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "간첩 리철진"

    characters = ['철진', '오선생', '화이']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_간첩리철진.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 강원도의힘(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "강원도의 힘"

    characters = ['상권', '지숙', '경찰관', '재완', '은경', '미선']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_강원도의힘.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 강철중(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "강철중: 공공의 적 1-1"

    characters = ['철중', '재영']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_강철중.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 거룩한계보(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "거룩한 계보"

    characters = ['치성', '주중']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_거룩한계보.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 거미숲(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "거미숲"

    characters = ['강민', '수인', '은아']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_거미숲.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 거울속으로(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "거울속으로"

    characters = ['우영민', '하현수', '이지현']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_거울속으로.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 건축무한육면각체의비밀(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "건축무한육면각체의 비밀"

    characters = ['용민', '태경', '덕희']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_건축무한육면각체의비밀.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 건축학개론(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "건축학개론"

    characters = ['승민', '서연']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_건축학개론.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 결혼은미친짓이다(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "결혼은, 미친짓이다"

    characters = ['준영', '연희']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_결혼은미친짓이다.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 고사(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "고사: 피의 중간고사"

    characters = ['창욱', '소영', '이나', '강현']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_고사.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 고양이를부탁해(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "고양이를 부탁해"

    characters = ['태희', '혜주', '지영', '온조' , '비류']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_고양이를부탁해.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 고지전(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "고지전"

    characters = ['강은표', '김수혁']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_고지전.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 곡성(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "곡성"

    characters = ['종구', '일광', '외지인(일본인)', '무명', '효진']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_곡성.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 공공의적(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "공공의 적"

    characters = ['철중', '규환']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_공공의적.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 공공의적2(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "공공의 적 2"

    characters = ['철중', '상우']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_공공의적2.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 공동경비구역JSA(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "공동경비구역 JSA"

    characters = ['경필', '수혁', '소피']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_공동경비구역JSA.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 광식이동생광태(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "광식이 동생 광태"

    characters = ['광식', '광태']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_광식이동생광태.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 괴물(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "괴물"

    characters = ['강두', '남일', '남주', '희봉', '현서']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_괴물.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 국가대표(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "국가대표"

    characters = ['밥', '헌태', '방코치', '칠구', '흥철', '재복', '봉구', '수연']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_국가대표.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 국화꽃향기(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "국화꽃향기"

    characters = ['희재', '인하']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_국화꽃향기.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 귀여워(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "귀여워"

    characters = ['963', '뭐시기', '순이', '개코']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_귀여워.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 그녀를믿지마세요(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "그녀를 믿지 마세요"

    characters = ['영주', '희철']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_그녀를믿지마세요.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 그놈은멋있었다(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "그 놈은 멋있었다"

    characters = ['은성', '예원']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_그놈은멋있었다.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 그림자살인(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "그림자 살인"

    characters = ['진호', '광수', '순덕']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_그림자살인.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 그해여름(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "그 해 여름"

    characters = ['석영', '정인']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_그해여름.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 극락도살인사건(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "극락도 살인사건"

    characters = ['우성', '춘배', '귀남']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_극락도살인사건.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 꽃잎(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "꽃잎"

    characters = ['장', '소녀']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_꽃잎.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 꽃피는봄이오면(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "꽃피는 봄이 오면"

    characters = ['현우', '수연', '연희', '엄마(현우 모)']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_꽃피는봄이오면.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 끝까지간다(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "끝까지 간다"

    characters = ['고건수', '박창민']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_끝까지간다.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 나도아내가있었으면좋겠다(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "나도 아내가 있었으면 좋겠다"

    characters = ['원주', '봉수']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_나도아내가있었으면좋겠다.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 나의결혼원정기(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "나의 결혼원정기"

    characters = ['만택', '라라', '희철']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_나의결혼원정기.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 남극일기(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "남극일기"

    characters = ['도형', '민재']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_남극일기.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 내깡패같은애인(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "내 깡패 같은 애인"

    characters = ['동철', '세진']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_내깡패같은애인.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 내마음의풍금(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "내 마음의 풍금"

    characters = ['수하', '홍연', '은희']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_내마음의풍금.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 내머리속의지우개(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "내 머리 속의 지우개"

    characters = ['철수', '수진']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_내머리속의지우개.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 내생애가장아름다운일주일(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "내 생애 가장 아름다운 일주일"

    characters = ['곽회장', '김여인', '조사장', '태현', '유정', '나반장', '성원', '여작가', '창후', '선애', '수경', '정훈']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_내생애가장아름다운일주일.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 내심장을쏴라(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None


    movie_name = "내 심장을 쏴라"

    characters = ['수명', '승민']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_내심장을쏴라.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 너는내운명(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "너는 내 운명"

    characters = ['은하', '석중']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_너는내운명.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 넘버3(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "넘버 3"

    characters = ['태주', '현지', '마동팔']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_넘버3.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 누가그녀와잤을까(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "누가 그녀와 잤을까?"

    characters = ['지영', '태요', '명섭', '재성']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_누가그녀와잤을까.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 눈물(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "눈물"

    characters = ['한', '새리', '창', '란']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_눈물.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 눈에는눈이에는이(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "눈에는 눈 이에는 이"

    characters = ['백반장', '안현민']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_눈에는눈이에는이.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 다세포소녀(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "다세포소녀"

    characters = ['가난소녀', '안소니']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_다세포소녀.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 다찌마와리(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "다찌마와 Lee"

    characters = ['리', '충녀', '화녀']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_다찌마와리.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 단적비연수(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "단적비연수"

    characters = ['단', '적', '비', '연', '수']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_단적비연수.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 달마야놀자(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "달마야 놀자"

    characters = ['재규', '청명']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_달마야놀자.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 달콤살벌한연인(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "달콤, 살벌한 연인"

    characters = ['대우', '미나']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_달콤살벌한연인.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 달콤한인생(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "달콤한 인생"

    characters = ['선우', '강사장']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_달콤한인생.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 대한민국헌법제1조(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "대한민국 헌법 제1조"

    characters = ['은비', '세영']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_대한민국헌법제1조.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 뜨거운것이좋아(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "뜨거운 것이 좋아"

    characters = ['영미', '아미', '강애', '승원', '경수', '호재']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_뜨거운것이좋아.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 파이란(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "파이란"

    characters = ['강재', '파이란']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_파이란.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 마이제너레이션(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "마이 제너레이션"

    characters = ['병석', '재경']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_마이제너레이션.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 여고괴담2(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "여고괴담 두번째 이야기"

    characters = ['민아', '효신', '시은']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_여고괴담2.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 박하사탕(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "박하사탕"

    characters = ['영호', '순임', '홍자']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_박하사탕.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 수취인불명(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "수취인불명"

    characters = ['창국', '은옥', '지흠', '개눈', '창국모', '지흠부', '제임스']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_수취인불명.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 싱글즈(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "싱글즈"

    characters = ['나난', '정준', '동미', '수헌']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_싱글즈.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 오수정(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "오! 수정"

    characters = ['수정', '재훈', '영수']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_오수정.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 올드보이(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "올드보이"

    characters = ['대수', '우진', '미도']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_올드보이.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 우아한거짓말(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "우아한 거짓말"

    characters = ['현숙', '만지', '화연', '천지']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_우아한거짓말.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 유령(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "유령"

    characters = ['202', '찬석']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_유령.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 이중간첩(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "이중간첩"

    characters = ['병호', '수미']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_이중간첩.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 추격자(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "추격자"

    characters = ['중호', '영민']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_추격자.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 커밍아웃(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "커밍 아웃"

    characters = ['현주', '재민', '지은', '여중생']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_커밍아웃.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 파란대문(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "파란대문"

    characters = ['진아', '혜미']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_파란대문.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 페이스(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "페이스"

    characters = ['현민', '선영']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_페이스.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 하루(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "하루"

    characters = ['진원', '석윤']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_하루.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)

def 행복한장의사(request):

    #login check
    if not request.user.is_authenticated:
        # 로그인되지 않았다면 login 페이지로 redirect
        return redirect('login')
    # user_id가 ''이면 logout
    elif request.session.get('user_id', '') == '':
        return redirect('logout')
    # 로그인 되어있음
    else:
        None

    movie_name = "행복한 장의사"

    characters = ['재현', '철구', '할아버지']

    sql_load = annotation.objects.values('user_id', 'speaker', 'speech', 'listener', 'annotation_key').filter(movie_name=movie_name)
    data_length = []
    for i in range(len(sql_load)):
        data_length.append(i)

    data = {}
    data['user_id'] = []
    data['speaker'] = []
    data['speech'] = []
    data['listener'] = []
    data['annotation_key'] = []

    for i in sql_load:
        data['user_id'].append(i['user_id'])
        data['speaker'].append(i['speaker'])
        data['speech'].append(i['speech'])
        data['listener'].append(i['listener'])
        data['annotation_key'].append(i['annotation_key'])

    saved_script = json.dumps(data['speech'])

    d = open('E:\Jiyoon\djangoProject\movie_script\scenario\시나리오_행복한장의사.txt', 'r', encoding='UTF-8')
    lines = d.readlines()

    script = []
    for line in lines:
        script.append(line)
    d.close()

    user_id = request.session.get('user_id', '')

    content = {'user_id': user_id, 'rawtext': script, 'data': data, 'movie_name': movie_name,
               'data_length': data_length, 'characters': characters, 'saved_script': saved_script}

    return render(request, 'movie_script/movie_annotation.html',content)