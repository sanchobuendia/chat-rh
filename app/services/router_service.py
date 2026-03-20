class RouterService:
    def __init__(self, llm_service):
        self.llm_service = llm_service

    def route(self, question: str) -> str:
        return self.llm_service.decide_route(question)
