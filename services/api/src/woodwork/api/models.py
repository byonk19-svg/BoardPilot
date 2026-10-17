from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field
from woodwork.domain import ProjectSpec

class Request(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Empty(Request):pass
class CreateProject(Request):
    title:str=Field(min_length=1,max_length=100)
    spec:ProjectSpec
class CreateRevision(Request):
    base_revision_id:str=Field(min_length=1,max_length=100)
    spec:ProjectSpec
class Draft(Request):
    base_revision_id:str=Field(min_length=1,max_length=100)
    raw:dict[str,Any]
class JobRequest(Request):
    kind:Literal['generate','documents','stock']
    idempotency_key:str=Field(min_length=1,max_length=100)
    source_artifact_set_id:str|None=Field(default=None,max_length=100)
class PackageRequest(Request):
    idempotency_key:str=Field(min_length=1,max_length=100)
    artifact_set_id:str|None=Field(default=None,max_length=100)
class ImportRequest(Request):
    token:str=Field(min_length=1,max_length=100)
    title:str=Field(min_length=1,max_length=100)
class ProposalRequest(Request):
    base_revision_id:str=Field(min_length=1,max_length=100)
    text:str=Field(min_length=1,max_length=4000)
    idempotency_key:str=Field(min_length=1,max_length=100)
    mode:Literal['fake','live']='fake'
class ApplyProposal(Request):
    expected_base_revision_id:str=Field(min_length=1,max_length=100)
class Measurement(Request):
    field:str=Field(min_length=1,max_length=100)
    text:str=Field(max_length=100)
    default_unit:Literal['mm','cm','in']|None=None
