class RoundRobinCounter:
    """Simple mutable counter used for round-robin start index."""

    def __init__(self, start: int = 0) -> None:
        self._value = start

    def next(self, modulo: int) -> int:
        index = self._value % modulo
        self._value += 1
        return index
