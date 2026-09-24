package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Measure;
import mu.mosaic.opportunity.obj.api.BuyingTimes;
import mu.mosaic.opportunity.obj.api.Categories;
import mu.mosaic.opportunity.obj.api.CategoryDetail;
import mu.mosaic.opportunity.obj.api.CustomerStates;
import mu.mosaic.opportunity.obj.api.DeliverySellers;
import mu.mosaic.opportunity.obj.api.DeliverySummary;
import mu.mosaic.opportunity.obj.api.Economy;
import mu.mosaic.opportunity.obj.api.Events;
import mu.mosaic.opportunity.obj.api.Monthly;
import mu.mosaic.opportunity.obj.api.ReviewScores;
import mu.mosaic.opportunity.obj.api.ReviewSummary;
import mu.mosaic.opportunity.obj.api.SalesForecast;
import mu.mosaic.opportunity.obj.api.SalesHistory;
import mu.mosaic.opportunity.obj.api.SalesMetrics;
import mu.mosaic.opportunity.obj.api.SalesMix;
import mu.mosaic.opportunity.obj.api.Scenario;
import mu.mosaic.opportunity.obj.api.ScoredOrders;
import mu.mosaic.opportunity.obj.api.TrendFigures;
import mu.mosaic.opportunity.service.Formatter;
import mu.mosaic.opportunity.service.MosaicApi;
import org.solarframework.ai.AITool;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * What the follow-up chat may look up: read-only calls to the analytics API, answered as short text formatted the
 * way the site shows it, so the model quotes figures instead of working them out. No tool writes anything, runs a
 * query of its own or reaches beyond the API; arguments are checked before any call. A figure in a reply is allowed
 * because a tool returned it, so every tool labels what its figures are: observed, predicted, hypothetical or
 * external context.
 * <p>Each tool that has a series also records a chart of the same API reply, which the page draws under the answer;
 * so one instance serves one question and is never shared.
 */
public class PanelTools {
    private static final int MAX_ROWS = 10;
    private static final Pattern MONTH = Pattern.compile("\\d{4}-\\d{2}");
    private static final Pattern CATEGORY = Pattern.compile("[a-z0-9_]{1,60}");
    // Chart kinds that suit each shape of data; the first is drawn unless the question asks for another of them.
    private static final List<String> TIME_KINDS = List.of("line", "area", "bar"), COMPARE_KINDS = List.of("bar", "hbar"),
            PARTS_KINDS = List.of("doughnut", "pie", "bar", "hbar");
    private final MosaicApi api;
    private final Formatter fmt;
    private final Panels panels;
    private final List<Map<String, Object>> charts = new ArrayList<>();

    public PanelTools(MosaicApi api, Formatter fmt, Panels panels) {
        this.api = api;
        this.fmt = fmt;
        this.panels = panels;
    }

    /** The charts of the tools called so far, in call order: {shape, kind, kinds, title, caption, unit, ...}. */
    public List<Map<String, Object>> charts() { return List.copyOf(charts); }

    /** The tools the chat may call: exactly the annotated methods below. */
    public Set<String> names() {
        return Arrays.stream(getClass().getMethods()).filter(m -> m.isAnnotationPresent(AITool.class)).map(m -> m.getName()).collect(Collectors.toSet());
    }

    @AITool(description = "Observed monthly gross item sales (BRL) and order counts for the last `months` months (1 to 20). Use for how sales moved.")
    public String salesHistory(int months) {
        ApiResult r = api.salesHistory();
        if (r.failed()) return "Not available right now: " + r.error();
        List<SalesHistory.Month> all = r.as(SalesHistory.class).months();
        List<SalesHistory.Month> shown = all.subList(Math.max(0, all.size() - Math.max(1, Math.min(months, all.size()))), all.size());
        StringBuilder out = new StringBuilder("Observed monthly sales (gross item sales in BRL, not profit):\n");
        shown.forEach(m -> out.append("- ").append(m.month()).append(": ").append(fmt.brl(m.sales())).append(", ").append(fmt.num(m.orders(), 0)).append(" orders\n"));
        lines("Monthly sales", "Recorded sales: item prices in BRL, before freight.", "brl", series("Sales, observed", shown, SalesHistory.Month::sales));
        return out.toString().strip();
    }

