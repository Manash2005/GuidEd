from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class AIProfile(BaseModel):
    isAINative: Optional[bool] = None
    builtAIProductOrWorkflow: Optional[bool] = None
    subdomains: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)

class ToolExperience(BaseModel):
    tableau: Optional[bool] = None
    hubspot: Optional[bool] = None
    googleAnalytics: Optional[bool] = None
    jira: Optional[bool] = None
    excel: Optional[bool] = None
    mixpanel: Optional[bool] = None

class MentorBase(BaseModel):
    mentorId: str = Field(..., description="Unique mentor identifier (e.g. M001)")
    name: str = Field(...)
    contact: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    city: Optional[str] = None
    domain: Optional[str] = None
    company: Optional[str] = None
    masterSector: Optional[str] = None
    sectorsOfExpertise: List[str] = Field(default_factory=list)
    rolesOfExpertise: List[str] = Field(default_factory=list)
    seniority: Optional[str] = None
    aiProfile: Optional[AIProfile] = Field(default_factory=AIProfile)
    toolExperience: Optional[ToolExperience] = Field(default_factory=ToolExperience)
    mentorshipQuality: Optional[Literal["Excellent", "Good", "Average", "Poor"]] = None
    activitiesParticipated: Optional[int] = Field(default=None, ge=0)
    dataQualityIssues: List[str] = Field(default_factory=list)

class MentorResponse(MentorBase):
    pass

class MentorPublicResponse(BaseModel):
    mentorId: str
    name: str
    city: Optional[str] = None
    domain: Optional[str] = None
    company: Optional[str] = None
    masterSector: Optional[str] = None
    sectorsOfExpertise: List[str] = Field(default_factory=list)
    rolesOfExpertise: List[str] = Field(default_factory=list)
    seniority: Optional[str] = None
    aiProfile: Optional[AIProfile] = Field(default_factory=AIProfile)
    toolExperience: Optional[ToolExperience] = Field(default_factory=ToolExperience)
    mentorshipQuality: Optional[Literal["Excellent", "Good", "Average", "Poor"]] = None
    activitiesParticipated: Optional[int] = Field(default=None, ge=0)
    dataQualityIssues: List[str] = Field(default_factory=list)
