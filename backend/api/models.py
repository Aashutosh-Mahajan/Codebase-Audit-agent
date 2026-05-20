"""
Pydantic data models shared across all agents and the report pipeline.

FileLocation — pinpoints a finding in the source tree.
Finding      — single audit finding produced by a specialist agent.
"""

from pydantic import BaseModel, Field


class FileLocation(BaseModel):
    """Exact location of a finding within a source file."""

    file_path: str = Field(description="Relative path from repository root")
    line_start: int = Field(default=0, description="Starting line number")
    line_end: int = Field(default=0, description="Ending line number")


class Finding(BaseModel):
    """A single audit finding emitted by a specialist agent."""

    agent: str = Field(description="Name of the agent that detected this finding")
    severity: str = Field(description="One of 'EXTREME', 'HIGH', 'MEDIUM', 'LOW'")
    title: str = Field(description="Short descriptive title")
    bug_type: str = Field(description="Category (e.g. 'Injection', 'Memory Leak')")
    what_is_it: str = Field(default="", description="Plain-English description of the issue")
    why_it_occurs: str = Field(default="", description="Root cause explanation")
    how_it_occurred: str = Field(default="", description="Code pattern or execution flow that caused it")
    where_it_is: FileLocation = Field(default_factory=lambda: FileLocation(file_path="unknown"), description="Location in the codebase")
    affected_code: str = Field(default="", description="Exact code snippet showing the issue")
    recommended_fix: str = Field(default="", description="Concrete fix or replacement code")
    references: list[str] = Field(default_factory=list, description="CWE IDs, OWASP refs, or doc links")
    score: float = Field(default=0.0, description="Severity score from 0.0 to 100.0")
    detected_by: list[str] = Field(default_factory=list, description="All agents that detected this finding")
