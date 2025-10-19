"""
Document Management Views (M9 + M11b + M17a + M12a)
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from landlord.models import Contract, Document, DocumentVersion, Property, Tenant, Unit


@staff_member_required
def documents_list(request):
    """List all documents with filters"""
    docs = Document.objects.select_related('uploaded_by', 'property', 'unit', 'tenant').all()

    # Filters
    related_type = request.GET.get('related_type')
    category = request.GET.get('category')
    search = request.GET.get('search', '').strip()

    if related_type:
        docs = docs.filter(related_type=related_type)
    if category:
        docs = docs.filter(category=category)
    if search:
        docs = docs.filter(Q(name__icontains=search) | Q(tags__icontains=search) | Q(notes__icontains=search))

    context = {
        'documents': docs[:100],  # Limit for performance
        'related_type_choices': Document.RelatedType.choices,
        'category_choices': Document.Category.choices,
        # M11b: Dropdowns für Upload-Modal
        'properties': Property.objects.all().order_by('name'),
        'units': Unit.objects.select_related('property').filter(is_active=True).order_by('property__name', 'unit_label'),
        'tenants': Tenant.objects.filter(is_active=True).order_by('primary_email'),
        'filters': {
            'related_type': related_type,
            'category': category,
            'search': search,
        }
    }
    return render(request, 'portal/documents_list.html', context)


@staff_member_required
@require_http_methods(["POST"])
@transaction.atomic
def document_upload(request):
    """Upload a new document (M9 + M11b)"""
    file = request.FILES.get('file')

    # M11b: Direct ForeignKeys statt Generic Relation
    property_id = request.POST.get('property')
    unit_id = request.POST.get('unit')
    tenant_id = request.POST.get('tenant')

    # Legacy support (deprecated)
    related_type = request.POST.get('related_type')
    related_id = request.POST.get('related_id')

    category = request.POST.get('category', 'sonstiges')
    tags = request.POST.get('tags', '')
    notes = request.POST.get('notes', '')

    if not file:
        messages.error(request, "Keine Datei ausgewählt.")
        return redirect('portal_documents')

    # File size limit: 10 MB
    if file.size > 10 * 1024 * 1024:
        messages.error(request, "Datei zu groß (max. 10 MB).")
        return redirect('portal_documents')

    # MIME whitelist
    allowed_types = [
        "image/jpeg", "image/png", "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]
    if file.content_type not in allowed_types:
        messages.error(request, f"Dateityp nicht erlaubt: {file.content_type}")
        return redirect('portal_documents')

    # M11b: Resolve FKs
    property_obj = None
    unit_obj = None
    tenant_obj = None

    if property_id:
        property_obj = get_object_or_404(Property, id=property_id)
    if unit_id:
        unit_obj = get_object_or_404(Unit, id=unit_id)
    if tenant_id:
        tenant_obj = get_object_or_404(Tenant, id=tenant_id)

    # M17a: Check if document already exists (for versioning)
    upload_comment = request.POST.get('upload_comment', '')
    existing_doc = None

    # Try to find existing document by name + same assignment
    if unit_obj:
        existing_doc = Document.objects.filter(
            name=file.name,
            unit=unit_obj
        ).first()
    elif property_obj:
        existing_doc = Document.objects.filter(
            name=file.name,
            property=property_obj
        ).first()
    elif tenant_obj:
        existing_doc = Document.objects.filter(
            name=file.name,
            tenant=tenant_obj
        ).first()

    if existing_doc:
        # M17a: Archive old version before updating
        DocumentVersion.objects.create(
            document=existing_doc,
            version_number=existing_doc.current_version,
            file=existing_doc.file,  # Keep old file!
            size_bytes=existing_doc.size_bytes or 0,
            content_type=existing_doc.content_type or '',
            uploaded_by=existing_doc.uploaded_by,
            upload_comment=f"Replaced by v{existing_doc.current_version + 1}"
        )

        # Update existing document
        existing_doc.file = file
        existing_doc.current_version += 1
        existing_doc.size_bytes = file.size
        existing_doc.content_type = file.content_type
        existing_doc.category = category
        existing_doc.tags = tags
        existing_doc.notes = notes
        existing_doc.uploaded_by = request.user
        existing_doc.save()

        messages.success(
            request,
            f"Dokument '{file.name}' aktualisiert (v{existing_doc.current_version}). "
            f"Alte Version v{existing_doc.current_version - 1} wurde archiviert."
        )
        created_doc = existing_doc
    else:
        # Create new document
        created_doc = Document.objects.create(
            file=file,
            name=file.name,
            category=category,
            current_version=1,
            # M11b: Direct FKs
            property=property_obj,
            unit=unit_obj,
            tenant=tenant_obj,
            # Legacy (deprecated)
            related_type=related_type or '',
            related_id=int(related_id) if related_id else None,
            size_bytes=file.size,
            content_type=file.content_type,
            tags=tags,
            notes=notes,
            uploaded_by=request.user,
        )

        messages.success(request, f"Dokument '{file.name}' hochgeladen (v1).")

    # M12a: Auto-create/link Contract if category is "vertrag" and unit is assigned
    if category == 'vertrag' and unit_obj:
        _handle_contract_for_document(created_doc, unit_obj, request)

    return redirect('portal_documents')


def _handle_contract_for_document(document: Document, unit: Unit, request):
    """
    M12a: Helper to create or link Contract when uploading a Mietvertrag
    """
    # Check if there's already a recent contract for this unit (draft or active)
    recent_contract = Contract.objects.filter(
        unit=unit,
        status__in=[Contract.Status.DRAFT, Contract.Status.ACTIVE]
    ).order_by('-created_at').first()

    if recent_contract:
        # Update existing contract with new document
        recent_contract.document = document
        recent_contract.save()
        messages.info(
            request,
            f"✅ Vertrag für {unit.unit_label} wurde mit Dokument aktualisiert "
            f"(Status: {recent_contract.get_status_display()})."
        )
    else:
        # Create new Contract in DRAFT status
        # User must fill in details (rent, dates, etc.) in admin
        tenant = unit.tenants.filter(is_active=True).first()

        if tenant:
            Contract.objects.create(
                unit=unit,
                tenant=tenant,
                document=document,
                status=Contract.Status.DRAFT,
                start_date=tenant.moved_in_at or timezone.now().date(),
                rent_amount=0,  # Must be filled by user!
                notes=f"Auto-erstellt beim Dokument-Upload: {document.name}"
            )
            messages.info(
                request,
                f"✅ Neuer Vertrag (Entwurf) für {unit.unit_label} erstellt. "
                f"Bitte Konditionen im Admin ausfüllen!"
            )
        else:
            messages.warning(
                request,
                f"⚠️ Kein aktiver Mieter für {unit.unit_label} gefunden. "
                f"Vertrag muss manuell erstellt werden."
            )



@staff_member_required
def document_delete(request, pk: int):
    """Delete a document"""
    doc = get_object_or_404(Document, pk=pk)
    name = doc.name
    doc.delete()
    messages.success(request, f"Dokument '{name}' gelöscht.")
    return redirect('portal_documents')


@staff_member_required
def document_history(request, pk: int):
    """M17a: Show version history of a document"""
    doc = get_object_or_404(Document, pk=pk)

    # Get all archived versions (ordered by version_number DESC)
    versions = doc.versions.select_related('uploaded_by').all()

    context = {
        'document': doc,
        'versions': versions,
    }
    return render(request, 'portal/document_history.html', context)


@staff_member_required
def document_version_download(request, pk: int, version_number: int):
    """M17a: Download a specific old version"""
    doc = get_object_or_404(Document, pk=pk)

    # Special case: version_number == current_version → download current file
    if version_number == doc.current_version:
        from django.http import FileResponse
        response = FileResponse(doc.file.open('rb'))
        response['Content-Disposition'] = f'attachment; filename="{doc.name}"'
        return response

    # Get archived version
    version = get_object_or_404(
        DocumentVersion,
        document=doc,
        version_number=version_number
    )

    from django.http import FileResponse
    response = FileResponse(version.file.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{doc.name}_v{version_number}.pdf"'
    return response

