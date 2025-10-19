"""
KPI & Reports Views (M9)
"""
import csv
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, F
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from landlord.models import Issue


@staff_member_required
def reports_kpi(request):
    """KPI Dashboard with SLA tracking"""
    now = timezone.now()
    last_30_days = now - timedelta(days=30)

    # Open issues per property
    open_by_property = Issue.objects.filter(
        status__in=['NEW', 'IN_PROGRESS', 'WAITING_TENANT', 'WAITING_VENDOR']
    ).values('unit__property__name').annotate(count=Count('id')).order_by('-count')[:10]

    # Average time to first response (last 30 days)
    issues_with_response = Issue.objects.filter(
        created_at__gte=last_30_days,
        first_response_at__isnull=False
    ).annotate(
        response_time_seconds=F('first_response_at') - F('created_at')
    )

    avg_response_by_category = issues_with_response.values('category').annotate(
        avg_seconds=Avg(F('first_response_at') - F('created_at'))
    ).order_by('category')

    # Average time to resolution (last 30 days)
    issues_done = Issue.objects.filter(
        created_at__gte=last_30_days,
        done_at__isnull=False
    )

    avg_resolution_by_severity = issues_done.values('severity').annotate(
        avg_seconds=Avg(F('done_at') - F('created_at'))
    ).order_by('severity')

    # SLA breaches (simple: issues where first_response took > 24h)
    sla_breached = Issue.objects.filter(
        created_at__gte=last_30_days,
        first_response_at__isnull=False
    ).annotate(
        response_hours=F('first_response_at') - F('created_at')
    ).filter(response_hours__gt=timedelta(hours=24)).count()

    total_with_response = issues_with_response.count()
    breach_percentage = (sla_breached / total_with_response * 100) if total_with_response > 0 else 0

    context = {
        'open_by_property': open_by_property,
        'avg_response_by_category': [
            {
                'category': item['category'],
                'avg_hours': (item['avg_seconds'].total_seconds() / 3600) if item['avg_seconds'] else 0
            }
            for item in avg_response_by_category
        ],
        'avg_resolution_by_severity': [
            {
                'severity': item['severity'],
                'avg_hours': (item['avg_seconds'].total_seconds() / 3600) if item['avg_seconds'] else 0
            }
            for item in avg_resolution_by_severity
        ],
        'sla_breached': sla_breached,
        'total_with_response': total_with_response,
        'breach_percentage': round(breach_percentage, 1),
    }

    return render(request, 'portal/reports_kpi.html', context)


@staff_member_required
def export_kpi_csv(request):
    """Export KPI data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="kpi_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Metric', 'Value', 'Unit'])

    now = timezone.now()
    last_30_days = now - timedelta(days=30)

    # Open issues
    open_count = Issue.objects.filter(
        status__in=['NEW', 'IN_PROGRESS', 'WAITING_TENANT', 'WAITING_VENDOR']
    ).count()
    writer.writerow(['Open Issues', open_count, 'count'])

    # Avg response time
    issues_with_response = Issue.objects.filter(
        created_at__gte=last_30_days,
        first_response_at__isnull=False
    )

    if issues_with_response.exists():
        avg_seconds = issues_with_response.aggregate(
            avg=Avg(F('first_response_at') - F('created_at'))
        )['avg']
        avg_hours = avg_seconds.total_seconds() / 3600 if avg_seconds else 0
        writer.writerow(['Avg First Response Time (30d)', round(avg_hours, 2), 'hours'])

    # SLA breaches
    sla_breached = issues_with_response.annotate(
        response_hours=F('first_response_at') - F('created_at')
    ).filter(response_hours__gt=timedelta(hours=24)).count()

    writer.writerow(['SLA Breaches (>24h response)', sla_breached, 'count'])

    return response
