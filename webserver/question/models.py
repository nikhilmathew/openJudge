import json
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.forms import ModelForm
from question import functions


class Profile(User):
    def __str__(self):
        return self.user.__str__()
    score = models.FloatField(default=0.0)
    last_solved = models.DateTimeField(default=now)


class Language(models.Model):
    """A programming language which is available on the check server"""
    def __str__(self):
        return self.name
    name = models.CharField(max_length=100)
    details = models.TextField()
    wrapper = models.FileField(upload_to='wrappers')
    overwrite = models.BooleanField(default=False, help_text='overwrite required for storing the source code')


class Attempt(models.Model):
    """An attempt on a question"""
    def __str__(self):
        return self.question.__str__() + ' - ' + self.player.__str__()
    player = models.ForeignKey('Profile', related_name='player')
    question = models.ForeignKey('Question', related_name='question')
    language = models.ForeignKey('Language', related_name='language')
    source = models.FileField(upload_to='%t/')
    correct = models.NullBooleanField(default=None)
    stamp = models.DateTimeField(auto_now_add=True)
    marks = models.FloatField()
    remarks = models.TextField()  # Remarks from the check server go there

    def __get_json__(self):
        data = {'pk': self.pk,
                'qno': self.question.qno,
                'source': self.source.url,
                'language': self.language.pk,
                }
        return data

    def is_correct(self):
        """Checks if the attempt was correct"""
        if self.correct! = None:
            return self.correct
        else:
            data = self.__get_json__()
            data = json.dumps(data)
            result, comment = functions.ask_check_server(data)
            self.correct = result
            self.remarks = comment
            self.save()
            return self.correct


class Question(models.Model):
    """A question in the competition"""
    qno = models.IntegerField()
    title = models.CharField(max_length=50)
    text = models.TextField(default='Question text goes here')
    # -----------

    def __str__(self):
        return self.title

    def get_score(self):
        """Get the current score for a question"""
        total_attempts = Attempt.objects.filter(question=self).exclude(correct=None).count()
        correct_attempts = Attempt.objects.filter(question=self, correct=True).count()
        if total_attempts == 0:
            score = 1.0
        else:
            score = float(correct_attempts) / float(total_attempts)
        return score


class AnswerType(models.Model):
    """Used to determine which type of checking to use.
    Error tolerant or exact"""

    def __str__(self):
        return self.name
    name = models.CharField(max_length=50)


class Answer(models.Model):
    """The answer to a question"""
    def __str__(self):
        return self.question.__str__()
    question = models.OneToOneField(Question)
    infile = models.FileField(upload_to='test_cases')
    outfile = models.FileField(upload_to='test_cases')
    sample_code = models.FileField(upload_to='solutions')
    answer_type = models.ForeignKey(AnswerType, related_name='answer_type')


class AttemptForm(ModelForm):
    class Meta:
        model = Attempt
        exclude = ['player', 'question', 'stamp', 'correct']