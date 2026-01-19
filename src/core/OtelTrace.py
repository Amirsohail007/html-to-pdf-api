try:
    from opentelemetry import trace

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class OtelTrace:
    @staticmethod
    def get_current_trace_id() -> str:
        if OTEL_AVAILABLE:
            try:
                current_span = trace.get_current_span()
                if current_span and current_span.is_recording():
                    span_context = current_span.get_span_context()
                    if span_context.trace_id != 0:
                        return format(span_context.trace_id, "032x")
            except Exception:
                pass
        return "N/A"

    @staticmethod
    def get_current_span_id() -> str:
        if OTEL_AVAILABLE:
            try:
                current_span = trace.get_current_span()
                if current_span and current_span.is_recording():
                    span_context = current_span.get_span_context()
                    if span_context.span_id != 0:
                        return format(span_context.span_id, "016x")
            except Exception:
                pass
        return "N/A"

    @staticmethod
    def get_current_trace_flags() -> str:
        if OTEL_AVAILABLE:
            try:
                current_span = trace.get_current_span()
                if current_span and current_span.is_recording():
                    span_context = current_span.get_span_context()
                    return format(span_context.trace_flags, "02x")
            except Exception:
                pass
        return "N/A"
