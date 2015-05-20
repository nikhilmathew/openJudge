from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from question import models
from django.http import JsonResponse


def home(request):
    """Homepage of the contest"""
    data = {}
    template = 'question/home.html'
    return render(request, template, data)


def leaderboard(request):
    """The scoreboard"""
    data = {}
    template = 'question/leaderboard.html'
    data['players'] = models.Profile.objects.order_by('score')
    data['questions'] = models.Question.objects.order_by('qno')
    return render(request, template, data)


def question_home(request):
    """Show all questions"""
    data = {}
    template = 'question/question.html'
    data['questions'] = models.Question.objects.all()
    return render(request, template, data)


@login_required
def question(request, qno):
    """Display a question and the form to accept the user's answer"""
    qno = int(qno)
    data = {}
    template = 'question/question.html'
    data['question'] = get_object_or_404(models.Question, qno=qno)
    data['attempts'] = models.Attempt.objects.filter(question=data['question'], player=request.user.profile)
    if request.method == 'GET':
        data['answer_form'] = models.AttemptForm()
    if request.method == 'POST':
        data['answer_form'] = models.AttemptForm(request.POST, request.FILES)
        if data['answer_form'].is_valid():
            form = data['answer_form']
            form.save(commit=False)
            form.player = request.user.profile
            form.question = data['question']
            form.marks = data['question'].get_marks()
            form.save()
            return redirect('question', qno=qno)
    return render(request, template, data)


def question_details(request, qno):
    data = {}
    qno = int(qno)
    question = get_object_or_404(models.Question, qno=qno)
    #  -----
    data['inp'] = question.answer.infile.url
    data['out'] = question.answer.outfile.url
    data['type'] = question.answer.answer_type.pk
    return JsonResponse(data)


def language_details(request, lno):
    data = {}
    lno = int(lno)
    language = get_object_or_404(models.Language, lno=lno)
    # -----
    data['wrap'] = language.wrapper.url
    data['misc'] = language.details
    return JsonResponse(data)


def detail_list(request):
    data = {}
    questions = models.Question.objects.all()
    data['question'] = {}
    for q in questions:
        data['question'][str(q.pk)] = {'inp': q.answer.infile.url,
                                       'out': q.answer.outfile.url,
                                       'type': q.answer.answer_type.pk
                                       }
    languages = models.Language.objects.all()
    data['language'] = {}
    for l in languages:
        data['language'][str(l.pk)] = {'wrap': l.wrapper.url,
                                       'misc': l.details,
                                       'overwrite': l.overwrite
                                       }
    return JsonResponse(data)