    @AITool(description = "The sales forecast for the next `months` months (1 to 6) with its range, the method used, and how its past predictions compared with simple rules. Predicted, not a promise.")
    public String salesForecast(int months) {
        ApiResult r = api.salesForecast(Math.max(1, Math.min(months, 6)));
        if (r.failed()) return "Not available right now: " + r.error();
        SalesForecast f = r.as(SalesForecast.class);
        StringBuilder out = new StringBuilder("Sales forecast (predicted, not a promise; method " + f.forecastMethod() + "):\n");
        f.forecast().forEach(p -> out.append("- ").append(p.month()).append(": ").append(fmt.brl(p.sales()))
                .append(" (range ").append(fmt.brl(p.lower())).append(" to ").append(fmt.brl(p.upper())).append(")\n"));
        ApiResult history = api.salesHistory();
        List<SalesHistory.Month> observed = history.failed() ? List.of() : history.as(SalesHistory.class).months();
        lines("Sales and the forecast", "Observed sales for the last 12 months, then the forecast and its range (predicted, not a promise).", "brl",
                series("Sales, observed", observed.subList(Math.max(0, observed.size() - 12), observed.size()), SalesHistory.Month::sales),
                series("Forecast", f.forecast(), SalesForecast.Point::sales), range(series("Forecast low", f.forecast(), SalesForecast.Point::lower)),
                range(series("Forecast high", f.forecast(), SalesForecast.Point::upper)));
        SalesForecast.Evaluation e = f.evaluation();
        return out.append("Average miss on past months: model ").append(fmt.brl(e.model().mae()))
                .append(", 'same as last month' ").append(fmt.brl(e.naiveLast().mae()))
                .append(", 'average of last 3 months' ").append(fmt.brl(e.meanLast3().mae())).append('.').toString();
    }

    @AITool(description = "Product categories with sales in the last 3 months against the 3 before (observed). filter: 'all', 'falling_behind' (fell well behind the business) or 'unusual_month' (latest month far from usual).")
    public String listCategories(String filter) {
        String flag = switch (Objects.toString(filter, "").strip().toLowerCase(Locale.ROOT)) {
            case "falling_behind" -> "underperforming_total";
            case "unusual_month" -> "latest_month_anomaly";
            default -> null;
        };
        ApiResult r = api.categories(flag, MAX_ROWS);
        if (r.failed()) return "Not available right now: " + r.error();
        Categories c = r.as(Categories.class);
        StringBuilder out = new StringBuilder("Whole business " + fmt.pct(c.totalChangePct()) + " (last 3 months against the 3 before). "
                + c.count() + " categories match; the largest " + MAX_ROWS + " by recent sales:\n");
        bars("Categories, last 3 months against the 3 before", "Recorded sales: item prices in BRL, before freight.", "brl",
                c.categories().stream().map(x -> x.category().replace('_', ' ')).toList(),
                Map.of("label", "3 months before", "values", c.categories().stream().map(Categories.Category::previous).toList()), Map.of("label", "Last 3 months", "values", c.categories().stream().map(Categories.Category::recent).toList()));
        c.categories().forEach(x -> out.append("- ").append(x.category()).append(": ")
                .append(fmt.brl(x.recent())).append(" recent against ").append(fmt.brl(x.previous())).append(" before (")
                .append(fmt.pct(x.changePct())).append("), ").append(fmt.rate(x.shareRecent(), 1)).append(" of sales\n"));
        return out.toString().strip();
    }

