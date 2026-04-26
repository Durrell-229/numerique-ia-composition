from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ai_engine.multi_ai import multi_ai

@login_required
def start_qcm(request):
    if request.method == 'POST':
        matiere = request.POST.get('matiere', '')
        classe = request.POST.get('classe', '')
        nb_questions = int(request.POST.get('nb_questions', 10))
        difficulte = request.POST.get('difficulte', 'moyen')
        theme = request.POST.get('theme', '')

        request.session['qcm_context'] = {
            'matiere': matiere, 'classe': classe,
            'nb_questions': nb_questions, 'difficulte': difficulte, 'theme': theme,
        }

        qcm_content = multi_ai.generate_qcm(matiere, classe, nb_questions, difficulte, theme)
        request.session['qcm_generated'] = qcm_content

        return render(request, 'qcm/take.html', {'qcm': qcm_content, 'matiere': matiere, 'classe': classe})

    return render(request, 'qcm/start.html')


@login_required
def submit_qcm(request):
    if request.method != 'POST':
        return redirect('qcm_start')

    reponses = request.POST.get('reponses', '')
    ctx = request.session.get('qcm_context', {})
    qcm_original = request.session.get('qcm_generated', '')

    feedback = multi_ai.correct_qcm(reponses, qcm_original, ctx)
    note = feedback.get('note', 0)

    return render(request, 'qcm/result.html', {
        'feedback': feedback, 'note': note,
        'matiere': ctx.get('matiere', ''), 'classe': ctx.get('classe', ''),
    })
