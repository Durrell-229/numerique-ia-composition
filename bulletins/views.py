from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Bulletin

@login_required
def index(request):
    # Les élèves voient leurs propres bulletins, les admins voient tout
    if getattr(request.user, 'role', '') == 'eleve':
        bulletins = Bulletin.objects.filter(eleve=request.user)
    else:
        bulletins = Bulletin.objects.all()
    return render(request, 'bulletins/index.html', {'bulletins': bulletins})

@login_required
def detail(request, bulletin_id):
    bulletin = get_object_or_404(Bulletin, id=bulletin_id)
    return render(request, 'bulletins/detail.html', {'bulletin': bulletin})
