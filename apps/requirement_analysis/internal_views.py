import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from backend.internal_service_auth import verify_internal_service_signature

from .models import RequirementDocument
from .services import DocumentProcessor


DOCUMENT_EXTRACTION_SCOPE = 'document-extraction'


@csrf_exempt
@require_POST
def extract_document_text_internal(request):
    try:
        payload = json.loads(request.body or b'{}')
        document_id = int(payload.get('document_id'))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid document_id'}, status=400)

    signature = request.headers.get('X-TestHub-Internal-Signature', '')
    if not verify_internal_service_signature(
        signature,
        DOCUMENT_EXTRACTION_SCOPE,
        document_id,
    ):
        return JsonResponse({'error': 'invalid internal signature'}, status=403)

    document = RequirementDocument.objects.filter(pk=document_id).first()
    if not document:
        return JsonResponse({'error': 'document not found'}, status=404)

    try:
        extracted_text = DocumentProcessor.extract_text(document)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=422)

    if extracted_text != document.extracted_text:
        document.extracted_text = extracted_text
        document.save(update_fields=['extracted_text', 'updated_at'])

    return JsonResponse(
        {
            'document_id': document.id,
            'extracted_text': extracted_text,
        }
    )
