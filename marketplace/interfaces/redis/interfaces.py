from typing import Protocol, TypeVar, Generic


T = TypeVar("T")


class AbstractQueue(Protocol, Generic[T]):
    """
    Protocol defining the interface for queue implementations.
    This interface allows interchangeable use of different queue backends (e.g., in-memory, Redis).
    """

    def put(self, item: T) -> None:
        """
        Add an item to the end of the queue.

        Args:
            item: The item to add.
        """
        ...

    def get(self) -> T:
        """
        Remove and return an item from the beginning of the queue.

        Returns:
            The next item from the queue.
        """
        ...

    def empty(self) -> bool:
        """
        Check if the queue is empty.

        Returns:
            True if the queue is empty, False otherwise.
        """
        ...

    def qsize(self) -> int:
        """
        Get the current size of the queue.

        Returns:
            The number of items in the queue.
        """
        ...
