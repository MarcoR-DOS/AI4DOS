class ExactTokenFilter:
    def __init__(self):
        self.tokens = ("<|fim_suffix|>", "‹¡fim_suffix!>")
        self.pending = ""

    def feed(self, text):
        self.pending += text
        result = []
        while self.pending:
            token = next((t for t in self.tokens if self.pending.startswith(t)), None)
            if token:
                self.pending = self.pending[len(token):]
            elif any(t.startswith(self.pending) for t in self.tokens):
                break
            else:
                result.append(self.pending[0])
                self.pending = self.pending[1:]
        return "".join(result)

    def finish(self):
        result, self.pending = self.pending, ""
        return result

