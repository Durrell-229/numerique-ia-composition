from io import BytesIO
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from django.conf import settings
import os

class BulletinService:
    @staticmethod
    def generate_bulletin_pdf(submission):
        """
        Génère un bulletin PDF à partir d'une soumission (CorrectionCopie).
        """
        # Récupération de la note et du feedback depuis la submission
        context = {
            'student': submission.student,
            'exam': submission.exam,
            'grade': submission.grade or "Non noté",
            'feedback': submission.corrected_text,
            'date': submission.created_at,
        }
        
        # Création du PDF avec reportlab
        result = BytesIO()
        pdf_canvas = canvas.Canvas(result, pagesize=letter)
        
        # Titre
        pdf_canvas.setFont("Helvetica-Bold", 16)
        pdf_canvas.drawString(50, 750, "Bulletin de Correction")
        
        # Contenu
        pdf_canvas.setFont("Helvetica", 10)
        y = 720
        pdf_canvas.drawString(50, y, f"Élève: {submission.student.username}")
        y -= 20
        pdf_canvas.drawString(50, y, f"Examen: {submission.exam.titre}")
        y -= 20
        pdf_canvas.drawString(50, y, f"Note: {context['grade']}")
        y -= 30
        
        pdf_canvas.setFont("Helvetica-Bold", 11)
        pdf_canvas.drawString(50, y, "Feedback:")
        y -= 15
        pdf_canvas.setFont("Helvetica", 9)
        
        if context['feedback']:
            lines = context['feedback'].split('\n')
            for line in lines[:30]:  # Limiter à 30 lignes
                pdf_canvas.drawString(50, y, line[:100])
                y -= 12
                if y < 50:
                    break
        
        pdf_canvas.save()
        return result.getvalue()

    @staticmethod
    def generate_pdf_from_bulletin(bulletin):
        """
        Génère un bulletin PDF à partir d'un objet Bulletin.
        Utilisé par le signal post_save de Resultat.
        """
        context = {
            'bulletin': bulletin,
            'eleve': bulletin.eleve,
            'classe': bulletin.classe,
            'periode': bulletin.get_periode_display(),
            'moyenne': bulletin.moyenne_generale,
            'rang': bulletin.rang,
            'appreciation': bulletin.appreciation_ia,
            'annee_scolaire': bulletin.annee_scolaire,
            'lignes': bulletin.lignes.all(),
        }
        
        try:
            html = render_to_string('bulletins/bulletin_officiel_template.html', context)
        except Exception:
            # Fallback si le template n'existe pas
            html = render_to_string('bulletins/bulletin_template.html', {
                'student': bulletin.eleve,
                'grade': bulletin.moyenne_generale,
                'feedback': bulletin.appreciation_ia,
                'date': bulletin.created_at,
            })
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            pdf_content = result.getvalue()
            # Sauvegarder le fichier PDF dans le bulletin
            from django.core.files.base import ContentFile
            filename = f"bulletin_{bulletin.eleve.last_name}_{bulletin.periode}_{bulletin.annee_scolaire}.pdf"
            bulletin.file_pdf.save(filename, ContentFile(pdf_content), save=True)
            return pdf_content
        return None
