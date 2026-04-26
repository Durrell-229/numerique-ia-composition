import logging
from celery import shared_task
from django.shortcuts import get_object_or_404
from .models import CompositionSession, Resultat
from ai_engine.multi_ai import multi_ai
from ai_engine.services import extract_text_from_file
from io import BytesIO
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

@shared_task
def process_ia_correction(session_id):
    """Tâche de fond pour corriger une copie via l'IA."""
    try:
        session = CompositionSession.objects.get(id=session_id)
    except CompositionSession.DoesNotExist:
        logger.error(f"Session {session_id} introuvable.")
        return f"Erreur: Session {session_id} introuvable."
    
    exam = session.exam
    
    # 1. Récupérer le texte du corrigé type
    corrige_file = exam.files.filter(type_fichier='corrige_type').first()
    corrige_text = ""
    if corrige_file:
        corrige_text = extract_text_from_file(corrige_file.fichier.path)
    
    # 2. Récupérer le texte de la copie de l'élève (fichiers uploadés ou texte direct)
    copie_text = ""
    
    # Fichiers uploadés (images de copies)
    submission_files = session.submission_files.all()
    if submission_files.exists():
        for sub in submission_files:
            copie_text += extract_text_from_file(sub.fichier.path) + "\n"
    
    # Réponses texte directes
    answers = session.answers.all()
    if answers.exists():
        for answer in answers:
            copie_text += f"\nQuestion {answer.question_number}: {answer.content}\n"

    # 3. Appel au service IA
    exam_info = {
        'titre': exam.titre,
        'note_maximale': float(exam.note_maximale)
    }
    
    correction_result = multi_ai.correct_copy(corrige_text, copie_text, exam_info)

    # 4. Enregistrement du résultat
    from django.utils import timezone
    note_finale = float(correction_result.get('note', 0))
    
    # Calcul de la mention
    mention = ''
    if note_finale >= 16: mention = 'excellent'
    elif note_finale >= 14: mention = 'tres_bien'
    elif note_finale >= 12: mention = 'bien'
    elif note_finale >= 10: mention = 'assez_bien'
    elif note_finale >= 8: mention = 'passable'
    else: mention = 'insuffisant'
    
    resultat, created = Resultat.objects.update_or_create(
        session=session,
        defaults={
            'note': note_finale,
            'note_sur': exam.note_maximale,
            'mention': mention,
            'appreciation': correction_result.get('appreciation', ''),
            'corrige_par_ia': True,
            'details_correction': {
                'details': correction_result.get('details', []),
                'points_forts': correction_result.get('points_forts_global', ''),
                'axes_amelioration': correction_result.get('axes_amelioration', '')
            },
            'corrige_at': timezone.now()
        }
    )
    
    # Génération du bulletin PDF (Format Bénin)
    try:
        context = {'resultat': resultat}
        html = render_to_string('compositions/bulletin_resultat_benin.html', context)
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=pdf_file)
        
        if not pisa_status.err:
            pdf_content = pdf_file.getvalue()
            filename = f"bulletin_{session.eleve.last_name}_{exam.titre[:10]}.pdf"
            resultat.bulletin_pdf.save(filename, ContentFile(pdf_content), save=True)
    except Exception as e:
        logger.error(f"Erreur lors de la génération du bulletin PDF: {e}")

    # 5. Marquer la session comme corrigée
    session.statut = 'corrige'
    session.save()
    
    # 6. Attribution de points XP (Gamification)
    try:
        from gamification.models import XPAction
        XPAction.objects.create(
            user=session.eleve,
            action='EXAM_COMPLETE',
            points_gagnes=50,
            description=f"Examen terminé : {exam.titre}"
        )
    except Exception as e:
        logger.warning(f"Erreur gamification: {e}")

    # 7. Envoyer une notification
    try:
        from notifications.utils import send_notification
        send_notification(
            user=session.eleve,
            title="Correction Terminée !",
            message=f"Votre copie pour l'examen '{exam.titre}' a été corrigée par l'IA. Note : {correction_result.get('note', 0)}/{exam.note_maximale}",
            type='BULLETIN'
        )
    except Exception as e:
        logger.warning(f"Erreur notification: {e}")
    
    return f"Correction terminée pour {session.eleve.email}"
