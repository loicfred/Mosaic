// The Sales page: draw sales by month with the forecast, and the charts under the suggestion and caveat tabs.
// Every figure comes from the API with the page or with a tab's answer; nothing is calculated here.
(() => {
  const chart = (...args) => MosaicPanels.chart(...args);
  const label = code => String(code).replace(/_/g, ' ');
  const monthly = (points, key) => points.map(p => ({ month: p.month, value: p[key] }));
  function adviceCharts(box, e) {
    const top = ((e && e.candidates) || []).slice(0, 3);
    if (!top.length) return;
    chart(box, 'Monthly sales of the suggested categories',
      'Recorded sales (item prices in $, before freight). Each was suggested because its sales rose over the last 3 months against the 3 before, at least as fast as the whole business.',
      id => MosaicCharts.lines(id, top.map(c => ({ label: label(c.category), points: monthly(c.series, 'sales') })), 'brl'));
    const own = k => top.map(c => c.checks[k].rate), business = k => e.business_rates && e.business_rates[k] ? e.business_rates[k].rate : null;
    chart(box, 'Late deliveries and low reviews against the whole business',
      'Last 3 months. A category counts as ready only when both rates are no more than ' + e.rules.rate_tolerance_pp + ' points worse than the business. A missing bar means too few orders to judge.',
      id => MosaicCharts.bars(id, top.map(c => label(c.category)).concat('Whole business'), [
        { label: 'Late-delivery rate', values: own('late_rate').concat(business('late_rate')), color: '--series-2' },
        { label: 'Low-review rate (1 or 2 stars)', values: own('low_review_rate').concat(business('low_review_rate')), color: '--series-3' }
      ], 'rate'));
    const profiled = top.filter(c => c.profile), whole = e.business_profile && e.business_profile.recent;
    if (!profiled.length || !whole) return;
    const names = profiled.map(c => label(c.category)).concat('Whole business'), rows = profiled.map(c => c.profile.recent).concat(whole);
    const share = (p, k) => p[k] ? p[k].rate : null;
    chart(box, 'How customers buy and pay in these categories',
      'Last 3 months, orders by the category of their priciest item. Freight is what customers paid for shipping as a share of item prices; instalments show how customers paid, not when sellers were paid.',
      id => MosaicCharts.bars(id, names, [
        { label: 'Freight share of item prices', values: rows.map(p => p.freight_share), color: '--series-1' },
        { label: 'Paid in more than one instalment', values: rows.map(p => share(p, 'multi_instalment')), color: '--series-2' },
        { label: 'From a returning customer', values: rows.map(p => share(p, 'returning_customer')), color: '--series-3' },
        { label: 'Cancelled or unavailable', values: rows.map(p => share(p, 'cancel')), color: '--series-4' }
      ], 'rate'));
    chart(box, 'Average order value, last 3 months against the 3 before',
      'Observed item sales per order in $. A basket falling by ' + Math.abs(e.rules.basket_fall_pct) + '% or more marks the category to watch: its growth is coming from more orders, not bigger ones.',
      id => MosaicCharts.bars(id, names, [
        { label: '3 months before', values: profiled.map(c => c.profile.previous.average_order_value).concat(e.business_profile.previous.average_order_value), color: '--chart-baseline' },
        { label: 'Last 3 months', values: rows.map(p => p.average_order_value), color: '--series-2' }
      ], 'brl'));
    chart(box, 'How much of the sales the biggest seller makes',
      'Last 3 months. When one seller makes ' + Math.round(e.rules.single_seller_share * 100) + '% or more of a category\'s sales, growth there depends on that seller, so the category is marked to watch.',
      id => MosaicCharts.bars(id, names, [
        { label: 'Biggest seller\'s share of sales', values: rows.map(p => p.top_seller_share), color: '--series-1' }
      ], 'rate'));
  }
  function caveatCharts(box, e) {
    const checks = Object.fromEntries(((e && e.checks) || []).map(c => [c.id, c]));
    const falling = checks.categories_falling_behind, late = checks.late_rate_rising, low = checks.low_reviews_rising,
       hurt = checks.late_orders_get_low_reviews;
    if (falling && falling.triggered)
      chart(box, 'The categories falling furthest behind',
        'Recorded monthly sales (item prices in $, before freight) of the categories that lost the most over the last 3 months against the 3 before.',
        id => MosaicCharts.lines(id, falling.evidence.worst.map(c => ({ label: label(c.category), points: monthly(c.series, 'sales') })), 'brl'));
    if ((late && late.triggered) || (low && low.triggered))
      chart(box, 'Late deliveries and low reviews by month',
        'Share of delivered orders that arrived late, and of reviewed orders rated 1 or 2 stars. The caveat compares the last 3 months with the 3 before.',
        id => MosaicCharts.lines(id, [
          { label: 'Late-delivery rate', points: monthly(late.evidence.monthly, 'late_rate'), color: '--series-2' },
          { label: 'Low-review rate', points: monthly(low.evidence.monthly, 'low_rate'), color: '--series-3' }
        ], 'rate'));
    if (hurt && hurt.triggered)
      chart(box, 'Low reviews on late and on-time orders',
        'Share of reviewed orders rated 1 or 2 stars. It shows the two go together, not that lateness is the only cause.',
        id => MosaicCharts.bars(id, ['Late orders', 'On-time orders'], [
          { label: 'Low-review rate', values: [hurt.evidence.late.low_rate, hurt.evidence.on_time.low_rate], color: '--series-3' }
        ], 'rate'));
    // the business-wide checks: each triggered one draws its monthly series, the last 3 months being the ones compared
    const trends = [
      ['cancellations_rising', 'Cancelled or unavailable orders by month', 'Share of all orders placed.', 'cancel_rate', 'rate'],
      ['basket_shrinking', 'Average order value by month', 'Observed item sales per order in $.', 'average_order_value', 'brl'],
      ['freight_share_rising', 'Freight as a share of item prices by month', 'What customers paid for shipping against what they paid for the items.', 'freight_share', 'rate'],
      ['instalments_rising', 'Orders paid in more than one instalment by month', 'How customers paid, not when sellers were paid.', 'multi_instalment_rate', 'rate'],
      ['few_returning_customers', 'Orders from returning customers by month', 'Share of orders from someone who had ordered before in this data.', 'returning_rate', 'rate']
    ];
    trends.forEach(([id, title, caption, key, unit]) => {
      const check = checks[id];
      if (check && check.triggered)
        chart(box, title, caption + ' The caveat compares the last 3 months with the 3 before.',
          chartId => MosaicCharts.lines(chartId, [{ label: title.replace(' by month', ''), points: monthly(check.evidence.monthly, key), color: '--series-2' }], unit));
    });
    const sellers = checks.sales_rest_on_few_sellers, state = checks.sales_rest_on_one_state;
    if ((sellers && sellers.triggered) || (state && state.triggered))
      chart(box, 'How concentrated the recent sales are',
        'Last 3 months: the top ' + sellers.evidence.top_sellers + ' sellers\' share of sales, and the biggest customer state (' + state.evidence.state + ').',
        chartId => MosaicCharts.bars(chartId, ['Top ' + sellers.evidence.top_sellers + ' sellers', 'Customers in ' + state.evidence.state], [
          { label: 'Share of sales', values: [sellers.evidence.share, state.evidence.share], color: '--series-1' }
        ], 'rate'));
  }

  window.MosaicSales = {
    page(months, forecast) {
      MosaicCharts.sales('sales-chart', months, forecast);
      MosaicPanels.bind({ 'advice-panel': adviceCharts, 'caveats-panel': caveatCharts });
    }
  };
})();