    @AITool(description = "One product category's observed sales, change, share of the business, flags and short forecast. category is its code, e.g. 'housewares' or 'health_beauty'.")
    public String categoryDetails(String category) {
        String code = Objects.toString(category, "").strip().toLowerCase(Locale.ROOT).replace(' ', '_');
        if (!CATEGORY.matcher(code).matches()) return "Not looked up: give a category code such as 'housewares'.";
        ApiResult r = api.category(code);
        if (r.failed()) return "Not available right now: " + r.error();
        CategoryDetail c = r.as(CategoryDetail.class);
        StringBuilder out = new StringBuilder(code + " (observed): " + fmt.brl(c.recent()) + " in the last 3 months against " + fmt.brl(c.previous())
                + " in the 3 before (" + fmt.pct(c.changePct()) + "); the whole business " + fmt.pct(c.totalChangePct())
                + ". Share of sales " + fmt.rate(c.shareRecent(), 1) + " against " + fmt.rate(c.sharePrevious(), 1) + " before.\n")
                .append("Falling well behind the business: ").append(c.flags().underperformingTotal() ? "yes" : "no")
                .append(". Latest month unusual: ").append(c.flags().latestMonthAnomaly() ? "yes" : "no").append(".\n");
        lines(code.replace('_', ' ') + ": monthly sales", "Recorded sales (item prices in BRL, before freight), then its short forecast (predicted).", "brl",
                series("Sales, observed", c.series(), CategoryDetail.Point::sales), series("Forecast", c.forecast(), CategoryDetail.Point::sales));
        if (!c.forecast().isEmpty()) {
            out.append("Short forecast (predicted, not a promise):\n");
            c.forecast().forEach(p -> out.append("- ").append(p.month()).append(": ").append(fmt.brl(p.sales())).append('\n'));
        }
        return out.toString().strip();
    }

    @AITool(description = "Hypothetical scenario: what a sales change of salesChangePct percent (-50 to 100) for `months` months (1 to 6) would mean for orders, late deliveries, low reviews and sellers pushed past their busiest month. Recent rates applied forward; not a forecast.")
    public String whatIfSalesChange(double salesChangePct, int months) {
        if (salesChangePct < -50 || salesChangePct > 100 || months < 1 || months > 6)
            return "Not run: the sales change must be between -50 and 100 percent and the months between 1 and 6.";
        ApiResult r = api.salesImpact(months, salesChangePct);
        if (r.failed()) return "Not available right now: " + r.error();
        Scenario s = r.as(Scenario.class);
        Scenario.Consequences c = s.consequences();
        if (c == null) return "No scenario: there were no sales in the recent months to start from.";
        Scenario.LateCase held = c.late().rateHeld();
        Scenario.Capacity capacity = c.sellersAtCapacity();
        bars("Orders a month: recent against the scenario", "Hypothetical: recent rates applied forward, not a forecast.", "count",
                List.of("Recent average", "Scenario"), Map.of("label", "Orders a month",
                        "values", Arrays.asList(s.baseline().monthlyOrders(), c.projectedMonthlyOrders())));
        return ("Hypothetical, sales " + fmt.pct(salesChangePct) + " for " + months + " months (recent rates applied forward, not a forecast):\n"
                + "- " + fmt.brl(c.projectedMonthlySales()) + " and " + fmt.num(c.projectedMonthlyOrders(), 0) + " orders a month ("
                + fmt.change(c.extraOrdersPerMonth()) + " orders on the recent average)\n"
                + "- at the recent late rate of " + fmt.rate(held.lateRate(), 1) + ": " + fmt.num(held.expectedLatePerMonth(), 0)
                + " late deliveries and " + fmt.num(held.expectedLowReviewsPerMonth(), 0) + " low reviews a month\n"
                + "- " + fmt.num(capacity.count(), 0) + " of " + fmt.num(capacity.activeSellers(), 0)
                + " active sellers would handle more orders in a month than they ever have").strip();
    }

    @AITool(description = "How one measure moved, last 3 months against the 3 before (observed). measure: 'delivery' (late-delivery rate), 'reviews' (low-review rate) or 'sellers' (active sellers).")
    public String measureTrend(String measure) {
        var m = Measure.fromPath(Objects.toString(measure, "").strip().toLowerCase(Locale.ROOT));
        if (m.isEmpty()) return "Not looked up: measure must be 'delivery', 'reviews' or 'sellers'.";
        ApiResult r = api.trend(m.get());
        if (r.failed()) return "Not available right now: " + r.error();
        TrendFigures t = r.as(TrendFigures.class);
        lines(t.label() + " by month", "Observed; the comparison is the last 3 months against the 3 before.", t.unit(),
                series(t.label(), t.monthly(), mv -> mv.value()));
        return t.label() + " (observed): " + fmt.unit(t.unit(), t.trend().recentValue()) + " in the last 3 months against "
                + fmt.unit(t.unit(), t.trend().previousValue()) + " in the 3 before (" + fmt.unitChange(t.trend()) + "); " + t.better() + " is better.";
    }

