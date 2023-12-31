"""Abstract interfaces for the package checker."""
import dataclasses
import inspect
import typing
from types import NoneType
from typing import (
    Annotated,
    Callable,
    Generic,
    ParamSpec,
    Protocol,
    Sequence,
    TypedDict,
    TypeVar,
    cast,
)

import pydantic

P = ParamSpec("P")
T = TypeVar("T")


class TaskDetails(TypedDict):
    """Annotations of a task that are stored in the `__task_details__` field."""

    description: str
    dependencies: Sequence[str]


class Argument(TypedDict):
    """Details for an input."""

    description: str
    required: bool
    default: str


class Task(Protocol, Generic[P]):
    """Protocol for a task."""

    __task_details__: TaskDetails

    @typing.overload
    def __call__(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        """Run the task."""

    @typing.overload
    def __call__(
        self,
        github_model: "Github",
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        """Run the task."""


def task(
    dependencies: Sequence[str] = tuple(), description: str = ""
) -> Callable[[Callable[P, None]], Task[P]]:
    """Decorate a task."""

    def wrapper(fn: Callable[P, None]) -> Task[P]:
        setattr(
            fn,
            "__task_details__",
            TaskDetails({"dependencies": dependencies, "description": description}),
        )
        return cast(Task, fn)

    return wrapper


@dataclasses.dataclass(frozen=True, kw_only=True)
class Input:
    """An input annotation."""

    description: str = ""


class Tasks:
    """Class that holds multiple tasks."""

    def __init__(self, **tasks: Task):
        """Create a new Tasks object."""
        self.__tasks = tasks

    def inputs(self) -> dict[str, Argument]:
        """Get the inputs to the tasks as a dictionary."""
        NONE = type("NONE", (), {"default": inspect._empty})()
        output = {}
        for name, task in self.__tasks.items():
            output[f"use_{name}"] = {
                "default": "false",
                "required": False,
                "description": task.__task_details__["description"]
                or f"Whether to run the {name} task.",
            }
            for kwarg, annotation in task.__annotations__.items():
                if (not hasattr(annotation, "__origin__")) or typing.get_origin(
                    annotation
                ) != Annotated:
                    annotation = Annotated[annotation, Input()]
                if kwarg == "github_model":
                    continue

                if (
                    default := inspect.signature(task)
                    .parameters.get(kwarg, NONE)
                    .default
                ) is inspect._empty:
                    default = "-"
                else:
                    default = default
                output[f"{name}_{kwarg}"] = Argument(
                    {
                        "description": annotation.__metadata__[0].description,
                        "required": not any(
                            a
                            for annotation in annotation.__args__
                            for a in getattr(annotation, "__args__", (annotation,))
                            if a is NoneType
                        ),
                        "default": default,
                    }
                )
        return output

    def cli_args(
        self,
    ) -> str:
        """Get the CLI args."""
        inputs = self.inputs()
        cli_args = " ".join(
            f"--{input} ${{{{ inputs.{input} }}}}" for input in inputs.keys()
        )
        return cli_args


class Repository(pydantic.BaseModel):
    """Github repository."""

    default_branch: str


class Event(pydantic.BaseModel):
    """Github event."""

    repository: Repository


class Github(pydantic.BaseModel):
    """Github event."""

    ref_name: str
    event: Event
