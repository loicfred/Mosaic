package mu.mosaic.opportunity.obj.api;

import java.util.List;

/** Brazilian holidays, retail dates, strikes and sport events: outside context, not the business's data. */
public record Events(List<Event> events) {

    public record Event(String start, String end, String name, String kind, String note) {

        public String dates() { return start.equals(end) ? start : start + " to " + end; }

        /** Whether the event touches any month from {@code from} to {@code to}, both "YYYY-MM". */
        public boolean touches(String from, String to) { return end.substring(0, 7).compareTo(from) >= 0 && start.substring(0, 7).compareTo(to) <= 0; }
    }
}