    @AITool(description = "The suggestion for a topic, with every candidate's figures and checks. topic: 'sales' (where to invest), 'delivery', 'reviews' or 'sellers'.")
    public String suggestion(String topic) { return panelEvidence(topic, "advice"); }

    @AITool(description = "The caveat checks for a topic, found and clear, with their figures. topic: 'sales', 'delivery', 'reviews' or 'sellers'.")
    public String caveats(String topic) { return panelEvidence(topic, "caveats"); }

    @AITool(description = "Observed late-delivery rate for the last 6 months, and how often late and on-time orders get a 1 or 2 star review.")
    public String deliveryAndReviews() {
        ApiResult delivery = api.deliverySummary(), reviews = api.reviewSummary();
        if (delivery.failed()) return "Not available right now: " + delivery.error();
        List<DeliverySummary.Month> months = delivery.as(DeliverySummary.class).monthly();
        lines("Late-delivery rate by month", "Share of delivered orders that arrived after the promised date (observed).", "rate",
                series("Late-delivery rate", months.subList(Math.max(0, months.size() - 12), months.size()), DeliverySummary.Month::lateRate));
        StringBuilder out = new StringBuilder("Late-delivery rate of delivered orders (observed):\n");
        months.subList(Math.max(0, months.size() - 6), months.size()).forEach(m -> out.append("- ").append(m.month()).append(": ")
                .append(fmt.rate(m.lateRate(), 1)).append(" (").append(fmt.num(m.late(), 0)).append(" of ").append(fmt.num(m.delivered(), 0)).append(")\n"));
        if (!reviews.failed()) {
            ReviewSummary.ByLateness by = reviews.as(ReviewSummary.class).byLateness();
            bars("Low reviews on late and on-time orders", "Share rated 1 or 2 stars (observed); they go together, not proof of cause.", "rate",
                    List.of("Late orders", "On-time orders"), Map.of("label", "Low-review rate",
                            "values", Arrays.asList(by.late().lowRate(), by.onTime().lowRate())));
            out.append("Rated 1 or 2 stars: late orders ").append(fmt.rate(by.late().lowRate(), 1))
                    .append(", on-time orders ").append(fmt.rate(by.onTime().lowRate(), 1))
                    .append(" (they go together; not proof of cause).");
        }
        return out.toString().strip();
    }

    @AITool(description = "Sellers with at least 30 delivered orders who deliver late most often (observed), with their late rate.")
    public String leastReliableSellers() {
        ApiResult r = api.deliverySellers(30, MAX_ROWS);
        if (r.failed()) return "Not available right now: " + r.error();
        List<DeliverySellers.Seller> sellers = r.as(DeliverySellers.class).sellers();
        bars("Sellers delivering late most often", "Late-delivery rate of each seller's delivered orders (observed).", "rate",
                sellers.stream().map(DeliverySellers.Seller::shortId).toList(), Map.of("label", "Late-delivery rate", "values", sellers.stream().map(DeliverySellers.Seller::lateRate).toList()));
        StringBuilder out = new StringBuilder("Sellers delivering late most often (observed, at least 30 delivered orders):\n");
        sellers.forEach(s -> out.append("- ").append(s.shortId()).append(": ")
                .append(fmt.rate(s.lateRate(), 1)).append(" late (").append(fmt.num(s.late(), 0)).append(" of ").append(fmt.num(s.orders(), 0)).append(")\n"));
        return out.toString().strip();
    }

    @AITool(description = "Open orders the late-delivery model rates most likely to arrive late (predicted risk, not an outcome), with category and states.")
    public String riskiestOpenOrders() {
        ApiResult r = api.openOrders(MAX_ROWS);
        if (r.failed()) return "Not available right now: " + r.error();
        ScoredOrders scored = r.as(ScoredOrders.class);
        StringBuilder out = new StringBuilder("Open orders most at risk of arriving late (model " + scored.modelVersion() + ", predicted risk):\n");
        scored.orders().forEach(o -> out.append("- ").append(o.category()).append(", ").append(o.sellerState()).append(" to ")
                .append(o.customerState()).append(": risk ").append(fmt.rate(o.risk(), 0)).append(", ").append(fmt.brl(o.totalPrice())).append('\n'));
        return out.toString().strip();
    }

