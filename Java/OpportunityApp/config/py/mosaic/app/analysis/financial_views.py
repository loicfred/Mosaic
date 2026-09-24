"""Observed financial exploration, using the shared order-grain table."""
import pandas as pd

from app.analysis.business_profile import placed_orders
from app.config import DATA_RANGE, EXCLUDED_STATUSES
from app.models import MODEL_NAMES, SALES_MODEL, CASHFLOW_MODEL

LIMITATIONS = [
    "Historical Brazilian Olist records, not Mauritian business evidence.",
    "Sales are gross item prices in BRL, excluding freight; not profit or merchant cash.",
]
ASSIGNMENT = "Category and seller use the highest-priced item per order; all order value is assigned to it."


def _ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def _scope(frame, sales=False):
    placed = placed_orders(frame, with_items=False)
    return placed[~placed['order_status'].isin(EXCLUDED_STATUSES)] if sales else placed


def _base(**values):
    return {'currency': 'BRL', 'rate_unit': 'fraction', 'limitations': list(LIMITATIONS), **values}


def quality(state):
    frame = state.orders.frame
    dates = frame['purchase_ts'].dropna()
    return _base(
        summary={'orders': len(frame), 'purchase_start': str(dates.min()) if len(dates) else None,
                 'purchase_end': str(dates.max()) if len(dates) else None,
                 'missing_delivery_dates': int(frame['order_delivered_customer_date'].isna().sum()),
                 'missing_reviews': int(frame['review_score'].isna().sum()),
                 'missing_purchase_dates': int(frame['purchase_ts'].isna().sum())},
        statuses=[{'status': str(k), 'orders': int(v)} for k, v in frame['order_status'].value_counts(dropna=False).items()],
        exclusions={'orders': state.orders.exclusions, 'sales': state.monthly.exclusions},
        analysis_range={'start': DATA_RANGE[0], 'end': DATA_RANGE[1]},
        dataset_hashes=state.dataset_hashes,
    )


def payments(frame, raw):
    scoped = _scope(frame)
    monthly, predominant, mix = [], [], []
    for month, rows in scoped.groupby('month'):
        paid = rows[rows['payment_total'].notna()]
        eligible = rows[~rows['order_status'].isin(EXCLUDED_STATUSES) & rows['total_price'].notna()]
        instalments = paid['installments'].dropna()
        monthly.append({'month': month, 'orders': len(rows), 'payment_orders': len(paid),
                        'payment_total': float(paid['payment_total'].sum()), 'sales': float(eligible['total_price'].sum()),
                        'average_order_value': _ratio(eligible['total_price'].sum(), len(eligible)),
                        'instalment_orders': int((instalments > 1).sum()),
                        'instalment_share': _ratio((instalments > 1).sum(), len(instalments)),
                        'average_installments': float(instalments.mean()) if len(instalments) else None,
                        'cancelled_orders': int(rows['order_status'].isin(EXCLUDED_STATUSES).sum()),
                        'cancellation_rate': float(rows['order_status'].isin(EXCLUDED_STATUSES).mean())})
        for kind, count in paid['payment_type'].value_counts().items():
            predominant.append({'month': month, 'payment_type': kind, 'orders': int(count), 'share': _ratio(count, len(paid))})
    # Join each payment to exactly one order's month, never to order items.
    joined = raw.merge(scoped[['order_id', 'month']], on='order_id', how='inner', validate='many_to_one')
    for month, rows in joined.groupby('month'):
        total = rows['payment_value'].sum()
        for kind, group in rows.groupby('payment_type'):
            value = float(group['payment_value'].sum())
            mix.append({'month': month, 'payment_type': kind, 'payment_total': value,
                        'payment_rows': len(group), 'share': _ratio(value, total)})
    result = _base(monthly=monthly, payment_mix=mix, predominant_mix=predominant)
    result['limitations'] += [
        'Customer payments are not seller settlement or cash balance. Payment mix is share of recorded payment value.',
        'Predominant mix assigns each order to its single largest payment row; instalments use the maximum per order.',
        'Cancellation includes canceled and unavailable orders. Average order value excludes these statuses and missing item values.',
    ]
    return result


def _freight_row(rows):
    eligible = rows[rows['total_price'].notna() & rows['total_freight'].notna()]
    sales, freight_value = float(eligible['total_price'].sum()), float(eligible['total_freight'].sum())
    return {'orders': len(eligible), 'sales': sales, 'freight': freight_value, 'freight_share': _ratio(freight_value, sales)}


def freight(frame):
    scoped = _scope(frame, sales=True)
    monthly = [{'month': month, **_freight_row(rows)} for month, rows in scoped.groupby('month')]
    current = monthly[-1]['month'] if monthly else None
    previous = str(pd.Period(current, freq='M') - 1) if current else None
    result = _base(monthly=monthly, current_period=current, previous_period=previous)
    for key, column in [('categories', 'category'), ('states', 'customer_state')]:
        result[key] = []
        for name, rows in scoped.groupby(column):
            now = _freight_row(rows[rows['month'] == current])
            before = _freight_row(rows[rows['month'] == previous])['freight_share']
            share = now['freight_share']
            change = share - before if share is not None and before is not None else None
            result[key].append({'name': str(name), **now, 'previous_share': before,
                                'change_pp': change * 100 if change is not None else None,
                                'relative_change': _ratio(change, before) if change is not None else None,
                                'rising': change is not None and change > 0})
    result['limitations'] += [ASSIGNMENT, 'Freight share is freight divided by gross item sales, not total payment. Rising means greater than the previous calendar month; it is not a causal finding.']
    return result


