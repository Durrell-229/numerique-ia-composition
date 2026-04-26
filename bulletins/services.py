from io import BytesIO
from django.template.loader import render_to_string
from xhtml2pdf import pisa
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
        
        # Rendu du template HTML
        html = render_to_string('bulletins/bulletin_template.html', context)
        
        # Création du PDF
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            return result.getvalue()
        return None

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