    @AITool(description = "Delivered orders without a review that the low-review model rates most likely to get 1 or 2 stars (predicted risk, not an outcome).")
    public String ordersAtRiskOfLowReview() {
        ApiResult r = api.unreviewedOrders(MAX_ROWS);
        if (r.failed()) return "Not available right now: " + r.error();
        ScoredOrders scored = r.as(ScoredOrders.class);
        StringBuilder out = new StringBuilder("Unreviewed orders most at risk of a low review (model " + scored.modelVersion() + ", predicted risk):\n");
        scored.orders().forEach(o -> out.append("- ").append(o.category()).append(", ").append(o.customerState())
                .append(": risk ").append(fmt.rate(o.risk(), 0)).append(", delivered ").append(fmt.num(o.daysLate(), 0)).append(" days after the promise\n"));
        return out.toString().strip();
    }

    @AITool(description = "Brazilian public holidays, retail dates (Black Friday, Mother's Day...), strikes and sport events in a month, as outside context. month is 'YYYY-MM'.")
    public String events(String month) {
        String m = Objects.toString(month, "").strip();
        if (!MONTH.matcher(m).matches()) return "Not looked up: give the month as YYYY-MM, e.g. 2017-11.";
        ApiResult r = api.events(m);
        if (r.failed()) return "Not available right now: " + r.error();
        List<Events.Event> events = r.as(Events.class).events();
        if (events.isEmpty()) return "No listed Brazilian event in " + m + " (external context).";
        StringBuilder out = new StringBuilder("Events in " + m + " (external context, not the business's data; an event says nothing about its effect):\n");
        events.forEach(e -> out.append("- ").append(e.dates()).append(": ").append(e.name()).append(" (").append(e.kind()).append(") - ").append(e.note()).append('\n'));
        return out.toString().strip();
    }

    @AITool(description = "Brazil's economy in a month from the Central Bank, as outside context: inflation, the dollar rate, the Selic interest rate and unemployment. month is 'YYYY-MM'.")
    public String economy(String month) {
        String m = Objects.toString(month, "").strip();
        if (!MONTH.matcher(m).matches()) return "Not looked up: give the month as YYYY-MM, e.g. 2018-05.";
        ApiResult r = api.economy(m);
        if (r.failed()) return "Not available right now: " + r.error();
        Economy economy = r.as(Economy.class);
        if (!economy.available()) return "Brazil's economic figures are not downloaded on this site.";
        if (economy.months().isEmpty()) return "No Central Bank figures for " + m + ".";
        Economy.Month e = economy.months().getFirst();
        return "Brazil in " + m + " (Central Bank of Brazil, external context; national figures, not the business's): inflation (IPCA) "
                + fmt.num(e.inflationIpcaPct(), 2) + "% in the month, US dollar " + fmt.num(e.usdBrl(), 2) + " BRL, Selic target "
                + fmt.num(e.selicTargetPct(), 2) + "% a year, unemployment " + fmt.num(e.unemploymentPct(), 1) + "%.";
    }

    @AITool(description = "How the last 3 months' sales split (observed): breakdown is 'category', 'payment_type', 'customer_state' or 'seller_state'. Use for 'what share', 'mix' or pie-chart questions.")
    public String salesMix(String breakdown) {
        String by = Objects.toString(breakdown, "").strip().toLowerCase(Locale.ROOT).replace(' ', '_');
        if (!List.of("category", "payment_type", "customer_state", "seller_state").contains(by))
            return "Not looked up: breakdown must be 'category', 'payment_type', 'customer_state' or 'seller_state'.";
        ApiResult r = api.salesMix(by, 3);
        if (r.failed()) return "Not available right now: " + r.error();
        SalesMix mix = r.as(SalesMix.class);
        parts("Sales by " + by.replace('_', ' ') + ", last 3 months", "Share of recorded sales: item prices before freight, orders not cancelled.", "rate",
                mix.rows().stream().map(x -> x.group().replace('_', ' ')).toList(), Map.of("label", "Share of sales", "values", mix.rows().stream().map(SalesMix.Row::share).toList()));
        StringBuilder out = new StringBuilder("Last 3 months' sales by " + by.replace('_', ' ') + " (observed; " + fmt.brl(mix.sales()) + " in "
                + fmt.num(mix.orders(), 0) + " orders):\n");
        mix.rows().forEach(x -> out.append("- ").append(x.group().replace('_', ' ')).append(": ").append(fmt.rate(x.share(), 1)).append(" (")
                .append(fmt.brl(x.sales())).append(", ").append(fmt.num(x.orders(), 0)).append(" orders)\n"));
        return out.toString().strip();
    }