def cohorts(frame):
    scoped = _scope(frame, sales=True)
    known = scoped.dropna(subset=['customer_unique_id', 'purchase_ts'])
    end = scoped['purchase_ts'].max()
    customers = known.groupby('customer_unique_id')['purchase_ts'].agg(first='min', last='max')
    customers['cohort'] = customers['first'].dt.strftime('%Y-%m')
    customers['returned'] = customers['last'] > customers['first']
    rows = []
    for month, group in customers.groupby('cohort'):
        followup = pd.Period(end, freq='M').ordinal - pd.Period(month, freq='M').ordinal
        rows.append({'cohort': month, 'customers': len(group), 'returning_customers': int(group['returned'].sum()),
                     'returning_share': float(group['returned'].mean()), 'followup_months': followup,
                     'incomplete': followup < 3})
    result = _base(rows=rows, observation_end=str(end) if pd.notna(end) else None,
                   missing_customer_ids=int(scoped['customer_unique_id'].isna().sum()), minimum_followup_months=3)
    result['limitations'] += ['Cohorts use customer_unique_id and the first observed non-cancelled purchase in the analysis range; earlier lifetime purchases are unknown.',
                              'Repeat requires a strictly later purchase timestamp. Cohorts with fewer than three calendar months of follow-up are marked incomplete; follow-up is unequal for all cohorts.']
    return result


def _outcomes(rows):
    late = rows.loc[rows['order_status'].eq('delivered') & rows['order_delivered_customer_date'].notna()
                    & rows['order_estimated_delivery_date'].notna(), 'late'].dropna()
    reviews = rows['low_review'].dropna()
    return {'orders': len(rows), 'sales': float(rows['total_price'].sum()),
            'delivery_orders': len(late), 'late_orders': int(late.sum()), 'late_rate': _ratio(late.sum(), len(late)),
            'reviewed_orders': len(reviews), 'low_review_orders': int(reviews.sum()),
            'low_review_rate': _ratio(reviews.sum(), len(reviews))}


def entities(frame):
    scoped = _scope(frame, sales=True)
    result = _base()
    for key, column in [('categories', 'category'), ('sellers', 'seller_id')]:
        result[key] = sorted([{'name': str(name), 'orders': len(rows), 'sales': float(rows['total_price'].sum())}
                              for name, rows in scoped.groupby(column)], key=lambda row: -row['sales'])
    result['limitations'].append(ASSIGNMENT)
    return result


def entity_detail(frame, kind, name):
    column = {'category': 'category', 'seller': 'seller_id'}.get(kind)
    if column is None or not frame[column].eq(name).any():
        return None
    scoped = _scope(frame, sales=True)
    rows = scoped[scoped[column].eq(name)]
    result = _base(kind=kind, name=name, summary=_outcomes(rows),
                   monthly=[{'month': month, **_outcomes(group)} for month, group in rows.groupby('month')],
                   business_monthly=[{'month': month, **_outcomes(group)} for month, group in scoped.groupby('month')],
                   minimum_orders=30, small_sample=len(rows) < 30)
    result['limitations'] += [ASSIGNMENT, 'Outcome rates use known outcomes only. Recent delivery outcomes may be incomplete; monthly samples below 30 orders are small.']
    return result


def model_cards(models, hashes):
    rows = []
    for name in MODEL_NAMES:
        command = 'python -m app.forecast.train' if name == SALES_MODEL else (
            'python -m app.models.train_cashflow' if name == CASHFLOW_MODEL else 'python -m app.models.train_risk')
        model, metadata = models.get(name, (None, None))
        metadata = metadata or {}
        evaluation = metadata.get('evaluation', {})
        beats = None
        rule = 'ROC-AUC > 0.5 and average precision > held-out positive base rate.'
        if name == SALES_MODEL:
            score = evaluation.get('model', {}).get('mae')
            baselines = [evaluation.get(key, {}).get('mae') for key in ('naive_last', 'mean_last_3')]
            beats = score < min(baselines) if score is not None and all(v is not None for v in baselines) else None
            rule = 'Model MAE must be below both saved baseline MAEs.'
        elif name == CASHFLOW_MODEL:
            score = evaluation.get('roc_auc')
            beats = score >= .6 if score is not None else None
            rule = 'Cash-flow ranking requires held-out ROC-AUC >= 0.6.'
        elif all(evaluation.get(k) is not None for k in ('roc_auc', 'average_precision', 'base_rate')):
            beats = evaluation['roc_auc'] > .5 and evaluation['average_precision'] > evaluation['base_rate']
        stale = any(hashes.get(k) != v for k, v in metadata.get('dataset_hashes', {}).items())
        status = 'not_trained' if model is None else ('stale' if stale else ('ready' if beats else 'evaluation_only'))
        rows.append({**metadata, 'name': name, 'status': status, 'train_command': command,
                     'trained_at': metadata.get('trained_at'), 'evaluation': evaluation,
                     'beats_baseline': beats, 'predictions_available': status == 'ready',
                     'baseline_rule': rule, 'limitations': metadata.get('limitations', [])})
    return _base(rows=rows)
