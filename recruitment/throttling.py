from rest_framework.throttling import SimpleRateThrottle


class AiAnalysisDailyThrottle(SimpleRateThrottle):
    scope = "ai_analysis_daily"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": "all"}