    @AITool(description = "One business measure by month (observed): metric is 'average_order_value', 'freight_share', 'cancel_rate', 'multi_instalment_rate' (paid in instalments) or 'returning_rate' (repeat customers).")
    public String businessMetricByMonth(String metric) {
        String key = Objects.toString(metric, "").strip().toLowerCase(Locale.ROOT);
        ApiResult r = api.salesMetrics();
        if (r.failed()) return "Not available right now: " + r.error();
        SalesMetrics metrics = r.as(SalesMetrics.class);
        SalesMetrics.Metric meta = metrics.metrics().get(key);
        if (meta == null) return "Not looked up: metric must be one of " + String.join(", ", metrics.metrics().keySet()) + ".";
        var months = metrics.series(key);
        var shown = months.subList(Math.max(0, months.size() - 12), months.size());
        lines(meta.label() + " by month", "Observed figures of this business.", meta.unit(), series(meta.label(), shown, mv -> mv.value()));
        StringBuilder out = new StringBuilder(meta.label() + " by month (observed):\n");
        shown.forEach(m -> out.append("- ").append(m.month()).append(": ").append(fmt.unit(meta.unit(), m.value())).append('\n'));
        return out.toString().strip();
    }

    @AITool(description = "Compare two product categories' observed monthly sales and their change over the last 3 months. Give the codes, e.g. 'housewares' and 'health_beauty'.")
    public String compareCategories(String first, String second) {
        List<CategoryDetail> found = new ArrayList<>();
        StringBuilder out = new StringBuilder();
        for (String name : List.of(Objects.toString(first, "").strip(), Objects.toString(second, "").strip())) {
            String code = name.toLowerCase(Locale.ROOT).replace(' ', '_');
            if (!CATEGORY.matcher(code).matches()) return "Not looked up: give two category codes such as 'housewares'.";
            ApiResult r = api.category(code);
            if (r.failed()) return "Not available right now: " + r.error();
            CategoryDetail c = r.as(CategoryDetail.class);
            found.add(c);
            out.append(code).append(" (observed): ").append(fmt.brl(c.recent())).append(" in the last 3 months against ")
                    .append(fmt.brl(c.previous())).append(" before (").append(fmt.pct(c.changePct())).append("), ")
                    .append(fmt.rate(c.shareRecent(), 1)).append(" of sales\n");
        }
        CategoryDetail a = found.get(0), b = found.get(1);
        lines(a.category().replace('_', ' ') + " and " + b.category().replace('_', ' '), "Recorded monthly sales: item prices in BRL, before freight.", "brl",
                series(a.category().replace('_', ' '), a.series(), CategoryDetail.Point::sales), series(b.category().replace('_', ' '), b.series(), CategoryDetail.Point::sales));
        return out.toString().strip();
    }

    @AITool(description = "One Brazilian economic indicator over every month of the data (January 2017 to August 2018), as outside context: indicator is 'inflation', 'dollar', 'interest_rate' or 'unemployment'.")
    public String economyTrend(String indicator) {
        String column = switch (Objects.toString(indicator, "").strip().toLowerCase(Locale.ROOT)) {
            case "inflation", "ipca" -> "inflation_ipca_pct";
            case "dollar", "usd", "exchange_rate" -> "usd_brl";
            case "interest_rate", "selic" -> "selic_target_pct";
            case "unemployment" -> "unemployment_pct";
            default -> null;
        };
        if (column == null) return "Not looked up: indicator must be 'inflation', 'dollar', 'interest_rate' or 'unemployment'.";
        ApiResult r = api.economy(null);
        if (r.failed()) return "Not available right now: " + r.error();
        Economy economy = r.as(Economy.class);
        if (!economy.available()) return "Brazil's economic figures are not downloaded on this site.";
        String name = String.valueOf(economy.series().get(column));
        lines(name, "Central Bank of Brazil; outside context, national figures, not the business's own.", "count",
                series(name, economy.months(), m -> m.indicator(column)));
        StringBuilder out = new StringBuilder(name + " (Central Bank of Brazil, outside context):\n");
        economy.months().forEach(m -> out.append("- ").append(m.month()).append(": ").append(fmt.num(m.indicator(column), 2)).append('\n'));
        return out.toString().strip();
    }

