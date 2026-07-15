import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.utils import timezone

from .models import PredictionHistory
from .ml import predictor


# ── Index / Predict ────────────────────────────────────────────────────────────

def index(request):
    """Home page with the prediction form."""
    recent = PredictionHistory.objects.all()[:5]
    total = PredictionHistory.objects.count()
    spam_count = PredictionHistory.objects.filter(label='spam').count()
    ham_count = PredictionHistory.objects.filter(label='ham').count()

    context = {
        'recent': recent,
        'total': total,
        'spam_count': spam_count,
        'ham_count': ham_count,
    }
    return render(request, 'detector/index.html', context)


@require_POST
def predict_ajax(request):
    """AJAX endpoint — returns JSON prediction result."""
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()

        if not text:
            return JsonResponse({'error': 'Please enter some text.'}, status=400)

        if len(text) < 5:
            return JsonResponse({'error': 'Text too short. Please enter at least 5 characters.'}, status=400)

        result = predictor.predict(text)

        # Save to history
        PredictionHistory.objects.create(
            text=text,
            label=result['label'],
            confidence=result['confidence'],
            spam_probability=result['spam_prob'],
            ham_probability=result['ham_prob'],
            text_length=len(text),
            source='manual',
        )

        return JsonResponse({
            'success': True,
            'label': result['label'],
            'confidence': result['confidence'],
            'spam_prob': result['spam_prob'],
            'ham_prob': result['ham_prob'],
            'text_length': len(text),
        })

    except FileNotFoundError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Prediction failed: {str(e)}'}, status=500)


@require_POST
def predict_batch(request):
    """Handle batch file upload — multiple messages separated by blank lines."""
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'No file uploaded.')
            return redirect('index')

        content = uploaded_file.read().decode('utf-8', errors='ignore')
        texts = [t.strip() for t in content.split('\n\n') if t.strip()]

        if not texts:
            # Try splitting by newline if no blank lines
            texts = [t.strip() for t in content.split('\n') if t.strip()]

        if not texts:
            messages.error(request, 'No valid messages found in the file.')
            return redirect('index')

        if len(texts) > 500:
            messages.warning(request, f'File contains {len(texts)} messages. Processing first 500.')
            texts = texts[:500]

        results = predictor.predict_batch(texts)

        # Bulk save to DB
        records = [
            PredictionHistory(
                text=r['text'],
                label=r['label'],
                confidence=r['confidence'],
                spam_probability=r['spam_prob'],
                ham_probability=r['ham_prob'],
                text_length=len(r['text']),
                source='batch',
            )
            for r in results
        ]
        PredictionHistory.objects.bulk_create(records)

        spam_n = sum(1 for r in results if r['label'] == 'spam')
        ham_n = len(results) - spam_n

        context = {
            'results': results,
            'total': len(results),
            'spam_count': spam_n,
            'ham_count': ham_n,
            'filename': uploaded_file.name,
        }
        return render(request, 'detector/batch_results.html', context)

    except Exception as e:
        messages.error(request, f'Batch processing failed: {str(e)}')
        return redirect('index')


# ── History ────────────────────────────────────────────────────────────────────

def history(request):
    """Paginated prediction history with search and filter."""
    qs = PredictionHistory.objects.all()

    # Filter
    label_filter = request.GET.get('label', '')
    search_query = request.GET.get('q', '')

    if label_filter in ('spam', 'ham'):
        qs = qs.filter(label=label_filter)

    if search_query:
        qs = qs.filter(text__icontains=search_query)

    # Paginate
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    total = PredictionHistory.objects.count()
    spam_count = PredictionHistory.objects.filter(label='spam').count()
    ham_count = total - spam_count

    context = {
        'page_obj': page_obj,
        'label_filter': label_filter,
        'search_query': search_query,
        'total': total,
        'spam_count': spam_count,
        'ham_count': ham_count,
    }
    return render(request, 'detector/history.html', context)


# ── Dashboard ──────────────────────────────────────────────────────────────────

def dashboard(request):
    """Stats dashboard with charts."""
    total = PredictionHistory.objects.count()
    spam_count = PredictionHistory.objects.filter(label='spam').count()
    ham_count = PredictionHistory.objects.filter(label='ham').count()

    avg_confidence = PredictionHistory.objects.aggregate(avg=Avg('confidence'))['avg'] or 0
    avg_spam_conf = PredictionHistory.objects.filter(label='spam').aggregate(avg=Avg('confidence'))['avg'] or 0
    avg_ham_conf = PredictionHistory.objects.filter(label='ham').aggregate(avg=Avg('confidence'))['avg'] or 0

    # Recent 7 days activity (by day)
    from django.db.models.functions import TruncDate
    daily_data = (
        PredictionHistory.objects
        .annotate(date=TruncDate('created_at'))
        .values('date', 'label')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Build chart data: last 14 days
    from datetime import timedelta
    today = timezone.now().date()
    dates = [(today - timedelta(days=i)) for i in range(13, -1, -1)]
    date_labels = [d.strftime('%b %d') for d in dates]

    spam_daily = {d: 0 for d in dates}
    ham_daily = {d: 0 for d in dates}
    for entry in daily_data:
        if entry['date'] in spam_daily:
            if entry['label'] == 'spam':
                spam_daily[entry['date']] = entry['count']
            else:
                ham_daily[entry['date']] = entry['count']

    spam_series = [spam_daily[d] for d in dates]
    ham_series = [ham_daily[d] for d in dates]

    # Confidence distribution buckets
    ranges = [(0, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    conf_labels = ['< 60%', '60-70%', '70-80%', '80-90%', '90-100%']
    conf_data = []
    for low, high in ranges:
        conf_data.append(
            PredictionHistory.objects.filter(
                confidence__gte=low, confidence__lt=high
            ).count()
        )

    recent = PredictionHistory.objects.all()[:10]

    context = {
        'total': total,
        'spam_count': spam_count,
        'ham_count': ham_count,
        'spam_pct': round(spam_count / total * 100, 1) if total else 0,
        'ham_pct': round(ham_count / total * 100, 1) if total else 0,
        'avg_confidence': round(avg_confidence, 1),
        'avg_spam_conf': round(avg_spam_conf, 1),
        'avg_ham_conf': round(avg_ham_conf, 1),
        'date_labels': json.dumps(date_labels),
        'spam_series': json.dumps(spam_series),
        'ham_series': json.dumps(ham_series),
        'conf_labels': json.dumps(conf_labels),
        'conf_data': json.dumps(conf_data),
        'recent': recent,
    }
    return render(request, 'detector/dashboard.html', context)


# ── Delete ─────────────────────────────────────────────────────────────────────

@require_POST
def delete_history(request):
    """Delete all prediction history."""
    PredictionHistory.objects.all().delete()
    messages.success(request, 'All prediction history has been cleared.')
    return redirect('history')