    @AITool(description = "Brazilian holidays, retail dates, strikes and sport events between two months, as outside context. fromMonth and toMonth are 'YYYY-MM'.")
    public String eventsBetween(String fromMonth, String toMonth) {
        String from = Objects.toString(fromMonth, "").strip(), to = Objects.toString(toMonth, "").strip();
        if (!MONTH.matcher(from).matches() || !MONTH.matcher(to).matches() || from.compareTo(to) > 0)
            return "Not looked up: give two months as YYYY-MM, the first not after the second.";
        ApiResult r = api.events(null);
        if (r.failed()) return "Not available right now: " + r.error();
        List<Events.Event> events = r.as(Events.class).events().stream().filter(e -> e.touches(from, to)).toList();
        if (events.isEmpty()) return "No listed Brazilian event between " + from + " and " + to + " (external context).";
        StringBuilder out = new StringBuilder("Events between " + from + " and " + to + " (external context; an event says nothing about its effect):\n");
        events.forEach(e -> out.append("- ").append(e.dates()).append(": ").append(e.name()).append(" (").append(e.kind()).append(")\n"));
        return out.toString().strip();
    }

    @AITool(description = "When customers buy (observed, all months): by is 'weekday' or 'hour'. Returns orders, sales and the share of orders per slot.")
    public String buyingTimes(String by) {
        String slot = Objects.toString(by, "").strip().toLowerCase(Locale.ROOT);
        if (!List.of("weekday", "hour").contains(slot)) return "Not looked up: by must be 'weekday' or 'hour'.";
        ApiResult r = api.buyingTimes(slot);
        if (r.failed()) return "Not available right now: " + r.error();
        List<BuyingTimes.Slot> slots = r.as(BuyingTimes.class).slots();
        bars("Orders by " + slot, "Observed orders, January 2017 to August 2018.", "count",
                slots.stream().map(BuyingTimes.Slot::slot).toList(), Map.of("label", "Orders", "values", slots.stream().map(BuyingTimes.Slot::orders).toList()));
        StringBuilder out = new StringBuilder("Orders by " + slot + " (observed, all months):\n");
        slots.forEach(s -> out.append("- ").append(s.slot()).append(": ").append(fmt.num(s.orders(), 0)).append(" orders, ")
                .append(fmt.rate(s.shareOfOrders(), 1)).append(" of all\n"));
        return out.toString().strip();
    }

    @AITool(description = "Customer states compared (observed, all months, the 10 with most orders): measure is 'orders', 'late_rate', 'average_delivery_days' or 'low_review_rate'.")
    public String customerStates(String measure) {
        String key = Objects.toString(measure, "").strip().toLowerCase(Locale.ROOT);
        String unit = switch (key) {
            case "orders" -> "count";
            case "late_rate", "low_review_rate" -> "rate";
            case "average_delivery_days" -> "days";
            default -> null;
        };
        if (unit == null) return "Not looked up: measure must be 'orders', 'late_rate', 'average_delivery_days' or 'low_review_rate'.";
        ApiResult r = api.customerStates();
        if (r.failed()) return "Not available right now: " + r.error();
        List<CustomerStates.State> states = r.as(CustomerStates.class).states();
        List<CustomerStates.State> top = states.subList(0, Math.min(MAX_ROWS, states.size()));
        bars(key.replace('_', ' ') + " by customer state", "Observed, the 10 states with the most orders; a missing bar means too few orders to judge.", unit,
                top.stream().map(CustomerStates.State::state).toList(), Map.of("label", key.replace('_', ' '), "values", top.stream().map(s -> s.measure(key)).toList()));
        StringBuilder out = new StringBuilder("Customer states with the most orders (observed, all months):\n");
        top.forEach(s -> out.append("- ").append(s.state()).append(": ").append(fmt.num(s.orders(), 0)).append(" orders, late ")
                .append(fmt.rate(s.lateRate(), 1)).append(", ").append(fmt.num(s.averageDeliveryDays(), 1)).append(" days to deliver, low reviews ")
                .append(fmt.rate(s.lowReviewRate(), 1)).append('\n'));
        return out.toString().strip();
    }

    @AITool(description = "How orders are rated (observed, all months): how many orders got 1, 2, 3, 4 and 5 stars, and their share.")
    public String reviewScores() {
        ApiResult r = api.reviewScores();
        if (r.failed()) return "Not available right now: " + r.error();
        List<ReviewScores.Score> scores = r.as(ReviewScores.class).scores();
        parts("Orders by review score", "Latest review per order (observed).", "rate",
                scores.stream().map(s -> s.score() + " star" + ("1".equals(s.score()) ? "" : "s")).toList(), Map.of("label", "Share of reviewed orders", "values", scores.stream().map(ReviewScores.Score::share).toList()));
        StringBuilder out = new StringBuilder("Review scores (observed, latest review per order):\n");
        scores.forEach(s -> out.append("- ").append(s.score()).append(" stars: ").append(fmt.num(s.orders(), 0)).append(" orders, ")
                .append(fmt.rate(s.share(), 1)).append('\n'));
        return out.toString().strip();
    }

    private String panelEvidence(String topic, String kind) {
        return panels.find(Objects.toString(topic, "").strip().toLowerCase(Locale.ROOT), kind).map(panel -> {
            ApiResult figures = panel.figures();
            return figures.failed() ? "Not available right now: " + figures.error() : panel.evidence(figures);
        }).orElse("Not looked up: topic must be 'sales', 'delivery', 'reviews' or 'sellers'.");
    }

    /** Values over months: one line per series. */
    @SafeVarargs
    private void lines(String title, String caption, String unit, Map<String, Object>... series) {
        List<Map<String, Object>> drawn = Arrays.stream(series).filter(s -> !((List<?>) s.get("points")).isEmpty()).toList();
        if (!drawn.isEmpty()) charts.add(chart("time", TIME_KINDS, title, caption, unit, Map.of("series", drawn)));
    }

    /** Values compared across labels (categories, sellers, periods); a pie would imply they add up to a whole, so none is offered. */
    @SafeVarargs
    private void bars(String title, String caption, String unit, List<String> labels, Map<String, Object>... series) {
        if (!labels.isEmpty()) charts.add(chart("categories", COMPARE_KINDS, title, caption, unit, Map.of("labels", labels, "series", List.of(series))));
    }

    /** The parts of one whole (sales by payment type, orders by star rating), so a pie or doughnut is honest here. */
    private void parts(String title, String caption, String unit, List<String> labels, Map<String, Object> series) {
        if (!labels.isEmpty()) charts.add(chart("categories", PARTS_KINDS, title, caption, unit, Map.of("labels", labels, "series", List.of(series))));
    }

    private Map<String, Object> chart(String shape, List<String> kinds, String title, String caption, String unit, Map<String, Object> data) {
        Map<String, Object> chart = new LinkedHashMap<>(Map.of("shape", shape, "kind", kinds.getFirst(), "kinds", kinds,
                "title", title, "caption", caption, "unit", unit));
        chart.putAll(data);
        return chart;
    }

    /** One line: each row's month and value; a missing value stays a gap. */
    private <T extends Monthly> Map<String, Object> series(String label, List<T> rows, Function<T, Double> value) {
        List<Map<String, Object>> points = new ArrayList<>();
        for (T row : rows) {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("month", row.month());
            point.put("value", value.apply(row));
            points.add(point);
        }
        return Map.of("label", label, "points", points);
    }

    /** A forecast's low or high edge: drawn as a thin dashed line, and left out when the chart is shown as bars. */
    private Map<String, Object> range(Map<String, Object> series) {
        Map<String, Object> edge = new LinkedHashMap<>(series);
        edge.put("range", true);
        return edge;
    }
}
